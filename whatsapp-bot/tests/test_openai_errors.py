"""No-cost local tests for OpenAI API failure handling."""
import asyncio
import time
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app import main
from app.services import AIService, AIServiceError
from app.settings import Settings


class FakeResponse:
    def __init__(self, status, error=None):
        self.status_code = status
        self._error = error or {}
    def json(self):
        return {"error": self._error}
    def raise_for_status(self):
        raise AssertionError("Expected the API error to be classified first")


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls = 0
    async def post(self, *args, **kwargs):
        self.calls += 1
        return self.response


@pytest.mark.parametrize("error,category", [
    ({"code": "insufficient_quota", "type": "insufficient_quota"}, "quota"),
    ({"code": "credit_balance_exhausted"}, "quota"),
    ({"code": "organization_spend_limit_exceeded"}, "quota"),
    ({"code": "rate_limit_exceeded", "type": "rate_limit_error"}, "limit"),
    ({}, "limit"),
])
def test_429_is_classified_and_circuit_breaker_prevents_repeat(error, category):
    ai = AIService("test-not-a-real-key", "model-test")
    fake = FakeClient(FakeResponse(429, error))
    ai.client = fake
    for _ in range(2):
        with pytest.raises(AIServiceError) as exc:
            asyncio.run(ai.reply([{"role": "user", "body": "Ман лоиҳа мехоҳам"}]))
        assert exc.value.code == category
        assert exc.value.status == 429
    assert fake.calls == 1


@pytest.mark.parametrize("status,category", [(401, "auth"), (403, "auth"), (400, "request")])
def test_nonretryable_access_errors(status, category):
    ai = AIService("test-not-a-real-key", "model-test")
    ai.client = FakeClient(FakeResponse(status))
    with pytest.raises(AIServiceError) as exc:
        asyncio.run(ai.reply([{"role": "user", "body": "Салом"}]))
    assert exc.value.code == category
    assert exc.value.status == status


def test_preview_explains_api_429_and_finishes_queue(tmp_path, monkeypatch):
    class AlwaysQuotaAI:
        calls = 0
        def __init__(self, api_key, model):
            pass
        async def reply(self, history):
            type(self).calls += 1
            raise AIServiceError("quota", 429)
        async def close(self):
            pass
    cfg = replace(Settings(), database_path=str(tmp_path / "preview429.db"),
                  demo_mode=True, ai_preview_mode=True,
                  openai_api_key="test-not-a-real-key",
                  admin_username="plazai", admin_password="test-password-long")
    monkeypatch.setattr(main, "config", cfg)
    monkeypatch.setattr(main, "AIService", AlwaysQuotaAI)
    hdr = {"X-PLAZAI-Request": "dashboard"}
    auth = ("plazai", "test-password-long")
    with TestClient(main.app) as client:
        r = client.post("/api/admin/demo", auth=auth, headers=hdr,
                        json={"text": "Назорати муаллифӣ чист?"})
        assert r.status_code == 200
        texts = []
        for _ in range(50):
            texts = [x["body"] for x in client.get(
                "/api/admin/chats/992900000001", auth=auth).json()["messages"]
                if x["role"] == "assistant"]
            if texts:
                break
            time.sleep(0.05)
        assert len(texts) == 1
        assert "OpenAI API" in texts[0]
        assert "ОФЛАЙН" in texts[0]
        assert "назорати муаллифӣ" in texts[0].casefold()
        with main.store.db() as con:
            rows = con.execute("SELECT status,attempts FROM queue").fetchall()
            assert len(rows) == 1
            assert rows[0]["status"] == "done"
            assert rows[0]["attempts"] == 1
        assert AlwaysQuotaAI.calls == 1
