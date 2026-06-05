from __future__ import annotations

import json

from werkzeug.exceptions import BadRequest

CONTEXT_MAX_BYTES = 8192


def normalize_interaction_context(context) -> dict | None:
    if context is None:
        return None
    if not isinstance(context, dict):
        raise BadRequest("context must be a JSON object")

    normalized: dict[str, object] = {}
    for key, value in context.items():
        key_str = str(key).strip()
        if not key_str:
            continue
        if value is None:
            normalized[key_str] = None
            continue
        if isinstance(value, bool):
            normalized[key_str] = value
            continue
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            normalized[key_str] = value
            continue
        if isinstance(value, str):
            trimmed = value.strip()
            if trimmed:
                normalized[key_str] = trimmed
            continue
        raise BadRequest("context values must be strings, numbers, booleans, or null")

    if not normalized:
        return None

    encoded = json.dumps(normalized, separators=(",", ":"), sort_keys=True)
    if len(encoded.encode("utf-8")) > CONTEXT_MAX_BYTES:
        raise BadRequest("context exceeds maximum size")
    return normalized
