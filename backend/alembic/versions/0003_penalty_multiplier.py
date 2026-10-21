"""penalty multiplier instead of tier penalty

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-21 16:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("penalty_multiplier", sa.Numeric(4, 2), server_default="1", nullable=False),
    )
    op.create_check_constraint(
        op.f("ck_users_penalty_multiplier_range"), "users", "penalty_multiplier BETWEEN 0 AND 10"
    )
    op.drop_column("tiers", "default_penalty")


def downgrade() -> None:
    # Штраф тира восстанавливаем как награда × множитель владельца.
    op.add_column("tiers", sa.Column("default_penalty", sa.Integer(), nullable=True))
    op.execute(
        "UPDATE tiers SET default_penalty = ROUND(tiers.default_reward * users.penalty_multiplier)"
        " FROM users WHERE users.id = tiers.user_id"
    )
    op.alter_column("tiers", "default_penalty", nullable=False)
    op.drop_constraint(op.f("ck_users_penalty_multiplier_range"), "users", type_="check")
    op.drop_column("users", "penalty_multiplier")
