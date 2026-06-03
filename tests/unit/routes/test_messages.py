import jwt
import pytest

pytestmark = pytest.mark.unit

PATIENT = "00000000-0000-7000-8000-000000000001"
EPISODE = "00000000-0000-7000-8000-000000000002"
SUB = "00000000-0000-7000-8000-000000000003"


def _patient_token(rsa_keypair) -> str:
    claims = {
        "sub": SUB,
        "aud": "chat",
        "exp": 9999999999,
        "iat": 1,
        "neosofia:actors": ["patient"],
        "neosofia:tenant_type": "platform",
    }
    return jwt.encode(claims, rsa_keypair["private"], algorithm="RS256")


def _auth_headers(rsa_keypair) -> dict[str, str]:
    return {"Authorization": f"Bearer {_patient_token(rsa_keypair)}"}


def test_get_messages_requires_auth(client):
    response = client.get(
        f"/api/v1/messages?care_episode_uuid={EPISODE}",
        base_url="https://localhost",
    )
    assert response.status_code == 401


def test_get_messages_requires_patient_uuid(client, rsa_keypair):
    response = client.get(
        f"/api/v1/messages?care_episode_uuid={EPISODE}",
        headers=_auth_headers(rsa_keypair),
        base_url="https://localhost",
    )
    assert response.status_code == 400


@pytest.mark.parametrize("text,fragment", [("pain is worse", "urgent"), ("feeling ok", "logged your update")])
def test_post_completion_response(text, fragment, client, rsa_keypair):
    response = client.post(
        "/api/v1/messages/completions",
        json={"messages": [{"content": text}]},
        headers=_auth_headers(rsa_keypair),
        base_url="https://localhost",
    )
    assert response.status_code == 200
    assert fragment in response.get_json()["message"].lower()
