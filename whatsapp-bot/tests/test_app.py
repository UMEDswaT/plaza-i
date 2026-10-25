import hashlib
import hmac
import json
from dataclasses import replace
from fastapi.testclient import TestClient
from app import main
from app.settings import Settings
from app.services import PRICE_OUTPUT, demo_reply, needs_handoff, handoff_message
from app.storage import Storage


def test_handoff_policy():
    assert needs_handoff('Нархаш чанд?')
    assert needs_handoff('Сколько стоит проект?')
    assert needs_handoff('Бо менеҷер суҳбат кунам')
    assert not needs_handoff('Ман дизайни хона мехоҳам')
    assert 'менеҷер' in handoff_message('Нархаш чанд?')
    assert 'менеджер' in handoff_message('Сколько стоит?')
    assert PRICE_OUTPUT.search('Арзиш 50 сомонӣ аст')
    assert not PRICE_OUTPUT.search('Душанбе, кӯчаи Соҳили 22')


def test_storage_dedup_and_history(tmp_path):
    s=Storage(str(tmp_path/'test.db'))
    assert s.receive('w1','992900000001','Салом')
    assert not s.receive('w1','992900000001','Салом')
    assert s.receive('w2','992900000001','Ба ман дизайн даркор')
    claimed=s.claim()
    assert claimed['meta_id']=='w1'
    assert len(s.transcript('992900000001',through=claimed['msg_seq']))==1
    s.finish('w1')
    assert s.claim()['meta_id']=='w2'
    s.set_mode('992900000001','human')
    assert s.mode('992900000001')=='human'
    s.delete_chat('992900000001')
    assert not s.list_chats()


def test_demo_design():
    assert 'дизайни дохили' in demo_reply('Ман дизайни хонаи худро мехоҳам')
    assert 'дизайн' in demo_reply('Мне нужен дизайн интерьера')


def test_webhook_signature_and_admin(tmp_path, monkeypatch):
    settings=replace(Settings(),database_path=str(tmp_path/'run.db'),
        demo_mode=True,admin_username='plazai',admin_password='secret-password-123',
        meta_app_secret='secret-meta',meta_phone_number_id='9876',meta_verify_token='token')
    monkeypatch.setattr(main,'config',settings)
    with TestClient(main.app) as client:
        auth=('plazai','secret-password-123')
        get=client.get('/webhook?hub.mode=subscribe&hub.verify_token=token&hub.challenge=987')
        assert get.status_code==200 and get.text=='987'
        assert client.get('/webhook?hub.mode=subscribe&hub.verify_token=bad&hub.challenge=987').status_code==403
        body={'object':'whatsapp_business_account','entry':[{'changes':[{'value':{
            'metadata':{'phone_number_id':'9876'},
            'messages':[{'id':'wamid.1','from':'992900000001','type':'text','text':{'body':'Ба ман дизайн даркор'}}]}}]}]}
        raw=json.dumps(body).encode()
        bad=client.post('/webhook',content=raw,headers={'x-hub-signature-256':'sha256=bad'})
        assert bad.status_code==403
        sig='sha256='+hmac.new(b'secret-meta',raw,hashlib.sha256).hexdigest()
        for _ in range(2):
            resp=client.post('/webhook',content=raw,headers={'x-hub-signature-256':sig})
            assert resp.status_code==200
        assert len(main.store.transcript('992900000001'))>=1
        assert client.get('/api/admin/chats').status_code==401
        assert client.get('/api/admin/chats',auth=auth).status_code==200
        assert client.post('/api/admin/chats/992900000001/mode',json={'mode':'human'},auth=auth).status_code==403
        hdr={'X-PLAZAI-Request':'dashboard'}
        assert client.post('/api/admin/chats/992900000001/mode',json={'mode':'human'},headers=hdr,auth=auth).status_code==200
        assert client.post('/api/admin/chats/992900000001/reply',json={'text':'Менеҷер ҷавоб медиҳад'},headers=hdr,auth=auth).status_code==200
