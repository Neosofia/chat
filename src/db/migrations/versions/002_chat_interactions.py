"""002 chat interactions

Revision ID: 002
Revises: 001
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None

SYSTEM_ACTOR_UUID = "00000000-0000-7000-8000-000000000000"


def upgrade() -> None:
    op.create_table(
        "chat_interactions",
        sa.Column(
            "chat_interaction_uuid",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("uuidv7()"),
        ),
        sa.Column("patient_uuid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("care_episode_uuid", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_index("ix_chat_interactions_patient_uuid", "chat_interactions", ["patient_uuid"])
    op.create_index("ix_chat_interactions_care_episode_uuid", "chat_interactions", ["care_episode_uuid"])
    op.execute(sa.text("SELECT audit.setup_tracking('public', 'chat_interactions')"))
    op.create_index("ix_chat_interactions_changed_at", "chat_interactions", ["changed_at"])

    op.add_column(
        "messages",
        sa.Column("chat_interaction_uuid", postgresql.UUID(as_uuid=True), nullable=True),
    )

    op.execute(
        sa.text(
            f"""
            INSERT INTO chat_interactions (
                chat_interaction_uuid,
                patient_uuid,
                care_episode_uuid,
                changed_by_uuid,
                changed_by_type
            )
            SELECT
                uuidv7(),
                distinct_pairs.patient_uuid,
                distinct_pairs.care_episode_uuid,
                '{SYSTEM_ACTOR_UUID}'::uuid,
                2
            FROM (
                SELECT DISTINCT patient_uuid, care_episode_uuid
                FROM messages
            ) AS distinct_pairs
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE messages AS message_row
            SET chat_interaction_uuid = interaction_row.chat_interaction_uuid
            FROM chat_interactions AS interaction_row
            WHERE message_row.patient_uuid = interaction_row.patient_uuid
              AND message_row.care_episode_uuid = interaction_row.care_episode_uuid
            """
        )
    )

    op.alter_column("messages", "chat_interaction_uuid", nullable=False)
    op.create_index("ix_messages_chat_interaction_uuid", "messages", ["chat_interaction_uuid"])
    op.create_foreign_key(
        "fk_messages_chat_interaction_uuid",
        "messages",
        "chat_interactions",
        ["chat_interaction_uuid"],
        ["chat_interaction_uuid"],
    )


def downgrade() -> None:
    raise NotImplementedError("chat interactions migration is irreversible")
