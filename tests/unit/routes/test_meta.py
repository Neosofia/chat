import pytest

pytestmark = pytest.mark.unit


def test_get_enums_is_public(client):
    response = client.get("/meta/enums", base_url="https://localhost")
    assert response.status_code == 200
    body = response.get_json()
    assert body["enums"]["ChatChannel"] == {
        "1": "web",
        "2": "mobile_app",
        "3": "sms",
    }
    assert body["enums"]["MessageSenderType"] == {
        "ai_agent": "ai_agent",
        "clinician": "clinician",
        "patient": "patient",
    }
    assert body["enums"]["InterventionSenderType"] == {"clinician": "clinician"}
    assert body["completion"] == {
        "user_sender_type": "patient",
        "assistant_sender_type": "ai_agent",
    }
    assert body["assistant"] == {"available": False}
