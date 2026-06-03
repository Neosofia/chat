from __future__ import annotations

import uuid
from datetime import timezone

from sqlalchemy import func

from werkzeug.exceptions import BadRequest

from src.models.message import Message

SYSTEM_ACTOR_UUID = uuid.UUID("00000000-0000-7000-8000-000000000000")
SERVICE_ACTOR_TYPE = 2


def _to_dict(item: Message) -> dict:
    return {
        "message_uuid": str(item.message_uuid),
        "patient_uuid": str(item.patient_uuid),
        "care_episode_uuid": str(item.care_episode_uuid) if item.care_episode_uuid else None,
        "sender_type": item.sender_type,
        "sender_uuid": str(item.sender_uuid) if item.sender_uuid else None,
        "content": item.content,
        "created_at": item.changed_at.astimezone(timezone.utc).isoformat(),
    }


def list_messages(db, patient_uuid: str, care_episode_uuid: str | None = None, limit: int = 200) -> list[dict]:
    patient_id = uuid.UUID(str(patient_uuid))
    if not care_episode_uuid:
        raise BadRequest("care_episode_uuid is required")
    query = db.query(Message).filter(Message.patient_uuid == patient_id)
    query = query.filter(Message.care_episode_uuid == uuid.UUID(str(care_episode_uuid)))
    rows = query.order_by(Message.changed_at.asc(), Message.message_uuid.asc()).limit(limit).all()
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
            .filter(Message.patient_uuid == patient_id)
            .filter(Message.care_episode_uuid == episode_id)
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
    required = ("patient_uuid", "care_episode_uuid", "sender_type", "content")
    missing = [field for field in required if not payload.get(field)]
    if missing:
        raise BadRequest(f"missing required fields: {missing}")
    if payload["sender_type"] not in {"patient", "ai_agent", "clinician"}:
        raise BadRequest("sender_type must be one of patient, ai_agent, clinician")
    if payload.get("created_at"):
        raise BadRequest("created_at cannot be set via the API")

    item = Message(
        patient_uuid=uuid.UUID(str(payload["patient_uuid"])),
        care_episode_uuid=uuid.UUID(str(payload["care_episode_uuid"])),
        sender_type=payload["sender_type"],
        sender_uuid=uuid.UUID(str(payload["sender_uuid"])) if payload.get("sender_uuid") else None,
        content=str(payload["content"]).strip(),
        changed_by_uuid=SYSTEM_ACTOR_UUID,
        changed_by_type=SERVICE_ACTOR_TYPE,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_dict(item)
