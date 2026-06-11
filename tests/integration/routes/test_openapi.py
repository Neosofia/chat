import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


def test_openapi_spec_contains_core_paths():
    root = Path(__file__).resolve().parents[3]
    spec = json.loads((root / "openapi.json").read_text())

    assert spec["openapi"] == "3.0.3"
    assert spec["info"]["title"] == "Chat Service API"
    assert "/health" in spec["paths"]
    assert "/meta/enums" in spec["paths"]
    assert "/api/v1/users/{user_uuid}/interactions" in spec["paths"]
    assert "/api/v1/users/{user_uuid}/interactions/{chat_interaction_uuid}/messages" in spec["paths"]
    assert "/api/v1/users/{user_uuid}/interactions/{chat_interaction_uuid}/completions" in spec["paths"]
    assert "/api/v1/users/{user_uuid}/last-activity" in spec["paths"]
    assert spec["info"]["version"] == "0.4.0"


def test_openapi_spec_defines_error_schema():
    root = Path(__file__).resolve().parents[3]
    spec = json.loads((root / "openapi.json").read_text())

    error_schema = spec["components"]["schemas"]["ErrorResponse"]
    assert error_schema["required"] == ["error"]
    assert "authorization_unavailable" in error_schema["properties"]["error"]["enum"]
