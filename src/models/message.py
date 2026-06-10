from __future__ import annotations

import uuid

from sqlalchemy import SmallInteger, String, Text, text
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
    chat_interaction_uuid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    channel: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    sender_type: Mapped[str] = mapped_column(String(32))
    sender_uuid: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    content: Mapped[str] = mapped_column(Text)
