"""001 messages table

Revision ID: 001
Revises: 000
Create Date: 2026-06-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = "000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "messages",
        sa.Column("message_uuid", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False, server_default=sa.text("uuidv7()")),
        sa.Column("patient_uuid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("care_episode_uuid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sender_type", sa.String(length=32), nullable=False),
        sa.Column("sender_uuid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
    )
    op.create_index("ix_messages_patient_uuid", "messages", ["patient_uuid"])
    op.create_index("ix_messages_care_episode_uuid", "messages", ["care_episode_uuid"])
    op.execute(sa.text("SELECT audit.setup_tracking('public', 'messages')"))
    op.create_index("ix_messages_changed_at", "messages", ["changed_at"])


def downgrade() -> None:
    raise NotImplementedError("messages migration is irreversible")
