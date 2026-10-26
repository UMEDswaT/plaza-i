"""No-network checks for optional FreeLLMAPI synthetic preview."""
import asyncio
from dataclasses import replace

import httpx
import pytest

from app.freellmapi import FreeLLMAPIService
from app.settings import Settings
from app.services import AIServiceError


def test_preview_gate_and_url_validation():
    cfg = replace(Settings(), ai_provider="freellmapi",
                  freellmapi_api_key="fake-key", freellmapi_model="auto",
                  admin_password="test-admin-password-long",
                  demo_mode=True, ai_preview_mode=True)
    cfg.check()
    with pytest.raises(RuntimeError, match="DEMO_MODE"):
        replace(cfg, demo_mode=False).check()
    with pytest.raises(RuntimeError, match="API key"):
        replace(cfg, freellmapi_api_key="").check()
    with pytest.raises(RuntimeError, match="endpoint"):
        replace(cfg, freellmapi_base_url="http://untrusted.example/v1").check()
    with pytest.raises(ValueError, match="HTTPS"):
        FreeLLMAPIService("fake-key", "auto", "http://untrusted.example/v1")


def test_mock_chat_completions_and_usage():
    calls = []

    def handler(request):
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer test-unified-key"
        data = __import__("json").loads(request.content)
        assert data["model"] == "auto"
        assert data["stream"] is False
        assert data["messages"][0]["role"] == "system"
        assert "PLAZA-I" in data["messages"][0]["content"]
        assert data["messages"][-1]["content"] == "Ман дизайни хона мехоҳам"
        calls.append(1)
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "Барои дизайн масоҳати хона чанд аст?"}}],
            "usage": {"prompt_tokens": 110, "completion_tokens": 15}
        })

    async def run():
        svc = FreeLLMAPIService("test-unified-key", "auto", "http://127.0.0.1:3001/v1")
        await svc.client.aclose()
        svc.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            answer = await svc.reply([{"role": "user", "body": "Ман дизайни хона мехоҳам"}])
            assert "масоҳати хона" in answer
            assert svc.model == "freellmapi/auto"
            assert svc.last_usage["input_tokens"] == 110
            assert svc.last_usage["output_tokens"] == 15
            assert len(calls) == 1
        finally:
            await svc.close()
    asyncio.run(run())


def test_rejects_provider_pricing_and_rate_limits():
    attempts = []

    def handler(request):
        attempts.append(1)
        if len(attempts) == 1:
            return httpx.Response(200, json={
                "choices": [{"message": {"content": "Нарх 75 сомонӣ аст."}}]})
        return httpx.Response(429)

    async def run():
        svc = FreeLLMAPIService("key", "auto", "https://router.example/v1")
        await svc.client.aclose()
        svc.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            answer = await svc.reply([{"role": "user", "body": "Ман мехоҳам хонаи нав созам"}])
            assert "менеҷер" in answer
            with pytest.raises(AIServiceError) as exc:
                await svc.reply([{"role": "user", "body": "Ассалому алейкум"}])
            assert exc.value.code == "limit"
            with pytest.raises(AIServiceError) as exc_again:
                await svc.reply([{"role": "user", "body": "Салом"}])
            assert exc_again.value.code == "limit"
            assert len(attempts) == 2  # circuit breaker prevents extra calls
        finally:
            await svc.close()
    asyncio.run(run())


def test_invalid_response_cannot_pass_as_ai_answer():
    async def run():
        svc = FreeLLMAPIService("key", "auto", "https://router.example/v1")
        await svc.client.aclose()
        svc.client = httpx.AsyncClient(transport=httpx.MockTransport(
            lambda req: httpx.Response(200, json={"choices": []})))
        try:
            with pytest.raises(AIServiceError) as exc:
                await svc.reply([{"role": "user", "body": "Салом"}])
            assert exc.value.code == "other"
        finally:
            await svc.close()
    asyncio.run(run())
