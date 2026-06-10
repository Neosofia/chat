from unittest.mock import patch

import jwt
import pytest

from src.bootstrap.config import settings

pytestmark = pytest.mark.unit

INTERACTION = "00000000-0000-7000-8000-000000000003"
SUB = "00000000-0000-7000-8000-000000000004"


def _patient_token(rsa_keypair) -> str:
    claims = {
        "sub": SUB,
        "aud": "chat",
        "exp": 9999999999,
        "iat": 1,
        "neosofia:actors": ["patient"],
        "neosofia:tenant_type": "platform",
        "neosofia:tenant_uuid": "00000000-0000-7000-8000-000000000010",
    }
    return jwt.encode(claims, rsa_keypair["private"], algorithm="RS256")


def _auth_headers(rsa_keypair) -> dict[str, str]:
    return {"Authorization": f"Bearer {_patient_token(rsa_keypair)}"}


def test_get_messages_requires_auth(client):
    response = client.get(
        f"/api/v1/messages?chat_interaction_uuid={INTERACTION}",
        base_url="https://localhost",
    )
    assert response.status_code == 401


def test_get_messages_requires_chat_interaction_uuid(client, rsa_keypair):
    response = client.get(
        "/api/v1/messages",
        headers=_auth_headers(rsa_keypair),
        base_url="https://localhost",
    )
    assert response.status_code == 400


def _fake_created_message(_db, payload: dict) -> dict:
    return {
        "message_uuid": "00000000-0000-7000-8000-000000000099",
        "chat_interaction_uuid": payload["chat_interaction_uuid"],
        "channel": payload.get("channel", 1),
        "channel_label": "web",
        "sender_type": payload["sender_type"],
        "sender_uuid": payload.get("sender_uuid"),
        "content": payload["content"],
        "created_at": "2026-06-05T12:00:00+00:00",
    }


@pytest.mark.parametrize("text,fragment", [("pain is worse", "urgent"), ("feeling ok", "logged your update")])
@patch("src.services.completion_service.list_messages")
@patch("src.services.completion_service.create_message")
@patch("src.services.completion_service.require_interaction")
def test_post_completion_response(mock_require, mock_create, mock_list, text, fragment, client, rsa_keypair):
    mock_require.return_value = type(
        "Interaction",
        (),
        {
            "patient_uuid": "00000000-0000-7000-8000-000000000001",
            "context": None,
        },
    )()
    mock_create.side_effect = _fake_created_message
    mock_list.return_value = [{"sender_type": "patient", "content": text}]
    with patch.object(settings, "inference_api_key", None):
        response = client.post(
            "/api/v1/messages/completions",
            json={
                "chat_interaction_uuid": INTERACTION,
                "content": text,
            },
            headers=_auth_headers(rsa_keypair),
            base_url="https://localhost",
        )
    assert response.status_code == 200
    body = response.get_json()
    assert fragment in body["message"].lower()
    assert body["patient_message"]["sender_type"] == "patient"
    assert body["assistant_message"]["sender_type"] == "ai_agent"


@patch("src.routes.messages.log_request_handled")
@patch("src.routes.messages.start_chat_session")
def test_post_session_start_completion(mock_start, mock_log, client, rsa_keypair):
    mock_start.return_value = {
        "message": "Hi Alex — how are you feeling today?",
        "assistant_message": {
            "message_uuid": "00000000-0000-7000-8000-000000000099",
            "sender_type": "ai_agent",
            "content": "Hi Alex — how are you feeling today?",
        },
    }
    response = client.post(
        "/api/v1/messages/completions",
        json={
            "chat_interaction_uuid": INTERACTION,
            "session_start": True,
        },
        headers=_auth_headers(rsa_keypair),
        base_url="https://localhost",
    )
    assert response.status_code == 200
    body = response.get_json()
    assert "how are you feeling" in body["message"].lower()
    assert body["assistant_message"]["sender_type"] == "ai_agent"
    assert "patient_message" not in body
    mock_log.assert_called_once()
    assert mock_log.call_args.args[0] == "completion_session_start"
    assert mock_log.call_args.args[1] == 200


def test_post_completion_requires_thread_fields(client, rsa_keypair):
    response = client.post(
        "/api/v1/messages/completions",
        json={"content": "hello"},
        headers=_auth_headers(rsa_keypair),
        base_url="https://localhost",
    )
    assert response.status_code == 400
