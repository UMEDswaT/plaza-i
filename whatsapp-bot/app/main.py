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
from fastapi.responses import HTMLResponse, PlainTextResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field

from app.settings import Settings
from app.storage import Storage
from app.services import AIService, AIServiceError, WhatsAppService, demo_reply, is_tajik, needs_handoff, handoff_message
from app.prompt import MEDIA_TG, MEDIA_RU
from app.dashboard import HTML
from app.expertise import KnowledgeBase, domain_demo_reply
from app.usage import UsageLedger

logger = logging.getLogger('plazai')
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
config = Settings()
store: Storage | None = None
knowledge: KnowledgeBase | None = None
usage_ledger: UsageLedger | None = None
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
            assert knowledge is not None
            answer=(knowledge.demo_answer(user)
                    or domain_demo_reply(user, is_tajik(user, history))
                    or demo_reply(user,history))
        else:
            assert ai is not None
            answer=await ai.reply(history)
            if usage_ledger is not None and getattr(ai, 'last_usage', None) is not None:
                try:
                    usage_ledger.record_success(msg_id, ai.model, ai.last_usage)
                except Exception:
                    # Accounting must not cause a second paid model call.
                    logger.exception('API usage ledger write failed')
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
    except AIServiceError as exc:
        if usage_ledger is not None:
            try:
                usage_ledger.record_error(msg_id, config.openai_model, exc.code)
            except Exception:
                logger.exception('API error ledger write failed')
        # Authentication, quota and rate-limit errors are NOT recoverable
        # by aggressive retries. Do not turn one message into 5 API calls.
        logger.warning("OpenAI unavailable (http_status=%s, category=%s)", exc.status, exc.code)
        if config.demo_mode:
            history = store.transcript(wa_id, through=event['msg_seq'], limit=20)
            user = next((x['body'] for x in reversed(history) if x['role']=='user'), '')
            tajik = is_tajik(user, history)
            if exc.code == 'quota':
                notice = ("OpenAI API: кредити истифода ё лимити хароҷот тамом шудааст. "
                          "Дар OpenAI Platform бахшҳои Billing ва Limits-ро санҷед." if tajik else
                          "OpenAI API: закончились кредиты или достигнут лимит расходов. "
                          "Проверьте Billing и Limits в OpenAI Platform.")
            elif exc.code == 'limit':
                notice = ("OpenAI API: хатои 429. Лимити дархостҳо ё маблағи API-ро санҷед. "
                          "Такрори пайдарпайи саволҳо мушкилро ҳал намекунад." if tajik else
                          "OpenAI API: ошибка 429. Проверьте лимиты запросов и баланс API. "
                          "Повторные попытки подряд не решат проблему.")
            elif exc.code == 'auth':
                notice = ("OpenAI API: калид ё иҷозат нодуруст аст. Танзимоти API-ро санҷед." if tajik else
                          "OpenAI API: неверный ключ или разрешения. Проверьте доступ.")
            else:
                notice = ("OpenAI API дархостро қабул накард; модел ва иҷозатҳоро санҷед." if tajik else
                          "OpenAI API отклонил запрос; проверьте модель и разрешения.")
            # Offline responses are explicitly marked and never misrepresented
            # as successful generative-AI answers.
            assert knowledge is not None
            offline = (knowledge.demo_answer(user)
                       or domain_demo_reply(user, tajik)
                       or demo_reply(user, history))
            marker = "Ҷавоби намунавии ОФЛАЙН:" if tajik else "Пример ответа ОФЛАЙН:"
            store.append(wa_id, 'assistant', "⚠️ " + notice + "\n\n" + marker + "\n" + offline)
        else:
            store.set_mode(wa_id, 'human')
        store.finish(msg_id)
    except Exception:
        # Do not log message text or API keys.
        logger.exception('Message delivery failed (id=%s)',msg_id[:18])
        if store.retry(msg_id):
            store.set_mode(wa_id, 'human')
            logger.warning('Chat switched to human after repeated delivery failures')


@asynccontextmanager
async def lifespan(app: FastAPI):
    global store, ai, wa, knowledge, usage_ledger
    config.check()
    store=Storage(config.database_path)
    knowledge=KnowledgeBase(config.database_path)
    usage_ledger=UsageLedger(config.database_path)
    store.recover()
    if not config.demo_mode or config.ai_preview_mode:
        ai=AIService(config.openai_api_key,config.openai_model)
        ai.knowledge_provider=knowledge.context
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


