"""PLAZA-I WhatsApp AI assistant — secure webhook, durable queue, and staff dashboard."""
import asyncio
import hashlib
import hmac
import json
import logging
import re
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field

from app.settings import Settings
from app.storage import Storage
from app.services import AIService, WhatsAppService, demo_reply, is_tajik, needs_handoff, handoff_message
from app.prompt import MEDIA_TG, MEDIA_RU
from app.dashboard import HTML

logger = logging.getLogger('plazai')
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
config = Settings()
store: Storage | None = None
ai: AIService | None = None
wa: WhatsAppService | None = None
basic_auth=HTTPBasic()


def admin_auth(creds: HTTPBasicCredentials = Depends(basic_auth)):
    correct_user=secrets.compare_digest(creds.username.encode(), config.admin_username.encode())
    correct_pass=secrets.compare_digest(creds.password.encode(), config.admin_password.encode())
    if not (correct_user and correct_pass):
        raise HTTPException(status_code=401, detail='Invalid login', headers={'WWW-Authenticate':'Basic'})
    return True


def csrf_guard(request: Request):
    if request.headers.get('X-PLAZAI-Request')!='dashboard':
        raise HTTPException(403, 'Admin request header required')


async def queue_worker():
    assert store is not None
    while True:
        try:
            event=store.claim()
            if event is None:
                await asyncio.sleep(0.8)
                continue
            await process_one(event)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception('Worker loop failure')
            await asyncio.sleep(1)


async def process_one(event):
    assert store is not None
    msg_id=event['meta_id']
    wa_id=event['wa_id']
    try:
        if store.mode(wa_id)=='human':
            store.finish(msg_id)
            return
        history=store.transcript(wa_id,through=event['msg_seq'],limit=20)
        user=next((x['body'] for x in reversed(history) if x['role']=='user'), '')
        if not user:
            store.finish(msg_id)
            return
        handoff=needs_handoff(user)
        if handoff:
            answer=handoff_message(user,history)
        elif user=='[MEDIA_NOT_SUPPORTED]':
            answer=MEDIA_TG if is_tajik(user,history) else MEDIA_RU
        elif config.demo_mode and not config.ai_preview_mode:
            answer=demo_reply(user,history)
        else:
            assert ai is not None
            answer=await ai.reply(history)
        if store.mode(wa_id)=='human':
            store.finish(msg_id)
            return
        if config.demo_mode:
            pass
        else:
            assert wa is not None
            await wa.send(wa_id,answer)
        store.append(wa_id,'assistant',answer)
        if handoff:
            store.set_mode(wa_id,'human')
        store.finish(msg_id)
    except Exception:
        # Do not log message text or API keys.
        logger.exception('Message delivery failed (id=%s)',msg_id[:18])
        if store.retry(msg_id):
            store.set_mode(wa_id, 'human')
            logger.warning('Chat switched to human after repeated delivery failures')


@asynccontextmanager
async def lifespan(app: FastAPI):
    global store, ai, wa
    config.check()
    store=Storage(config.database_path)
    store.recover()
    if not config.demo_mode or config.ai_preview_mode:
        ai=AIService(config.openai_api_key,config.openai_model)
    if not config.demo_mode:
        wa=WhatsAppService(config.meta_access_token,config.meta_phone_number_id,config.meta_graph_version)
    task=asyncio.create_task(queue_worker())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        if wa:
            await wa.close()
        if ai:
            await ai.close()


app=FastAPI(title='PLAZA-I WhatsApp AI',version='1.0.0',lifespan=lifespan,docs_url=None,redoc_url=None)


@app.get('/health')
def health():
    return {'ok':True, 'demo':config.demo_mode, 'ai_preview':config.demo_mode and config.ai_preview_mode}


@app.get('/webhook')
def webhook_check(request: Request):
    q=request.query_params
    mode=q.get('hub.mode')
    token=q.get('hub.verify_token','')
    challenge=q.get('hub.challenge','')
    if mode=='subscribe' and config.meta_verify_token and secrets.compare_digest(token,config.meta_verify_token):
        return PlainTextResponse(challenge)
    raise HTTPException(status_code=403,detail='Webhook verification failed')


