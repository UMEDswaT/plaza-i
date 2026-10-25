"""No-charge tests for OpenAI usage/cost reporting."""
import asyncio
import hashlib
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app import main
from app.usage import UsageLedger, estimate_usd
from app.settings import Settings


def test_gpt54_mini_price_and_cached_tokens():
    assert estimate_usd("gpt-5.4-mini", 3000, 300) == pytest.approx(0.0036)
    assert estimate_usd("gpt-5.4-mini-2026-03-17", 1000, 200, 500) == pytest.approx(
        (500*.75 + 500*.075 + 200*4.5)/1_000_000
    )
    assert estimate_usd("custom-model", 1000, 200) is None
    with pytest.raises(ValueError):
        estimate_usd("gpt-5.4-mini", 100, 10, 101)
    with pytest.raises(ValueError):
        estimate_usd("gpt-5.4-mini", -1, 10)


def test_ledger_records_usage_without_customer_text_or_identifiers(tmp_path):
    path = tmp_path / "ledger.sqlite3"
    tracker = UsageLedger(str(path))
    msg_id = "wamid.private-provider-id-1234"
    details={"input_tokens":3000,"output_tokens":300,
             "input_tokens_details":{"cached_tokens":0}}
    assert tracker.record_success(msg_id, "gpt-5.4-mini", details)
    assert not tracker.record_success(msg_id, "gpt-5.4-mini", details)
    assert tracker.record_error("test-quota", "gpt-5.4-mini", "quota")
    assert tracker.record_error("test-auth", "gpt-5.4-mini", "auth")
    assert tracker.record_success("other-model", "other-model", details)
    assert not tracker.record_success("bad", "gpt-5.4-mini",
                                      {"input_tokens":2, "output_tokens":1,
                                       "input_tokens_details":{"cached_tokens":3}})
    total=tracker.summary(30)["totals"]
    assert total["requests"] == 4
    assert total["successful"] == 2
    assert total["failed"] == 2
    assert total["errors"] == {"quota":1,"auth":1}
    assert total["estimated_usd"] == pytest.approx(.0036)
    assert total["unpriced_successes"] == 1
    with tracker.db() as db:
        rows=db.execute("SELECT event_hash FROM api_usage").fetchall()
        assert msg_id not in [r["event_hash"] for r in rows]
        assert hashlib.sha256(msg_id.encode()).hexdigest() in [
            r["event_hash"] for r in rows]
    with pytest.raises(ValueError):
        tracker.summary(365)


def test_metrics_endpoint_requires_admin(tmp_path, monkeypatch):
    settings=replace(Settings(), database_path=str(tmp_path/"metrics.db"),
        demo_mode=True, ai_preview_mode=False,
        admin_username="plazai", admin_password="metrics-test-password")
    monkeypatch.setattr(main,"config",settings)
    with TestClient(main.app) as client:
        assert client.get("/api/admin/usage").status_code == 401
        a=client.get("/api/admin/usage", auth=("plazai","metrics-test-password"))
        assert a.status_code == 200
        assert a.json()["totals"]["successful"] == 0
        assert a.headers.get("Cache-Control") == "no-store"
        invalid=client.get("/api/admin/usage?days=365",
                           auth=("plazai","metrics-test-password"))
        assert invalid.status_code == 400


def test_preview_records_real_token_usage_from_mock_model(tmp_path,monkeypatch):
    class FakeMeteredModel:
        def __init__(self, api_key, model):
            self.model=model
            self.last_usage=None
        async def reply(self, history):
            self.last_usage={"input_tokens":3000,"output_tokens":300,
                             "input_tokens_details":{"cached_tokens":500}}
            return "Таҳияи смета аз ведомости корҳо оғоз мешавад."
        async def close(self): pass
    settings=replace(Settings(),database_path=str(tmp_path/"metered.db"),
        demo_mode=True, ai_preview_mode=True, openai_api_key="test-only-key",
        openai_model="gpt-5.4-mini", admin_username="plazai",
        admin_password="usage-preview-password")
    monkeypatch.setattr(main,"config",settings)
    monkeypatch.setattr(main,"AIService",FakeMeteredModel)
    with TestClient(main.app) as client:
        auth=("plazai","usage-preview-password")
        headers={"X-PLAZAI-Request":"dashboard"}
        r=client.post("/api/admin/demo",auth=auth,headers=headers,
                      json={"text":"Чӣ гуна смета таҳия мешавад?"})
        assert r.status_code==200
        import time
        totals={}
        for _ in range(40):
            totals=client.get("/api/admin/usage?days=1",auth=auth).json()["totals"]
            if totals["successful"]:
                break
            time.sleep(.05)
        assert totals["successful"]==1
        assert totals["input_tokens"]==3000
        assert totals["output_tokens"]==300
        assert totals["cached_input_tokens"]==500
        expected=((2500*.75+500*.075+300*4.5)/1_000_000)
        assert totals["estimated_usd"]==pytest.approx(expected,abs=1e-6)
