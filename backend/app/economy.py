"""Операции с монетами.

Правило: каждое изменение баланса — в одной транзакции БД со сменой статуса квеста
и записью в transactions. Строка пользователя блокируется (SELECT … FOR UPDATE) первой,
до остальных строк, — единый порядок блокировок исключает взаимоблокировки.
"""

from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Transaction, User

TransactionType = Literal["quest_reward", "penalty", "purchase", "manual"]


def utcnow() -> datetime:
    return datetime.now(UTC)


def lock_user(db: Session, user_id: int) -> User:
    """Блокирует строку пользователя до конца транзакции и перечитывает баланс.

    populate_existing обязателен: пользователь уже загружен в сессию при авторизации,
    и без него SQLAlchemy вернул бы старый объект с устаревшим балансом.
    """
    return db.execute(
        select(User)
        .where(User.id == user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one()


def record_transaction(
    db: Session,
    locked_user: User,
    amount: int,
    type_: TransactionType,
    *,
    quest_id: int | None = None,
    reward_id: int | None = None,
) -> Transaction:
    """Меняет баланс и пишет транзакцию. Пользователь должен быть заблокирован lock_user."""
    locked_user.balance += amount
    transaction = Transaction(
        user_id=locked_user.id,
        amount=amount,
        type=type_,
        quest_id=quest_id,
        reward_id=reward_id,
        balance_after=locked_user.balance,
    )
    db.add(transaction)
    return transaction
