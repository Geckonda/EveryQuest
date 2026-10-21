"""Очередь идущих трат.

Трата идёт с started_at до ends_at. Заказ «после текущих» встаёт в очередь: его
started_at — конец последней незаконченной траты, и до этого момента отсчёт не идёт.
Закончили трату раньше — очередь за ней сдвигается вперёд, а не ждёт исходного времени.

Функции не делают commit и не блокируют — вызывающий код уже держит блокировку
пользователя (lock_user), чтобы две операции не пересобирали очередь одновременно.
"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import RewardSession


def _unfinished(user_id: int, now: datetime):
    return (
        RewardSession.user_id == user_id,
        RewardSession.finished_at.is_(None),
        RewardSession.ends_at > now,
    )


def queue_end(db: Session, user_id: int, now: datetime) -> datetime:
    """Когда освободится очередь: конец последней незаконченной траты или сейчас."""
    last = db.scalar(select(func.max(RewardSession.ends_at)).where(*_unfinished(user_id, now)))
    return max(last, now) if last else now


def repack(db: Session, user_id: int, now: datetime) -> None:
    """Подтягивает ожидающие траты вперёд, если перед ними освободилось время.

    Якорь — конец идущих сейчас трат (или сейчас). Ожидающие по порядку встают
    вплотную за якорем; длительность сохраняется, позже исходного никто не сдвигается.
    """
    sessions = db.scalars(
        select(RewardSession)
        .where(*_unfinished(user_id, now))
        .order_by(RewardSession.started_at, RewardSession.id)
    ).all()
    running = [s for s in sessions if s.started_at <= now]
    waiting = [s for s in sessions if s.started_at > now]

    anchor = max((s.ends_at for s in running), default=now)
    for session in waiting:
        if session.started_at > anchor:
            duration = session.ends_at - session.started_at
            session.started_at = anchor
            session.ends_at = anchor + duration
        anchor = max(anchor, session.ends_at)
    db.flush()
