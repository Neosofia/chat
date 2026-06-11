from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.bootstrap.config import settings
from src.services.inference_health import check_inference_health, inference_models_url

pytestmark = pytest.mark.unit


def test_inference_models_url_derives_from_completions_path():
    with patch.object(
        settings,
        "inference_completions_url",
        "https://inference.example/v1/chat/completions",
    ):
        assert inference_models_url() == "https://inference.example/v1/models"


def test_check_inference_health_reports_unconfigured():
    with patch("src.services.inference_health.inference_configured", return_value=False):
        status, detail = check_inference_health()
    assert status == "degraded"
    assert detail == "AI assistant inference is not configured"


@patch("src.services.inference_health.httpx.get")
def test_check_inference_health_reports_ok(mock_get):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    with (
        patch("src.services.inference_health.inference_configured", return_value=True),
        patch.object(settings, "inference_api_key", "test-key"),
        patch.object(
            settings,
            "inference_completions_url",
            "https://inference.example/v1/chat/completions",
        ),
    ):
        status, detail = check_inference_health()

    assert status == "ok"
    assert detail is None
    mock_get.assert_called_once()


@patch("src.services.inference_health.httpx.get", side_effect=httpx.HTTPError("boom"))
def test_check_inference_health_reports_unreachable(mock_get):
    with (
        patch("src.services.inference_health.inference_configured", return_value=True),
        patch.object(settings, "inference_api_key", "test-key"),
        patch.object(
            settings,
            "inference_completions_url",
            "https://inference.example/v1/chat/completions",
        ),
    ):
        status, detail = check_inference_health()

    assert status == "degraded"
    assert detail == "AI assistant inference is not responding"
