from __future__ import annotations

import uuid
from datetime import timezone

from sqlalchemy import func

from werkzeug.exceptions import BadRequest, NotFound

from src.models.chat_interaction import ChatInteraction
from src.models.message import Message
from src.services.context_service import normalize_interaction_context

SYSTEM_ACTOR_UUID = uuid.UUID("00000000-0000-7000-8000-000000000000")
SERVICE_ACTOR_TYPE = 2

PREVIEW_MAX_LEN = 80


def _preview_text(content: str) -> str:
    trimmed = content.strip()
    if len(trimmed) <= PREVIEW_MAX_LEN:
        return trimmed
    return f"{trimmed[:PREVIEW_MAX_LEN].rstrip()}…"


def _interaction_preview(db, interaction_uuid: uuid.UUID) -> str | None:
    patient_message = (
        db.query(Message.content)
        .filter(Message.chat_interaction_uuid == interaction_uuid)
        .filter(Message.sender_type == "patient")
        .order_by(Message.changed_at.asc(), Message.message_uuid.asc())
        .first()
    )
    if patient_message:
        return _preview_text(patient_message[0])

    any_message = (
        db.query(Message.content)
        .filter(Message.chat_interaction_uuid == interaction_uuid)
        .order_by(Message.changed_at.desc(), Message.message_uuid.desc())
        .first()
    )
    if any_message:
        return _preview_text(any_message[0])
    return None


def _to_dict(
    interaction: ChatInteraction,
    *,
    message_count: int = 0,
    last_message_at,
    preview: str | None,
) -> dict:
    started_at = interaction.changed_at.astimezone(timezone.utc).isoformat()
    return {
        "chat_interaction_uuid": str(interaction.chat_interaction_uuid),
        "patient_uuid": str(interaction.patient_uuid),
        "care_episode_uuid": str(interaction.care_episode_uuid),
        "started_at": started_at,
        "last_message_at": last_message_at.astimezone(timezone.utc).isoformat() if last_message_at else None,
        "message_count": message_count,
        "preview": preview,
    }


def create_interaction(
    db,
    patient_uuid: str,
    care_episode_uuid: str,
    *,
    context=None,
) -> dict:
    if not patient_uuid or not care_episode_uuid:
        raise BadRequest("patient_uuid and care_episode_uuid are required")

    interaction = ChatInteraction(
        patient_uuid=uuid.UUID(str(patient_uuid)),
        care_episode_uuid=uuid.UUID(str(care_episode_uuid)),
        context=normalize_interaction_context(context),
        changed_by_uuid=SYSTEM_ACTOR_UUID,
        changed_by_type=SERVICE_ACTOR_TYPE,
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    return _to_dict(interaction, message_count=0, last_message_at=None, preview=None)


def list_interactions(db, patient_uuid: str, care_episode_uuid: str) -> list[dict]:
    if not patient_uuid or not care_episode_uuid:
        raise BadRequest("patient_uuid and care_episode_uuid are required")

    patient_id = uuid.UUID(str(patient_uuid))
    episode_id = uuid.UUID(str(care_episode_uuid))

    rows = (
        db.query(
            ChatInteraction,
            func.count(Message.message_uuid),
            func.max(Message.changed_at),
        )
        .outerjoin(Message, Message.chat_interaction_uuid == ChatInteraction.chat_interaction_uuid)
        .filter(ChatInteraction.patient_uuid == patient_id)
        .filter(ChatInteraction.care_episode_uuid == episode_id)
        .group_by(ChatInteraction.chat_interaction_uuid)
        .order_by(func.coalesce(func.max(Message.changed_at), ChatInteraction.changed_at).desc())
        .all()
    )

    items: list[dict] = []
    for interaction, message_count, last_message_at in rows:
        preview = _interaction_preview(db, interaction.chat_interaction_uuid) if message_count else None
        items.append(
            _to_dict(
                interaction,
                message_count=int(message_count or 0),
                last_message_at=last_message_at,
                preview=preview,
            )
        )
    return items


def get_latest_interaction_uuid(db, patient_uuid: str, care_episode_uuid: str) -> str | None:
    interactions = list_interactions(db, patient_uuid, care_episode_uuid)
    if not interactions:
        return None
    return interactions[0]["chat_interaction_uuid"]


def require_interaction(db, chat_interaction_uuid: str) -> ChatInteraction:
    if not chat_interaction_uuid:
        raise BadRequest("chat_interaction_uuid is required")

    interaction_id = uuid.UUID(str(chat_interaction_uuid))
    interaction = (
        db.query(ChatInteraction)
        .filter(ChatInteraction.chat_interaction_uuid == interaction_id)
        .first()
    )
    if not interaction:
        raise NotFound("chat interaction not found")
    return interaction
