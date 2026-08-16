"""Client OpenAI-compatible (Chat Completions + JSON)."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class LlmConfigError(RuntimeError):
    """Clé API ou config LLM manquante / invalide."""


class LlmRequestError(RuntimeError):
    """Échec d'appel au provider LLM."""


def require_llm_configured() -> None:
    if not settings.openai_api_key.strip():
        raise LlmConfigError(
            "OPENAI_API_KEY manquante. Ajoute-la dans .env (local) ou sur Render."
        )


async def chat_json(
    *,
    system: str,
    user: str,
    temperature: float = 0.1,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """Appelle le chat completions et parse la réponse JSON."""
    require_llm_configured()

    base = settings.llm_base_url.rstrip("/")
    url = f"{base}/chat/completions"
    payload = {
        "model": settings.llm_model,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, headers=headers, json=payload)
    except httpx.TimeoutException as e:
        raise LlmRequestError("Timeout lors de l'appel au LLM") from e
    except httpx.HTTPError as e:
        raise LlmRequestError(f"Erreur réseau LLM : {e}") from e

    if response.status_code >= 400:
        detail = response.text[:500]
        logger.warning("LLM HTTP %s: %s", response.status_code, detail)
        raise LlmRequestError(f"LLM HTTP {response.status_code}: {detail}")

    try:
        body = response.json()
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as e:
        raise LlmRequestError("Réponse LLM illisible") from e

    if not isinstance(content, str) or not content.strip():
        raise LlmRequestError("Réponse LLM vide")

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as e:
        raise LlmRequestError("Réponse LLM non-JSON") from e

    if not isinstance(parsed, dict):
        raise LlmRequestError("Réponse LLM : objet JSON attendu")
    return parsed
