"""deletion

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-22 18:22:52.825400

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Позицию меню можно удалить: сеанс траты хранит своё название, ссылка становится NULL.
    op.alter_column("reward_sessions", "reward_id", existing_type=sa.INTEGER(), nullable=True)
    # Название удалённой позиции меню — в записях летописи.
    op.add_column("transactions", sa.Column("title_snapshot", sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column("transactions", "title_snapshot")
    # Сеансы удалённых позиций меню без ссылки NOT NULL не переживут — убираем их.
    op.execute("DELETE FROM reward_sessions WHERE reward_id IS NULL")
    op.alter_column("reward_sessions", "reward_id", existing_type=sa.INTEGER(), nullable=False)
