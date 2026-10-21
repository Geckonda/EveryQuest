"""reversal transaction type

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-21 19:48:36.279350

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Автогенерация не видит изменение CHECK — миграция написана вручную;
# tests/test_migrations.py сверяет определения CHECK с моделями.
OLD = "type IN ('quest_reward', 'penalty', 'purchase', 'manual')"
NEW = "type IN ('quest_reward', 'penalty', 'purchase', 'manual', 'reversal')"


def upgrade() -> None:
    op.drop_constraint(op.f("ck_transactions_type"), "transactions", type_="check")
    op.create_check_constraint(op.f("ck_transactions_type"), "transactions", NEW)


def downgrade() -> None:
    # Отмены превращаем в поправки казначея — суммы и баланс остаются верными.
    op.execute("UPDATE transactions SET type = 'manual' WHERE type = 'reversal'")
    op.drop_constraint(op.f("ck_transactions_type"), "transactions", type_="check")
    op.create_check_constraint(op.f("ck_transactions_type"), "transactions", OLD)
