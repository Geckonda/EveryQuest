from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.crud import get_owned
from app.db import DbSession
from app.deps import CurrentUser
from app.economy import lock_user, utcnow
from app.models import RewardSession
from app.schemas import RewardSessionOut
from app.sessions import repack

router = APIRouter(prefix="/reward-sessions", tags=["reward-sessions"])


@router.get("/active")
def list_active_sessions(user: CurrentUser, db: DbSession) -> list[RewardSessionOut]:
    """Идущие и ожидающие в очереди траты (started_at в будущем) — по времени начала."""
    sessions = db.scalars(
        select(RewardSession)
        .where(
            RewardSession.user_id == user.id,
            RewardSession.finished_at.is_(None),
            RewardSession.ends_at > utcnow(),
        )
        .order_by(RewardSession.started_at, RewardSession.ends_at, RewardSession.id)
    )
    return [RewardSessionOut.model_validate(session) for session in sessions]


@router.post("/{session_id}/finish")
def finish_session(session_id: int, user: CurrentUser, db: DbSession) -> RewardSessionOut:
    """Закончить раньше срока (или отменить ожидающую). Монеты не возвращаются.

    Очередь за ней сдвигается вперёд — следующая трата начинается сразу.
    """
    # Блокировка пользователя сериализует пересборку очереди с покупками.
    lock_user(db, user.id)
    session = get_owned(db, RewardSession, session_id, user)
    now = utcnow()
    if session.finished_at is not None or session.ends_at <= now:
        raise HTTPException(status.HTTP_409_CONFLICT, "Время уже вышло")
    session.finished_at = now
    db.flush()
    repack(db, user.id, now)
    db.commit()
    return RewardSessionOut.model_validate(session)
