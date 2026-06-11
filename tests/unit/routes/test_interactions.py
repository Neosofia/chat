from unittest.mock import patch

import jwt
import pytest

pytestmark = pytest.mark.unit

PATIENT = "00000000-0000-7000-8000-000000000001"
OTHER = "00000000-0000-7000-8000-000000000099"
TENANT = "00000000-0000-7000-8000-000000000010"


def _auth_headers(rsa_keypair) -> dict[str, str]:
    token = jwt.encode(
        {
            "sub": PATIENT,
            "aud": "chat",
            "exp": 9999999999,
            "iat": 1,
            "neosofia:actors": ["patient"],
            "neosofia:tenant_uuid": TENANT,
        },
        rsa_keypair["private"],
        algorithm="RS256",
    )
    return {"Authorization": f"Bearer {token}"}


def _care_episode_service_headers(rsa_keypair) -> dict[str, str]:
    token = jwt.encode(
        {
            "sub": "care-episode",
            "aud": "chat",
            "exp": 9999999999,
            "iat": 1,
            "azp": "care-episode",
            "neosofia:token_type": "service",
        },
        rsa_keypair["private"],
        algorithm="RS256",
    )
    return {"Authorization": f"Bearer {token}"}


@patch("src.routes.interactions.list_last_message_times")
def test_get_last_activity(mock_list, client, rsa_keypair):
    mock_list.return_value = [{"user_uuid": PATIENT, "last_message_at": "2026-06-05T12:00:00+00:00"}]
    response = client.get(
        f"/api/v1/users/{PATIENT}/last-activity",
        headers=_auth_headers(rsa_keypair),
        base_url="https://localhost",
    )
    assert response.status_code == 200
    assert response.get_json()["user_uuid"] == PATIENT


def test_get_last_activity_rejects_other_patient(client, rsa_keypair):
    response = client.get(
        f"/api/v1/users/{OTHER}/last-activity",
        headers=_auth_headers(rsa_keypair),
        base_url="https://localhost",
    )
    assert response.status_code == 403


@patch("src.routes.interactions.list_interactions")
def test_get_interactions(mock_list, client, rsa_keypair):
    mock_list.return_value = [{"chat_interaction_uuid": "00000000-0000-7000-8000-000000000003"}]
    response = client.get(
        f"/api/v1/users/{PATIENT}/interactions",
        headers=_auth_headers(rsa_keypair),
        base_url="https://localhost",
    )
    assert response.status_code == 200


def test_post_interaction_rejects_other_patient(client, rsa_keypair):
    response = client.post(
        f"/api/v1/users/{OTHER}/interactions",
        json={},
        headers=_auth_headers(rsa_keypair),
        base_url="https://localhost",
    )
    assert response.status_code == 403


@patch("src.routes.interactions.create_interaction")
def test_post_interaction_rejects_client_context(mock_create, client, rsa_keypair):
    response = client.post(
        f"/api/v1/users/{PATIENT}/interactions",
        json={"context": {"procedure_name": "appendectomy"}},
        headers=_auth_headers(rsa_keypair),
        base_url="https://localhost",
    )
    assert response.status_code == 400
    mock_create.assert_not_called()


@patch("src.routes.interactions.create_interaction")
def test_post_interaction_accepts_care_episode_service_context(mock_create, client, rsa_keypair):
    mock_create.return_value = {"chat_interaction_uuid": "00000000-0000-7000-8000-000000000003"}
    response = client.post(
        f"/api/v1/users/{PATIENT}/interactions",
        json={"context": {"procedure_name": "appendectomy"}},
        headers=_care_episode_service_headers(rsa_keypair),
        base_url="https://localhost",
    )
    assert response.status_code == 201
    mock_create.assert_called_once()
    assert mock_create.call_args.kwargs["context"] == {"procedure_name": "appendectomy"}


@patch("src.routes.interactions.create_interaction")
def test_post_interaction_rejects_missing_context(mock_create, client, rsa_keypair):
    response = client.post(
        f"/api/v1/users/{PATIENT}/interactions",
        json={},
        headers=_auth_headers(rsa_keypair),
        base_url="https://localhost",
    )
    assert response.status_code == 400
    mock_create.assert_not_called()


@patch("src.routes.interactions.create_interaction")
def test_post_interaction_rejects_empty_context_from_care_episode(mock_create, client, rsa_keypair):
    response = client.post(
        f"/api/v1/users/{PATIENT}/interactions",
        json={"context": {}},
        headers=_care_episode_service_headers(rsa_keypair),
        base_url="https://localhost",
    )
    assert response.status_code == 400
    mock_create.assert_not_called()


@patch("src.routes.interactions.list_messages")
@patch("src.routes.interactions.require_interaction_for_user")
def test_get_messages(mock_require, mock_list, client, rsa_keypair):
    mock_require.return_value = object()
    mock_list.return_value = [{"message_uuid": "00000000-0000-7000-8000-000000000010"}]
    response = client.get(
        f"/api/v1/users/{PATIENT}/interactions/00000000-0000-7000-8000-000000000003/messages",
        headers=_auth_headers(rsa_keypair),
        base_url="https://localhost",
    )
    assert response.status_code == 200
    assert len(response.get_json()["items"]) == 1


@patch("src.routes.interactions.create_message")
@patch("src.routes.interactions.require_interaction_for_user")
def test_post_message(mock_require, mock_create, client, rsa_keypair):
    mock_require.return_value = object()
    mock_create.return_value = {"message_uuid": "00000000-0000-7000-8000-000000000010"}
    response = client.post(
        f"/api/v1/users/{PATIENT}/interactions/00000000-0000-7000-8000-000000000003/messages",
        json={"sender_type": "patient", "content": "hello"},
        headers=_auth_headers(rsa_keypair),
        base_url="https://localhost",
    )
    assert response.status_code == 201
