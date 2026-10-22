from datetime import datetime, time, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select, tuple_
from sqlalchemy.orm import Session

from app.db import DbSession
from app.deps import CurrentUser
from app.economy import InsufficientFunds, manual_adjust, utcnow
from app.models import Quest, Reward, Transaction
from app.pagination import MAX_PAGE_SIZE, PAGE_SIZE, decode_cursor, encode_cursor
from app.recurrence import local_today
from app.schemas import (
    BalanceChange,
    DaySummary,
    ManualTransactionIn,
    TransactionOut,
    TransactionPage,
    TransactionType,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])


def transaction_out(db: Session, transaction: Transaction) -> TransactionOut:
    """Одна транзакция с названием квеста или траты."""
    title = None
    if transaction.quest_id is not None:
        title = db.scalar(select(Quest.name).where(Quest.id == transaction.quest_id))
    elif transaction.reward_id is not None:
        title = db.scalar(select(Reward.name).where(Reward.id == transaction.reward_id))
    return TransactionOut.model_validate(transaction).model_copy(update={"title": title})


@router.get("")
def list_transactions(
    user: CurrentUser,
    db: DbSession,
    type_: Annotated[TransactionType | None, Query(alias="type")] = None,
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = PAGE_SIZE,
) -> TransactionPage:
    """Летопись страницами, новые сверху. cursor — next_cursor прошлой страницы."""
    condition = Transaction.user_id == user.id
    if type_ is not None:
        condition &= Transaction.type == type_

    # Общее число — только для первой страницы: на каждой пересчитывать всё дорого.
    total = None
    if cursor is None:
        total = db.scalar(select(func.count()).select_from(Transaction).where(condition)) or 0
    else:
        created_at, transaction_id = decode_cursor(cursor)
        condition &= tuple_(Transaction.created_at, Transaction.id) < (created_at, transaction_id)

    rows = db.execute(
        select(Transaction, func.coalesce(Quest.name, Reward.name))
        .outerjoin(Quest, Quest.id == Transaction.quest_id)
        .outerjoin(Reward, Reward.id == Transaction.reward_id)
        .where(condition)
        .order_by(Transaction.created_at.desc(), Transaction.id.desc())
        # На одну больше — так видно, есть ли следующая страница.
        .limit(limit + 1)
    ).all()
    page = rows[:limit]
    last = page[-1][0] if len(rows) > limit else None
    items = [
        TransactionOut.model_validate(transaction).model_copy(update={"title": title})
        for transaction, title in page
    ]
    return TransactionPage(
        items=items,
        total=total,
        next_cursor=encode_cursor(last.created_at, last.id) if last else None,
    )


@router.get("/today")
def today_summary(user: CurrentUser, db: DbSession) -> DaySummary:
    """Итог текущего дня по часовому поясу пользователя: сколько заработано и потрачено."""
    day = local_today(user.timezone, utcnow())
    start = datetime.combine(day, time(), tzinfo=ZoneInfo(user.timezone))
    # Следующая полночь — через combine, а не +24 ч: в день перехода на летнее время их 23 или 25.
    end = datetime.combine(day + timedelta(days=1), time(), tzinfo=ZoneInfo(user.timezone))
    sums = dict(
        db.execute(
            select(Transaction.type, func.sum(Transaction.amount))
            .where(
                Transaction.user_id == user.id,
                Transaction.created_at >= start,
                Transaction.created_at < end,
            )
            .group_by(Transaction.type)
        ).all()
    )
    return DaySummary(
        date=day,
        earned=sums.get("quest_reward", 0),
        spent=-sums.get("purchase", 0),
        penalties=-sums.get("penalty", 0),
        manual=sums.get("manual", 0),
    )


@router.post("/manual", status_code=status.HTTP_201_CREATED)
def create_manual_transaction(
    data: ManualTransactionIn, user: CurrentUser, db: DbSession
) -> BalanceChange:
    try:
        transaction, locked_user = manual_adjust(db, user.id, data.amount, data.note)
    except InsufficientFunds as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from None
    db.commit()
    return BalanceChange(transaction=transaction_out(db, transaction), balance=locked_user.balance)
