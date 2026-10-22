"""pagination indexes

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-22 18:07:14.174579

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# У закрытого квеста всегда есть момент закрытия — по нему листается архив курсором.
# Автогенерация CHECK не видит — написано вручную (сверку делает tests/test_migrations.py).
CLOSED_AT_CHECK = "(status = 'active') = (closed_at IS NULL)"


def upgrade() -> None:
    # Закрытые до миграции 0004 (снятые с доски) могли остаться без момента закрытия.
    op.execute(
        "UPDATE quests SET closed_at = COALESCE(due_at, created_at)"
        " WHERE status <> 'active' AND closed_at IS NULL"
    )
    op.create_check_constraint(op.f("ck_quests_closed_at"), "quests", CLOSED_AT_CHECK)
    op.create_index(
        "ix_quests_user_id_closed_at_id", "quests", ["user_id", "closed_at", "id"], unique=False
    )
    op.drop_index(op.f("ix_transactions_user_id_created_at"), table_name="transactions")
    op.create_index(
        "ix_transactions_user_id_created_at_id",
        "transactions",
        ["user_id", "created_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_transactions_user_id_created_at_id", table_name="transactions")
    op.create_index(
        op.f("ix_transactions_user_id_created_at"),
        "transactions",
        ["user_id", "created_at"],
        unique=False,
    )
    op.drop_index("ix_quests_user_id_closed_at_id", table_name="quests")
    op.drop_constraint(op.f("ck_quests_closed_at"), "quests", type_="check")
