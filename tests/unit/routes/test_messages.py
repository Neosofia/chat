import pytest

pytestmark = pytest.mark.unit

PATIENT = "00000000-0000-7000-8000-000000000001"
EPISODE = "00000000-0000-7000-8000-000000000002"


def test_get_messages_requires_patient_uuid(client):
    response = client.get(
        f"/api/v1/messages?care_episode_uuid={EPISODE}",
        base_url="https://localhost",
    )
    assert response.status_code == 400


@pytest.mark.parametrize("text,fragment", [("pain is worse", "urgent"), ("feeling ok", "logged your update")])
def test_post_completion_response(text, fragment, client):
    response = client.post(
        "/api/v1/messages/completions",
        json={"messages": [{"content": text}]},
        base_url="https://localhost",
    )
    assert response.status_code == 200
    assert fragment in response.get_json()["message"].lower()
