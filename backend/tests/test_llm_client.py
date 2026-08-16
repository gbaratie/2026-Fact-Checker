"""Tests client LLM avec httpx mocké."""

import json

import httpx
import pytest

from app.services import llm_client


@pytest.fixture(autouse=True)
def _llm_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(llm_client.settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(llm_client.settings, "llm_model", "gpt-4o-mini")
    monkeypatch.setattr(llm_client.settings, "llm_base_url", "https://api.openai.com/v1")


@pytest.mark.asyncio
async def test_chat_json_parses_content(monkeypatch: pytest.MonkeyPatch):
    payload = {"topic_slugs": ["immigration"], "confidence": 0.8}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/chat/completions")
        body = json.loads(request.content.decode())
        assert body["response_format"] == {"type": "json_object"}
        assert body["model"] == "gpt-4o-mini"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": json.dumps(payload)}},
                ]
            },
        )

    transport = httpx.MockTransport(handler)

    class FakeAsyncClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(llm_client.httpx, "AsyncClient", FakeAsyncClient)

    result = await llm_client.chat_json(system="sys", user="user")
    assert result == payload


@pytest.mark.asyncio
async def test_chat_json_requires_api_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(llm_client.settings, "openai_api_key", "")
    with pytest.raises(llm_client.LlmConfigError):
        await llm_client.chat_json(system="sys", user="user")


@pytest.mark.asyncio
async def test_chat_json_http_error(monkeypatch: pytest.MonkeyPatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="unauthorized")

    transport = httpx.MockTransport(handler)

    class FakeAsyncClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(llm_client.httpx, "AsyncClient", FakeAsyncClient)

    with pytest.raises(llm_client.LlmRequestError, match="401"):
        await llm_client.chat_json(system="sys", user="user")
