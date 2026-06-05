import pytest
from werkzeug.exceptions import BadRequest

from src.services.message_service import create_message, list_last_message_times, list_messages

pytestmark = pytest.mark.unit

INTERACTION = "00000000-0000-7000-8000-000000000003"
PATIENT = "00000000-0000-7000-8000-000000000001"
EPISODE = "00000000-0000-7000-8000-000000000002"


@pytest.mark.parametrize(
    "payload,match",
    [
        ({"sender_type": "patient", "content": "x"}, "chat_interaction_uuid"),
        ({"chat_interaction_uuid": INTERACTION, "content": "x"}, "sender_type"),
        ({"chat_interaction_uuid": INTERACTION, "sender_type": "patient"}, "content"),
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
                "chat_interaction_uuid": INTERACTION,
                "sender_type": sender_type,
                "content": "x",
            },
        )


def test_list_messages_requires_interaction():
    with pytest.raises(BadRequest, match="chat_interaction_uuid"):
        list_messages(object(), None)


def test_list_last_message_times_rejects_incomplete_items():
    with pytest.raises(BadRequest, match="patient_uuid and care_episode_uuid"):
        list_last_message_times(object(), [{"patient_uuid": PATIENT}])
