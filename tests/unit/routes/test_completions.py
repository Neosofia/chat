from unittest.mock import patch

import jwt
import pytest

pytestmark = pytest.mark.unit

INTERACTION = "00000000-0000-7000-8000-000000000003"
PATIENT = "00000000-0000-7000-8000-000000000001"
OTHER = "00000000-0000-7000-8000-000000000099"
TENANT = "00000000-0000-7000-8000-000000000010"


def _patient_token(rsa_keypair) -> str:
    claims = {
        "sub": PATIENT,
        "aud": "chat",
        "exp": 9999999999,
        "iat": 1,
        "neosofia:actors": ["patient"],
        "neosofia:tenant_uuid": TENANT,
    }
    return jwt.encode(claims, rsa_keypair["private"], algorithm="RS256")


def _auth_headers(rsa_keypair) -> dict[str, str]:
    return {"Authorization": f"Bearer {_patient_token(rsa_keypair)}"}


def _messages_url(user_uuid: str = PATIENT, interaction_uuid: str = INTERACTION) -> str:
    return f"/api/v1/users/{user_uuid}/interactions/{interaction_uuid}/messages"


def test_get_messages_requires_auth(client):
    response = client.get(
        _messages_url(),
        base_url="https://localhost",
    )
    assert response.status_code == 401


@patch("src.routes.interactions.start_chat_session")
@patch("src.routes.interactions.require_interaction_for_user")
def test_post_completion_session_start(
    mock_require_for_user,
    mock_start,
    client,
    rsa_keypair,
):
    mock_require_for_user.return_value = object()
    mock_start.return_value = {"message": "Hello", "assistant_message": None}
    response = client.post(
        f"/api/v1/users/{PATIENT}/interactions/{INTERACTION}/completions",
        json={"session_start": True},
        headers=_auth_headers(rsa_keypair),
        base_url="https://localhost",
    )
    assert response.status_code == 200
    mock_start.assert_called_once()


@patch("src.routes.interactions.complete_user_turn")
@patch("src.routes.interactions.require_interaction_for_user")
def test_post_completion_user_turn(
    mock_require_for_user,
    mock_complete,
    client,
    rsa_keypair,
):
    mock_require_for_user.return_value = object()
    mock_complete.return_value = {
        "message": "Take it easy today.",
        "user_message": {"message_uuid": "00000000-0000-7000-8000-000000000099"},
        "assistant_message": {"message_uuid": "00000000-0000-7000-8000-000000000100"},
    }
    response = client.post(
        f"/api/v1/users/{PATIENT}/interactions/{INTERACTION}/completions",
        json={"content": "pain is worse"},
        headers=_auth_headers(rsa_keypair),
        base_url="https://localhost",
    )
    assert response.status_code == 200
    assert response.get_json()["message"] == "Take it easy today."
    mock_complete.assert_called_once()
