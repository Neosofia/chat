"""005 messages channel

Revision ID: 005
Revises: 004
Create Date: 2026-06-09
"""

from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None

WEB_CHANNEL = 1


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("channel", sa.SmallInteger(), nullable=False, server_default=str(WEB_CHANNEL)),
    )
    op.create_check_constraint(
        "ck_messages_channel",
        "messages",
        "channel IN (1, 2, 3)",
    )
    op.alter_column("messages", "channel", server_default=None)


def downgrade() -> None:
    raise NotImplementedError("messages channel migration is irreversible")
