"""003 drop redundant patient and episode columns from messages

Revision ID: 003
Revises: 002
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_messages_patient_uuid", table_name="messages")
    op.drop_index("ix_messages_care_episode_uuid", table_name="messages")
    op.execute(sa.text("DROP VIEW IF EXISTS messages_history"))
    op.execute(sa.text("ALTER TABLE messages_audit DROP COLUMN IF EXISTS patient_uuid"))
    op.execute(sa.text("ALTER TABLE messages_audit DROP COLUMN IF EXISTS care_episode_uuid"))
    op.drop_column("messages", "patient_uuid")
    op.execute(sa.text("DROP VIEW IF EXISTS messages_history"))
    op.drop_column("messages", "care_episode_uuid")
    op.execute(sa.text("SELECT audit.setup_views('public', 'messages')"))


def downgrade() -> None:
    raise NotImplementedError("messages episode column drop is irreversible")
