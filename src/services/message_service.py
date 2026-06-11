from __future__ import annotations

import uuid
from datetime import timezone

from sqlalchemy import func

from werkzeug.exceptions import BadRequest, ServiceUnavailable

from src.bootstrap.config import inference_configured, settings
from src.models.chat_channel import CHAT_CHANNEL_LABELS, parse_chat_channel
from src.models.chat_interaction import ChatInteraction
from src.models.message import Message
from src.services.interaction_service import require_interaction

SYSTEM_ACTOR_UUID = uuid.UUID("00000000-0000-7000-8000-000000000000")
SERVICE_ACTOR_TYPE = 2


def has_intervention(rows: list[dict]) -> bool:
    intervention = frozenset(settings.intervention_sender_types)
    return any(str(row.get("sender_type", "")).strip().lower() in intervention for row in rows)


def _to_dict(item: Message) -> dict:
    return {
        "message_uuid": str(item.message_uuid),
        "chat_interaction_uuid": str(item.chat_interaction_uuid),
        "channel": item.channel,
        "channel_label": CHAT_CHANNEL_LABELS[item.channel],
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
        user_uuid = str(item.get("user_uuid", "")).strip()
        if not user_uuid:
            raise BadRequest("each item requires user_uuid")
        user_id = uuid.UUID(user_uuid)
        last_at = (
            db.query(func.max(Message.changed_at))
            .join(ChatInteraction, Message.chat_interaction_uuid == ChatInteraction.chat_interaction_uuid)
            .filter(ChatInteraction.user_uuid == user_id)
            .scalar()
        )
        results.append(
            {
                "user_uuid": str(user_id),
                "last_message_at": last_at.astimezone(timezone.utc).isoformat() if last_at else None,
            }
        )
    return results


def create_message(db, payload: dict) -> dict:
    required = ("chat_interaction_uuid", "sender_type", "content")
    missing = [field for field in required if not payload.get(field)]
    if missing:
        raise BadRequest(f"missing required fields: {missing}")

    if payload.get("created_at"):
        raise BadRequest("created_at cannot be set via the API")

    chat_interaction_uuid = str(payload["chat_interaction_uuid"])
    sender_type = str(payload["sender_type"]).strip().lower()
    allowed = frozenset(settings.message_sender_types)
    if sender_type not in allowed:
        raise BadRequest(f"sender_type must be one of {', '.join(sorted(allowed))}")
    if sender_type == settings.completion_user_sender_type:
        thread = list_messages(db, chat_interaction_uuid, limit=200)
        if not has_intervention(thread) and not inference_configured():
            raise ServiceUnavailable("AI assistant is not available")

    interaction = require_interaction(db, chat_interaction_uuid)

    sender_uuid = payload.get("sender_uuid")
    if sender_type == settings.completion_user_sender_type and not sender_uuid:
        sender_uuid = str(interaction.user_uuid)

    channel = parse_chat_channel(payload.get("channel"))

    item = Message(
        chat_interaction_uuid=uuid.UUID(chat_interaction_uuid),
        channel=int(channel),
        sender_type=sender_type,
        sender_uuid=uuid.UUID(str(sender_uuid)) if sender_uuid else None,
        content=str(payload["content"]).strip(),
        changed_by_uuid=SYSTEM_ACTOR_UUID,
        changed_by_type=SERVICE_ACTOR_TYPE,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_dict(item)
