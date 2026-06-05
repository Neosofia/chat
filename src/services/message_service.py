from __future__ import annotations

import uuid
from datetime import timezone

from sqlalchemy import func

from werkzeug.exceptions import BadRequest

from src.models.chat_interaction import ChatInteraction
from src.models.message import Message
from src.services.interaction_service import require_interaction

SYSTEM_ACTOR_UUID = uuid.UUID("00000000-0000-7000-8000-000000000000")
SERVICE_ACTOR_TYPE = 2


def _to_dict(item: Message) -> dict:
    return {
        "message_uuid": str(item.message_uuid),
        "chat_interaction_uuid": str(item.chat_interaction_uuid),
        "sender_type": item.sender_type,
        "sender_uuid": str(item.sender_uuid) if item.sender_uuid else None,
        "content": item.content,
        "created_at": item.changed_at.astimezone(timezone.utc).isoformat(),
    }


def list_messages(db, chat_interaction_uuid: str | None = None, limit: int = 200) -> list[dict]:
    if not chat_interaction_uuid:
        raise BadRequest("chat_interaction_uuid is required")
    require_interaction(db, chat_interaction_uuid)
    rows = (
        db.query(Message)
        .filter(Message.chat_interaction_uuid == uuid.UUID(str(chat_interaction_uuid)))
        .order_by(Message.changed_at.desc(), Message.message_uuid.desc())
        .limit(limit)
        .all()
    )
    rows.reverse()
    return [_to_dict(row) for row in rows]


def list_last_message_times(db, items: list[dict]) -> list[dict]:
    results: list[dict] = []
    for item in items:
        patient_uuid = str(item.get("patient_uuid", "")).strip()
        care_episode_uuid = str(item.get("care_episode_uuid", "")).strip()
        if not patient_uuid or not care_episode_uuid:
            raise BadRequest("each item requires patient_uuid and care_episode_uuid")
        patient_id = uuid.UUID(patient_uuid)
        episode_id = uuid.UUID(care_episode_uuid)
        last_at = (
            db.query(func.max(Message.changed_at))
            .join(ChatInteraction, Message.chat_interaction_uuid == ChatInteraction.chat_interaction_uuid)
            .filter(ChatInteraction.patient_uuid == patient_id)
            .filter(ChatInteraction.care_episode_uuid == episode_id)
            .scalar()
        )
        results.append(
            {
                "patient_uuid": str(patient_id),
                "care_episode_uuid": str(episode_id),
                "last_message_at": last_at.astimezone(timezone.utc).isoformat() if last_at else None,
            }
        )
    return results


def create_message(db, payload: dict) -> dict:
    required = ("chat_interaction_uuid", "sender_type", "content")
    missing = [field for field in required if not payload.get(field)]
    if missing:
        raise BadRequest(f"missing required fields: {missing}")
    if payload["sender_type"] not in {"patient", "ai_agent", "clinician"}:
        raise BadRequest("sender_type must be one of patient, ai_agent, clinician")
    if payload.get("created_at"):
        raise BadRequest("created_at cannot be set via the API")

    chat_interaction_uuid = str(payload["chat_interaction_uuid"])
    interaction = require_interaction(db, chat_interaction_uuid)

    sender_uuid = payload.get("sender_uuid")
    if payload["sender_type"] == "patient" and not sender_uuid:
        sender_uuid = str(interaction.patient_uuid)

    item = Message(
        chat_interaction_uuid=uuid.UUID(chat_interaction_uuid),
        sender_type=payload["sender_type"],
        sender_uuid=uuid.UUID(str(sender_uuid)) if sender_uuid else None,
        content=str(payload["content"]).strip(),
        changed_by_uuid=SYSTEM_ACTOR_UUID,
        changed_by_type=SERVICE_ACTOR_TYPE,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_dict(item)
