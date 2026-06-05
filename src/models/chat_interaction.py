from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.models.audit_mixin import AuditColumnsMixin


class ChatInteraction(Base, AuditColumnsMixin):
    __tablename__ = "chat_interactions"

    chat_interaction_uuid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuidv7()"),
    )
    patient_uuid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    care_episode_uuid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
