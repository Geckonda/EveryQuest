"""users.default_due_time

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-24 12:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 23:59 — как было до настройки: срок нового квеста «до конца дня».
    op.add_column(
        "users",
        sa.Column("default_due_time", sa.Time(), server_default=sa.text("'23:59'"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "default_due_time")
