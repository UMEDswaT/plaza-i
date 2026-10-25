"""Regression tests for Tajik/Russian language selection and Meta payload handling."""
import hashlib
import hmac
import json
from dataclasses import replace

from fastapi.testclient import TestClient

from app import main
from app.services import is_tajik
from app.settings import Settings


def test_tajik_and_russian_selection():
    assert is_tajik("Салом")
    assert is_tajik("Мехохам хонаи нав")
    assert is_tajik("Salom, mehoham loyiha")
    assert not is_tajik("Мне нужен проект")
    assert is_tajik("Ок", [{"role": "user", "body": "Ман хона мехоҳам"}])
    assert not is_tajik("Ок", [{"role": "user", "body": "Мне нужен проект"}])


def test_webhook_handles_signed_unexpected_shapes(tmp_path, monkeypatch):
    config = replace(
        Settings(),
        database_path=str(tmp_path / "test.db"),
        demo_mode=True,
        admin_password="temporary-test-password",
        meta_app_secret="local-test-secret",
        meta_phone_number_id="1234",
    )
    monkeypatch.setattr(main, "config", config)
    payloads = [
        {"object": "whatsapp_business_account", "entry": "unexpected"},
        {"object": "whatsapp_business_account", "entry": [None, {"changes": None}]},
        {"object": "whatsapp_business_account", "entry": [
            {"changes": [{"value": {"metadata": {"phone_number_id": "1234"},
               "messages": [None, {"id": "a", "from": "992900000001",
               "type": "text", "text": None}]}}]}
        ]},
    ]
    with TestClient(main.app) as client:
        for payload in payloads:
            raw = json.dumps(payload).encode("utf-8")
            signature = "sha256=" + hmac.new(
                b"local-test-secret", raw, hashlib.sha256
            ).hexdigest()
            result = client.post(
                "/webhook", content=raw,
                headers={"x-hub-signature-256": signature}
            )
            assert result.status_code == 200
        assert main.store.list_chats() == []
