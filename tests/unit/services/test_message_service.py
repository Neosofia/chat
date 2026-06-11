from unittest.mock import patch

import pytest
from werkzeug.exceptions import BadRequest, ServiceUnavailable

from src.bootstrap.config import settings
from src.services.message_service import create_message, list_last_message_times, list_messages

pytestmark = pytest.mark.unit

INTERACTION = "00000000-0000-7000-8000-000000000003"
PATIENT = "00000000-0000-7000-8000-000000000001"


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
    with pytest.raises(BadRequest, match="user_uuid"):
        list_last_message_times(object(), [{}])


def test_list_last_message_times_returns_null_when_no_messages():
    from unittest.mock import MagicMock

    db = MagicMock()
    scalar_query = MagicMock()
    scalar_query.scalar.return_value = None
    db.query.return_value.join.return_value.filter.return_value = scalar_query

    results = list_last_message_times(db, [{"user_uuid": PATIENT}])
    assert results == [{"user_uuid": PATIENT, "last_message_at": None}]


def test_list_messages_returns_ordered_rows():
    from datetime import datetime, timezone
    from unittest.mock import MagicMock, patch
    from uuid import UUID

    message = MagicMock()
    message.message_uuid = UUID("00000000-0000-7000-8000-000000000010")
    message.chat_interaction_uuid = UUID(INTERACTION)
    message.channel = 1
    message.sender_type = "patient"
    message.sender_uuid = UUID(PATIENT)
    message.content = "hello"
    message.changed_at = datetime(2026, 6, 5, 12, 0, tzinfo=timezone.utc)

    db = MagicMock()
    list_query = MagicMock()
    list_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [message]
    db.query.return_value = list_query

    with patch("src.services.message_service.require_interaction"):
        items = list_messages(db, INTERACTION, limit=10)

    assert items[0]["content"] == "hello"
    assert items[0]["channel_label"] == "web"


def test_create_message_rejects_created_at():
    with pytest.raises(BadRequest, match="created_at"):
        create_message(
            object(),
            {
                "chat_interaction_uuid": INTERACTION,
                "sender_type": "patient",
                "content": "x",
                "created_at": "2026-06-05T12:00:00Z",
            },
        )


def test_create_message_persists_patient_sender():
    from datetime import datetime, timezone
    from unittest.mock import MagicMock, patch
    from uuid import UUID

    interaction = MagicMock()
    interaction.user_uuid = UUID(PATIENT)
    changed_at = datetime(2026, 6, 5, 12, 0, tzinfo=timezone.utc)

    db = MagicMock()

    def _refresh(item):
        item.changed_at = changed_at

    db.refresh.side_effect = _refresh

    with (
        patch("src.services.message_service.require_interaction", return_value=interaction),
        patch("src.services.message_service.list_messages", return_value=[]),
        patch("src.services.message_service.inference_configured", return_value=True),
    ):
        item = create_message(
            db,
            {
                "chat_interaction_uuid": INTERACTION,
                "sender_type": "patient",
                "content": "  hello  ",
            },
        )

    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()
    assert item["content"] == "hello"
    assert item["sender_uuid"] == PATIENT
    assert item["created_at"] == changed_at.astimezone(timezone.utc).isoformat()


def test_create_message_rejects_patient_turn_without_assistant():
    with (
        patch("src.services.message_service.list_messages", return_value=[]),
        patch("src.services.message_service.inference_configured", return_value=False),
    ):
        with pytest.raises(ServiceUnavailable, match="not available"):
            create_message(
                object(),
                {
                    "chat_interaction_uuid": INTERACTION,
                    "sender_type": "patient",
                    "content": "hello",
                },
            )
