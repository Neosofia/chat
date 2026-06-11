from __future__ import annotations

import httpx

from src.bootstrap.config import inference_configured, settings

INFERENCE_HEALTH_TIMEOUT_SECONDS = 5.0


def inference_models_url() -> str:
    base = settings.inference_completions_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return f"{base[: -len('/chat/completions')]}/models"
    return f"{base}/models"


def check_inference_health() -> tuple[str, str | None]:
    """Return overall LLM dependency status: ('ok', None) or ('degraded', detail)."""
    if not inference_configured():
        return "degraded", "AI assistant inference is not configured"

    try:
        response = httpx.get(
            inference_models_url(),
            headers={"Authorization": f"Bearer {settings.inference_api_key}"},
            timeout=INFERENCE_HEALTH_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        return "degraded", "AI assistant inference is not responding"

    return "ok", None
