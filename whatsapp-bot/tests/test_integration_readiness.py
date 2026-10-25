"""Safe onboarding prerequisites and staging/production separation."""
import hashlib
import hmac
import json
import time
from dataclasses import replace

from fastapi.testclient import TestClient
from app import main
from app.settings import Settings


def test_integration_status_is_private_and_redacts_credentials(tmp_path, monkeypatch):
    cfg=replace(Settings(), database_path=str(tmp_path/'status.db'),
        demo_mode=True, ai_preview_mode=True,
        openai_api_key='openai-secret-test-sentinel',
        meta_access_token='meta-secret-test-sentinel',
        meta_app_secret='app-secret-test-sentinel',
        meta_verify_token='verify-secret-test-sentinel',
        meta_phone_number_id='987654',
        admin_username='plazai',
        admin_password='dashboard-secret-test')
    monkeypatch.setattr(main,'config',cfg)
    with TestClient(main.app) as client:
        assert client.get('/api/admin/integration-status').status_code == 401
        r=client.get('/api/admin/integration-status',
            auth=('plazai','dashboard-secret-test'))
        assert r.status_code == 200
        assert r.headers.get('cache-control')=='no-store'
        j=r.json()
        assert j['openai']['api_key_configured'] is True
        assert j['openai']['billing_verified'] is False
        assert j['whatsapp']['all_credentials_configured'] is True
        assert j['whatsapp']['live_intake_enabled'] is False
        assert j['whatsapp']['onboarding_verified'] is False
        assert j['storage']['durability_verified'] is False
        body=r.text
        for secret in ('openai-secret-test-sentinel','meta-secret-test-sentinel',
                       'app-secret-test-sentinel','verify-secret-test-sentinel'):
            assert secret not in body


def test_live_webhook_accepts_signed_message_with_mock_services(tmp_path, monkeypatch):
    class FakeAI:
        def __init__(self,*args):
            self.last_usage=None
            self.model='gpt-5.4-mini'
        async def reply(self,history):
            return 'Ҷавоби санҷишӣ'
        async def close(self): pass
    class FakeWhatsApp:
        sent=[]
        def __init__(self,*args): pass
        async def send(self,wa_id,answer):
            self.sent.append((wa_id,answer))
            return {'ok':True}
        async def close(self): pass

    cfg=replace(Settings(),database_path=str(tmp_path/'live.db'),
        demo_mode=False,ai_preview_mode=False,openai_api_key='not-a-real-key',
        meta_access_token='not-a-real-meta-token',
        meta_app_secret='signed-test-secret',
        meta_verify_token='verify-test-token',
        meta_phone_number_id='987654',
        admin_password='dashboard-secret-test',
        admin_username='plazai')
    monkeypatch.setattr(main,'config',cfg)
    monkeypatch.setattr(main,'AIService',FakeAI)
    monkeypatch.setattr(main,'WhatsAppService',FakeWhatsApp)

    payload={'object':'whatsapp_business_account','entry':[
        {'changes':[{'value':{
            'metadata':{'phone_number_id':'987654'},
            'messages':[{'id':'wamid.test-live','from':'992900000001',
                         'type':'text','text':{'body':'Ман дизайн мехоҳам'}}]
        }}]}
    ]}
    data=json.dumps(payload).encode()
    sig='sha256='+hmac.new(b'signed-test-secret',data,hashlib.sha256).hexdigest()
    with TestClient(main.app) as client:
        invalid=client.post('/webhook',content=data,
                            headers={'x-hub-signature-256':'sha256=bad'})
        assert invalid.status_code==403
        valid=client.post('/webhook',content=data,
                          headers={'x-hub-signature-256':sig})
        assert valid.status_code==200
        again=client.post('/webhook',content=data,
                          headers={'x-hub-signature-256':sig})
        assert again.status_code==200
        for _ in range(45):
            if FakeWhatsApp.sent:
                break
            time.sleep(.05)
        assert FakeWhatsApp.sent==[('992900000001','Ҷавоби санҷишӣ')]
        messages=main.store.transcript('992900000001')
        assert [x['role'] for x in messages]==['user','assistant']
