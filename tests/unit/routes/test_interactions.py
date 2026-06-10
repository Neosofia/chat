from unittest.mock import patch

import jwt
import pytest

pytestmark = pytest.mark.unit

PATIENT = "00000000-0000-7000-8000-000000000001"
EPISODE = "00000000-0000-7000-8000-000000000002"
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


def test_get_interactions_requires_patient_uuid(client, rsa_keypair):
    response = client.get(
        f"/api/v1/interactions?care_episode_uuid={EPISODE}",
        headers=_auth_headers(rsa_keypair),
        base_url="https://localhost",
    )
    assert response.status_code == 400


def test_get_interactions_requires_auth(client):
    response = client.get(
        f"/api/v1/interactions?patient_uuid={PATIENT}&care_episode_uuid={EPISODE}",
        base_url="https://localhost",
    )
    assert response.status_code == 401


@patch("src.routes.interactions.list_interactions")
def test_get_interactions_returns_items(mock_list, client, rsa_keypair):
    mock_list.return_value = [
        {
            "chat_interaction_uuid": INTERACTION,
            "patient_uuid": PATIENT,
            "care_episode_uuid": EPISODE,
            "started_at": "2026-06-05T12:00:00+00:00",
            "last_message_at": None,
            "message_count": 0,
            "preview": None,
        }
    ]
    response = client.get(
        f"/api/v1/interactions?patient_uuid={PATIENT}&care_episode_uuid={EPISODE}",
        headers=_auth_headers(rsa_keypair),
        base_url="https://localhost",
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["items"][0]["chat_interaction_uuid"] == INTERACTION


@patch("src.routes.interactions.log_request_handled")
@patch("src.routes.interactions.create_interaction")
def test_post_interaction_creates_shell(mock_create, mock_log, client, rsa_keypair):
    mock_create.return_value = {
        "chat_interaction_uuid": INTERACTION,
        "patient_uuid": PATIENT,
        "care_episode_uuid": EPISODE,
        "started_at": "2026-06-05T12:00:00+00:00",
        "last_message_at": None,
        "message_count": 0,
        "preview": None,
    }
    response = client.post(
        "/api/v1/interactions",
        json={"patient_uuid": PATIENT, "care_episode_uuid": EPISODE},
        headers=_auth_headers(rsa_keypair),
        base_url="https://localhost",
    )
    assert response.status_code == 201
    assert response.get_json()["chat_interaction_uuid"] == INTERACTION
    mock_log.assert_called_once()
    assert mock_log.call_args.args == ("interaction_create", 201)
    assert mock_log.call_args.kwargs["care_episode_uuid"] == EPISODE


def test_post_interaction_requires_fields(client, rsa_keypair):
    response = client.post(
        "/api/v1/interactions",
        json={"patient_uuid": PATIENT},
        headers=_auth_headers(rsa_keypair),
        base_url="https://localhost",
    )
    assert response.status_code == 400