@app.get('/api/admin/usage', dependencies=[Depends(admin_auth)])
def api_usage(days: int = 30):
    assert usage_ledger is not None
    try:
        summary=usage_ledger.summary(days)
    except ValueError as exc:
        raise HTTPException(400,str(exc))
    return JSONResponse(summary, headers={'Cache-Control':'no-store'})


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
    if config.suggest_from_staff and knowledge is not None:
        # Learning candidates remain unpublished until explicitly approved.
        try:
            history = store.transcript(wa_id,limit=16)
            question = next((m['body'] for m in reversed(history)
                             if m['role']=='user'), None)
            if question:
                knowledge.suggest_from_staff(question,body.text)
        except Exception:
            logger.exception('Could not create knowledge suggestion')
    return {'ok':True}


@app.post('/api/admin/demo',dependencies=[Depends(admin_auth),Depends(csrf_guard)])
def simulate(body: TextRequest):
    assert store is not None
    if not config.demo_mode:
        raise HTTPException(403,'Demo is disabled')
    import uuid
    store.receive('demo-'+uuid.uuid4().hex,'992900000001',body.text)
    return {'ok':True, 'wa_id':'992900000001'}



class KnowledgeDraft(BaseModel):
    question: str = Field(min_length=8,max_length=500)
    answer: str = Field(min_length=10,max_length=1500)
    topic: str = Field(default='general',max_length=60)


class KnowledgeReview(BaseModel):
    state: str
    question: str | None = Field(default=None, min_length=8,max_length=500)
    answer: str | None = Field(default=None,min_length=10,max_length=1500)


@app.get('/api/admin/knowledge',dependencies=[Depends(admin_auth)])
def list_knowledge(state: str='all'):
    assert knowledge is not None
    try:
        return {'items': knowledge.list_entries(state)}
    except ValueError as exc:
        raise HTTPException(400,str(exc))



class KnowledgeImport(BaseModel):
    items: list[KnowledgeDraft] = Field(min_length=1,max_length=200)


@app.get('/api/admin/knowledge/export',dependencies=[Depends(admin_auth)])
def export_knowledge():
    assert knowledge is not None
    entries = knowledge.list_entries('approved',limit=500)
    # Approved reusable facts only: no phone numbers, raw conversations or passwords.
    return JSONResponse(
        {'format':'plazai-approved-knowledge-v1',
         'items':[{'topic':row['topic'],'question':row['question'],
                   'answer':row['answer']} for row in entries]},
        headers={'Cache-Control':'no-store'})


@app.post('/api/admin/knowledge/import',dependencies=[Depends(admin_auth),Depends(csrf_guard)])
def import_knowledge(payload: KnowledgeImport):
    assert knowledge is not None
    count = 0
    for entry in payload.items:
        try:
            knowledge.propose(entry.question,entry.answer,entry.topic,'import_review')
            count += 1
        except ValueError as exc:
            raise HTTPException(400,str(exc))
    # Restored knowledge is pending; an admin must review it before use.
    return {'ok':True,'processed':count,'state':'pending'}


@app.post('/api/admin/knowledge',dependencies=[Depends(admin_auth),Depends(csrf_guard)])
def propose_knowledge(draft: KnowledgeDraft):
    assert knowledge is not None
    try:
        entry_id=knowledge.propose(draft.question,draft.answer,draft.topic,'manager')
    except ValueError as exc:
        raise HTTPException(400,str(exc))
    return {'ok':True,'id':entry_id,'state':'pending'}


@app.post('/api/admin/knowledge/{entry_id}/review',
          dependencies=[Depends(admin_auth),Depends(csrf_guard)])
def review_knowledge(entry_id: int, review: KnowledgeReview):
    assert knowledge is not None
    try:
        knowledge.review(entry_id,review.state,review.question,review.answer)
    except KeyError:
        raise HTTPException(404,'Unknown knowledge entry')
    except ValueError as exc:
        raise HTTPException(400,str(exc))
    return {'ok':True,'id':entry_id,'state':review.state}


@app.delete('/api/admin/chats/{wa_id}',dependencies=[Depends(admin_auth),Depends(csrf_guard)])
def erase_chat(wa_id: str):
    assert store is not None
    if not re.fullmatch(r'\d{6,20}',wa_id):
        raise HTTPException(400,'Invalid phone number')
    store.delete_chat(wa_id)
    return {'ok':True}
