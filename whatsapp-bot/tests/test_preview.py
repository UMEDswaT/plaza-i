"""Tests for opt-in AI preview and contextual offline replies."""
import time
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app import main
from app.services import demo_reply
from app.settings import Settings


def test_demo_context_and_company_faq():
    first = "Ман дизайни хона мехоҳам"
    result = demo_reply(first)
    assert "метри мураббаъ" in result
    history = [
        {"role": "user", "body": first},
        {"role": "assistant", "body": result},
        {"role": "user", "body": "120 м2"},
    ]
    followup = demo_reply("120 м2", history)
    assert "ҳуҷра" in followup
    assert "Соҳили" in demo_reply("Суроғаатон куҷо?")
    assert "лиценз" in demo_reply("Есть лицензия?").lower()
    assert "срок" in demo_reply("Какой срок проекта?").lower()


def test_ai_preview_key_is_required():
    settings = replace(Settings(), demo_mode=True, ai_preview_mode=True,
                       openai_api_key="", admin_password="test-admin-password")
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        settings.check()
    ready = replace(settings, openai_api_key="dummy-key")
    ready.check()
    with pytest.raises(RuntimeError, match="DEMO_MODE"):
        replace(ready, demo_mode=False).check()


def test_ai_preview_uses_ai_without_whatsapp(tmp_path, monkeypatch):
    class FakeAI:
        calls = []
        def __init__(self, api_key, model):
            assert api_key == "local-test-key"
        async def reply(self, history):
            self.calls.append(history)
            return "Ҷавоби пурраи санҷиш"
        async def close(self):
            pass

    class NoWhatsApp:
        def __init__(self, *args, **kwargs):
            raise AssertionError("AI preview must never start WhatsApp")

    settings = replace(Settings(), database_path=str(tmp_path/"preview.db"),
        demo_mode=True, ai_preview_mode=True, openai_api_key="local-test-key",
        admin_username="plazai", admin_password="test-admin-password")
    monkeypatch.setattr(main, "config", settings)
    monkeypatch.setattr(main, "AIService", FakeAI)
    monkeypatch.setattr(main, "WhatsAppService", NoWhatsApp)
    auth=("plazai", "test-admin-password")
    headers={"X-PLAZAI-Request": "dashboard"}
    with TestClient(main.app) as client:
        assert client.get("/health").json()["ai_preview"] is True
        assert client.get("/api/admin/chats", auth=auth).json()["ai_preview"] is True
        sent=client.post("/api/admin/demo", json={"text":"Ман дизайн мехоҳам"},
                         auth=auth, headers=headers)
        assert sent.status_code == 200
        answer = None
        for _ in range(30):
            messages=client.get("/api/admin/chats/992900000001", auth=auth).json()["messages"]
            answer=next((m["body"] for m in messages if m["role"]=="assistant"), None)
            if answer:
                break
            time.sleep(0.1)
        assert answer == "Ҷавоби пурраи санҷиш"
        assert FakeAI.calls
