"""quest close reason

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-21 17:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CLOSE_REASON_CHECK = (
    "(status = 'active' AND close_reason IS NULL)"
    " OR (status = 'completed' AND close_reason = 'completed')"
    " OR (status = 'failed' AND close_reason IN ('expired', 'abandoned'))"
    " OR (status = 'archived' AND close_reason = 'archived')"
)


def upgrade() -> None:
    op.alter_column("quests", "completed_at", new_column_name="closed_at")
    op.add_column("quests", sa.Column("close_reason", sa.String(16), nullable=True))
    # До этой миграции провалить квест можно было только просрочкой.
    op.execute(
        "UPDATE quests SET close_reason = CASE status"
        " WHEN 'completed' THEN 'completed'"
        " WHEN 'failed' THEN 'expired'"
        " WHEN 'archived' THEN 'archived' END"
    )
    op.execute("UPDATE quests SET closed_at = due_at WHERE status = 'failed'")
    op.create_check_constraint(op.f("ck_quests_close_reason"), "quests", CLOSE_REASON_CHECK)


def downgrade() -> None:
    op.drop_constraint(op.f("ck_quests_close_reason"), "quests", type_="check")
    op.drop_column("quests", "close_reason")
    # completed_at раньше заполнялся только у выполненных.
    op.execute("UPDATE quests SET closed_at = NULL WHERE status <> 'completed'")
    op.alter_column("quests", "closed_at", new_column_name="completed_at")