@app.post('/webhook')
async def webhook_receive(request: Request):
    assert store is not None
    raw=await request.body()
    if len(raw)>1_000_000:
        raise HTTPException(413,'Payload too large')
    signature=request.headers.get('x-hub-signature-256','')
    if not config.meta_app_secret:
        raise HTTPException(403,'Webhook disabled in demo')
    expected='sha256='+hmac.new(config.meta_app_secret.encode(),raw,hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature,expected):
        raise HTTPException(403,'Invalid webhook signature')
    try:
        data=json.loads(raw)
    except (json.JSONDecodeError,UnicodeDecodeError):
        raise HTTPException(400,'Invalid JSON')
    if not isinstance(data,dict) or data.get('object')!='whatsapp_business_account':
        return {'ok':True}
    entries = data.get('entry', [])
    if not isinstance(entries, list):
        return {'ok': True}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        changes = entry.get('changes', [])
        if not isinstance(changes, list):
            continue
        for change in changes:
            if not isinstance(change, dict):
                continue
            value = change.get('value', {})
            if not isinstance(value, dict):
                continue
            metadata = value.get('metadata', {})
            if not isinstance(metadata, dict):
                continue
            if metadata.get('phone_number_id') != config.meta_phone_number_id:
                continue
            messages = value.get('messages', [])
            if not isinstance(messages, list):
                continue
            for msg in messages:
                if not isinstance(msg, dict):
                    continue
                msg_id = msg.get('id')
                wa_id = msg.get('from')
                if not isinstance(msg_id, str) or not msg_id or not isinstance(wa_id, str):
                    continue
                if not re.fullmatch(r'\d{6,20}', wa_id):
                    continue
                if msg.get('type') == 'text':
                    text_data = msg.get('text', {})
                    if not isinstance(text_data, dict):
                        continue
                    raw_body = text_data.get('body')
                    if not isinstance(raw_body, str):
                        continue
                    body = raw_body.strip()[:3500]
                    if not body:
                        continue
                else:
                    body = '[MEDIA_NOT_SUPPORTED]'
                store.receive(msg_id, wa_id, body)
    return {'ok':True}


@app.get('/admin',response_class=HTMLResponse,dependencies=[Depends(admin_auth)])
def admin_page():
    return HTMLResponse(HTML,headers={'Cache-Control':'no-store','X-Frame-Options':'DENY','Content-Security-Policy':"default-src 'self'; script-src 'unsafe-inline' 'self'; style-src 'unsafe-inline' 'self'; connect-src 'self'; frame-ancestors 'none'"})


@app.get('/api/admin/chats',dependencies=[Depends(admin_auth)])
def chats():
    assert store is not None
    return {'items':store.list_chats(), 'demo':config.demo_mode,
            'ai_preview':config.demo_mode and config.ai_preview_mode}


@app.get('/api/admin/chats/{wa_id}',dependencies=[Depends(admin_auth)])
def chat(wa_id: str):
    assert store is not None
    if not re.fullmatch(r'\d{6,20}',wa_id):
        raise HTTPException(400,'Invalid phone number')
    return {'mode':store.mode(wa_id),'messages':store.chat_details(wa_id)}


class ModeRequest(BaseModel):
    mode: str


class TextRequest(BaseModel):
    text: str = Field(min_length=1,max_length=3500)


@app.post('/api/admin/chats/{wa_id}/mode',dependencies=[Depends(admin_auth),Depends(csrf_guard)])
def change_mode(wa_id: str, body: ModeRequest):
    assert store is not None
    if not re.fullmatch(r'\d{6,20}',wa_id) or body.mode not in ('ai','human'):
        raise HTTPException(400,'Invalid mode or number')
    store.set_mode(wa_id,body.mode)
    return {'ok':True,'mode':body.mode}


@app.post('/api/admin/chats/{wa_id}/reply',dependencies=[Depends(admin_auth),Depends(csrf_guard)])
async def manual_reply(wa_id: str, body: TextRequest):
    assert store is not None
    if not re.fullmatch(r'\d{6,20}',wa_id):
        raise HTTPException(400,'Invalid phone number')
    if store.mode(wa_id)!='human':
        raise HTTPException(409,'Switch chat to HUMAN before sending')
    if not config.demo_mode:
        assert wa is not None
        try:
            await wa.send(wa_id,body.text)
        except Exception:
            logger.exception('Staff WhatsApp send failed')
            raise HTTPException(502,'WhatsApp did not accept the message')
    store.append(wa_id,'staff',body.text)
    return {'ok':True}


@app.post('/api/admin/demo',dependencies=[Depends(admin_auth),Depends(csrf_guard)])
def simulate(body: TextRequest):
    assert store is not None
    if not config.demo_mode:
        raise HTTPException(403,'Demo is disabled')
    import uuid
    store.receive('demo-'+uuid.uuid4().hex,'992900000001',body.text)
    return {'ok':True, 'wa_id':'992900000001'}


@app.delete('/api/admin/chats/{wa_id}',dependencies=[Depends(admin_auth),Depends(csrf_guard)])
def erase_chat(wa_id: str):
    assert store is not None
    if not re.fullmatch(r'\d{6,20}',wa_id):
        raise HTTPException(400,'Invalid phone number')
    store.delete_chat(wa_id)
    return {'ok':True}
