"""Операции с монетами.

Правило: каждое изменение баланса — в одной транзакции БД со сменой статуса квеста
и записью в transactions. Строка пользователя блокируется (SELECT … FOR UPDATE) первой,
до остальных строк, — единый порядок блокировок исключает взаимоблокировки.

Функции не делают commit — это решает вызывающий код.
"""

from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Reward, Transaction, User
from app.schemas import TransactionType


class InsufficientFunds(Exception):  # noqa: N818 — доменная ошибка, не «Error»
    def __init__(self, needed: int, balance: int) -> None:
        super().__init__(f"Не хватает монет: нужно {needed}, на счету {balance}")
        self.needed = needed
        self.balance = balance


MAX_COINS = 1_000_000


def utcnow() -> datetime:
    return datetime.now(UTC)


def default_penalty(reward: int, multiplier: Decimal) -> int:
    """Штраф по умолчанию: награда × множитель, половина округляется вверх.

    Ограничен сверху, как и любая сумма в API: иначе квест нельзя было бы потом сохранить.
    """
    penalty = (reward * multiplier).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    return min(int(penalty), MAX_COINS)


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
    note: str | None = None,
) -> Transaction:
    """Меняет баланс и пишет транзакцию. Пользователь должен быть заблокирован lock_user."""
    locked_user.balance += amount
    transaction = Transaction(
        user_id=locked_user.id,
        amount=amount,
        type=type_,
        quest_id=quest_id,
        reward_id=reward_id,
        note=note,
        balance_after=locked_user.balance,
    )
    db.add(transaction)
    db.flush()
    return transaction


def purchase(db: Session, user_id: int, reward: Reward) -> tuple[Transaction, User]:
    """Покупка разрешена, только если хватает монет; в минусе купить ничего нельзя."""
    user = lock_user(db, user_id)
    if user.balance < reward.price:
        raise InsufficientFunds(reward.price, user.balance)
    transaction = record_transaction(db, user, -reward.price, "purchase", reward_id=reward.id)
    return transaction, user


def manual_adjust(
    db: Session, user_id: int, amount: int, note: str | None
) -> tuple[Transaction, User]:
    """Ручная корректировка. Уйти в минус можно только от штрафов — не от списания вручную."""
    user = lock_user(db, user_id)
    if amount < 0 and user.balance + amount < 0:
        raise InsufficientFunds(-amount, user.balance)
    transaction = record_transaction(db, user, amount, "manual", note=note)
    return transaction, user
