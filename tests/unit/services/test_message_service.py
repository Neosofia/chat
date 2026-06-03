import pytest
from werkzeug.exceptions import BadRequest

from src.services.message_service import create_message, list_last_message_times, list_messages

pytestmark = pytest.mark.unit

PATIENT = "00000000-0000-7000-8000-000000000001"
EPISODE = "00000000-0000-7000-8000-000000000002"


@pytest.mark.parametrize(
    "payload,match",
    [
        ({"care_episode_uuid": EPISODE, "sender_type": "patient", "content": "x"}, "patient_uuid"),
        ({"patient_uuid": PATIENT, "sender_type": "patient", "content": "x"}, "care_episode_uuid"),
        ({"patient_uuid": PATIENT, "care_episode_uuid": EPISODE, "content": "x"}, "sender_type"),
    ],
)
def test_create_message_rejects_missing_fields(payload, match):
    with pytest.raises(BadRequest, match=match):
        create_message(object(), payload)


@pytest.mark.parametrize("sender_type", ["nurse", "bot"])
def test_create_message_rejects_invalid_sender_type(sender_type):
    with pytest.raises(BadRequest, match="sender_type"):
        create_message(
            object(),
            {
                "patient_uuid": PATIENT,
                "care_episode_uuid": EPISODE,
                "sender_type": sender_type,
                "content": "x",
            },
        )


def test_list_messages_requires_episode():
    with pytest.raises(BadRequest, match="care_episode_uuid"):
        list_messages(object(), PATIENT, None)


def test_list_last_message_times_rejects_incomplete_items():
    with pytest.raises(BadRequest, match="patient_uuid and care_episode_uuid"):
        list_last_message_times(object(), [{"patient_uuid": PATIENT}])
