from __future__ import annotations

import uuid

from sqlalchemy import String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.models.audit_mixin import AuditColumnsMixin


class Message(Base, AuditColumnsMixin):
    __tablename__ = "messages"

    message_uuid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuidv7()"),
    )
    patient_uuid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    care_episode_uuid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    sender_type: Mapped[str] = mapped_column(String(32))
    sender_uuid: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    content: Mapped[str] = mapped_column(Text)
