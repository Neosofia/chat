import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from werkzeug.exceptions import BadRequest, NotFound

from src.models.chat_interaction import ChatInteraction
from src.services.interaction_service import (
    _interaction_preview,
    _preview_text,
    create_interaction,
    get_latest_interaction_uuid,
    list_interactions,
    require_interaction,
)

pytestmark = pytest.mark.unit

PATIENT = "00000000-0000-7000-8000-000000000001"
EPISODE = "00000000-0000-7000-8000-000000000002"
INTERACTION = "00000000-0000-7000-8000-000000000003"


def test_preview_text_truncates_long_content():
    assert _preview_text("  " + ("x" * 100) + "  ").endswith("…")
    assert _preview_text("short") == "short"


def test_interaction_preview_prefers_patient_message():
    db = MagicMock()
    patient_query = MagicMock()
    patient_query.filter.return_value.filter.return_value.order_by.return_value.first.return_value = (
        "Patient question about pain",
    )
    db.query.return_value = patient_query

    preview = _interaction_preview(db, uuid.UUID(INTERACTION))
    assert preview == "Patient question about pain"


def test_interaction_preview_falls_back_to_latest_message():
    db = MagicMock()
    patient_query = MagicMock()
    patient_query.filter.return_value.filter.return_value.order_by.return_value.first.return_value = None
    any_query = MagicMock()
    any_query.filter.return_value.order_by.return_value.first.return_value = ("Assistant reply",)
    db.query.side_effect = [patient_query, any_query]

    preview = _interaction_preview(db, uuid.UUID(INTERACTION))
    assert preview == "Assistant reply"


def test_interaction_preview_returns_none_without_messages():
    db = MagicMock()
    empty_query = MagicMock()
    empty_query.filter.return_value.filter.return_value.order_by.return_value.first.return_value = None
    empty_query.filter.return_value.order_by.return_value.first.return_value = None
    db.query.side_effect = [empty_query, empty_query]

    assert _interaction_preview(db, uuid.UUID(INTERACTION)) is None


def test_create_interaction_requires_fields():
    with pytest.raises(BadRequest, match="patient_uuid and care_episode_uuid"):
        create_interaction(object(), "", EPISODE)


def test_create_interaction_returns_shell():
    db = MagicMock()
    now = datetime(2026, 6, 5, 12, 0, tzinfo=timezone.utc)

    def refresh(interaction: ChatInteraction) -> None:
        interaction.chat_interaction_uuid = uuid.UUID(INTERACTION)
        interaction.changed_at = now

    db.refresh.side_effect = refresh

    result = create_interaction(
        db,
        PATIENT,
        EPISODE,
        context={"patient_first_name": "Alex"},
    )
    assert result["chat_interaction_uuid"] == INTERACTION
    assert result["patient_uuid"] == PATIENT
    assert result["care_episode_uuid"] == EPISODE
    assert result["message_count"] == 0
    added = db.add.call_args.args[0]
    assert added.context == {"patient_first_name": "Alex"}
    db.add.assert_called_once()
    db.commit.assert_called_once()


def test_list_interactions_requires_fields():
    with pytest.raises(BadRequest, match="patient_uuid and care_episode_uuid"):
        list_interactions(object(), PATIENT, "")


def test_list_interactions_returns_preview_for_threads_with_messages():
    db = MagicMock()
    interaction = ChatInteraction(
        chat_interaction_uuid=uuid.UUID(INTERACTION),
        patient_uuid=uuid.UUID(PATIENT),
        care_episode_uuid=uuid.UUID(EPISODE),
        changed_by_uuid=uuid.UUID("00000000-0000-7000-8000-000000000000"),
        changed_by_type=2,
    )
    interaction.changed_at = datetime(2026, 6, 5, 10, 0, tzinfo=timezone.utc)
    last_message_at = datetime(2026, 6, 5, 11, 0, tzinfo=timezone.utc)

    list_query = MagicMock()
    list_query.outerjoin.return_value.filter.return_value.filter.return_value.group_by.return_value.order_by.return_value.all.return_value = [
        (interaction, 2, last_message_at),
    ]

    preview_query = MagicMock()
    preview_query.filter.return_value.filter.return_value.order_by.return_value.first.return_value = (
        "How is my pain?",
    )
    db.query.side_effect = [list_query, preview_query]

    items = list_interactions(db, PATIENT, EPISODE)
    assert len(items) == 1
    assert items[0]["preview"] == "How is my pain?"
    assert items[0]["message_count"] == 2
    assert items[0]["last_message_at"] == last_message_at.astimezone(timezone.utc).isoformat()


def test_get_latest_interaction_uuid_returns_first_item():
    db = MagicMock()
    interaction = ChatInteraction(
        chat_interaction_uuid=uuid.UUID(INTERACTION),
        patient_uuid=uuid.UUID(PATIENT),
        care_episode_uuid=uuid.UUID(EPISODE),
        changed_by_uuid=uuid.UUID("00000000-0000-7000-8000-000000000000"),
        changed_by_type=2,
    )
    interaction.changed_at = datetime(2026, 6, 5, 10, 0, tzinfo=timezone.utc)

    list_query = MagicMock()
    list_query.outerjoin.return_value.filter.return_value.filter.return_value.group_by.return_value.order_by.return_value.all.return_value = [
        (interaction, 0, None),
    ]
    db.query.return_value = list_query

    assert get_latest_interaction_uuid(db, PATIENT, EPISODE) == INTERACTION


def test_get_latest_interaction_uuid_returns_none_when_empty():
    db = MagicMock()
    list_query = MagicMock()
    list_query.outerjoin.return_value.filter.return_value.filter.return_value.group_by.return_value.order_by.return_value.all.return_value = []
    db.query.return_value = list_query

    assert get_latest_interaction_uuid(db, PATIENT, EPISODE) is None


def test_require_interaction_requires_uuid():
    with pytest.raises(BadRequest, match="chat_interaction_uuid is required"):
        require_interaction(object(), "")


def test_require_interaction_raises_not_found():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(NotFound, match="chat interaction not found"):
        require_interaction(db, INTERACTION)


def test_require_interaction_returns_match():
    db = MagicMock()
    interaction = ChatInteraction(
        chat_interaction_uuid=uuid.UUID(INTERACTION),
        patient_uuid=uuid.UUID(PATIENT),
        care_episode_uuid=uuid.UUID(EPISODE),
        changed_by_uuid=uuid.UUID("00000000-0000-7000-8000-000000000000"),
        changed_by_type=2,
    )
    db.query.return_value.filter.return_value.first.return_value = interaction
    assert require_interaction(db, INTERACTION) is interaction
