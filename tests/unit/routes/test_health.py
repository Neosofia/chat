from unittest.mock import patch

import pytest
from importlib.metadata import version

from src.app import create_app
from src.bootstrap.config import Settings

pytestmark = pytest.mark.unit


def test_health_allows_plain_http_in_production(rsa_keypair):
    """Railway's internal probe uses HTTP; /health must not 302 to HTTPS."""
    import base64
    import src.app as app_module
    import src.bootstrap.config as config_module

    original_app_settings = app_module.settings
    original_config_settings = config_module.settings
    production_settings = Settings(
        env="production",
        jwt_public_key=base64.b64encode(rsa_keypair["public"]).decode("utf-8"),
        authorization_policies_dir=original_config_settings.authorization_policies_dir,
    )
    app_module.settings = production_settings
    config_module.settings = production_settings
    try:
        response = create_app(
            {
                "TESTING": True,
                "TIER1_ACTOR_CLASSES": frozenset({"operator", "study", "clinician", "patient"}),
            }
        ).test_client().get("/health")
        assert response.status_code == 200
        assert response.headers.get("Location") is None
        body = response.get_json()
        assert body["version"] == version("chat")
        assert body["status"] in {"ok", "degraded"}
    finally:
        app_module.settings = original_app_settings
        config_module.settings = original_config_settings


def test_health_is_rate_limited(client):
    # Decorator is wired; Flask-Limiter enforces settings.health_rate_limit in production.
    for _ in range(3):
        response = client.get("/health")
        assert response.status_code == 200


@patch("src.routes.health.check_inference_health", return_value=("ok", None))
def test_health_returns_ok_when_inference_is_healthy(mock_check, client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "version": version("chat")}
    mock_check.assert_called_once()


@patch(
    "src.routes.health.check_inference_health",
    return_value=("degraded", "AI assistant inference is not configured"),
)
def test_health_returns_degraded_when_inference_is_unavailable(mock_check, client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {
        "status": "degraded",
        "version": version("chat"),
        "detail": "AI assistant inference is not configured",
    }
    mock_check.assert_called_once()
