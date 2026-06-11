"""007 drop chat interactions care episode uuid

Revision ID: 007
Revises: 006
Create Date: 2026-06-10
"""

from alembic import op
import sqlalchemy as sa

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_chat_interactions_care_episode_uuid", table_name="chat_interactions")
    op.execute(sa.text("DROP VIEW IF EXISTS chat_interactions_history"))
    op.execute(sa.text("ALTER TABLE chat_interactions_audit DROP COLUMN IF EXISTS care_episode_uuid"))
    op.drop_column("chat_interactions", "care_episode_uuid")
    op.execute(sa.text("SELECT audit.setup_views('public', 'chat_interactions')"))


def downgrade() -> None:
    raise NotImplementedError("care episode column drop is irreversible")
