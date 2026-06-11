"""006 chat interactions user uuid

Revision ID: 006
Revises: 005
Create Date: 2026-06-10
"""

from alembic import op
import sqlalchemy as sa

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("chat_interactions", "patient_uuid", new_column_name="user_uuid")
    op.execute(
        sa.text(
            "ALTER INDEX IF EXISTS ix_chat_interactions_patient_uuid "
            "RENAME TO ix_chat_interactions_user_uuid"
        )
    )
    op.alter_column("chat_interactions_audit", "patient_uuid", new_column_name="user_uuid")


def downgrade() -> None:
    raise NotImplementedError("chat interactions user_uuid migration is irreversible")
