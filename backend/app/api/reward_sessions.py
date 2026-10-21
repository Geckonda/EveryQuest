from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.crud import get_owned
from app.db import DbSession
from app.deps import CurrentUser
from app.economy import utcnow
from app.models import RewardSession
from app.schemas import RewardSessionOut

router = APIRouter(prefix="/reward-sessions", tags=["reward-sessions"])


@router.get("/active")
def list_active_sessions(user: CurrentUser, db: DbSession) -> list[RewardSessionOut]:
    """Идущие траты: не закончены вручную и время ещё не вышло. Сначала те, что кончатся раньше."""
    sessions = db.scalars(
        select(RewardSession)
        .where(
            RewardSession.user_id == user.id,
            RewardSession.finished_at.is_(None),
            RewardSession.ends_at > utcnow(),
        )
        .order_by(RewardSession.ends_at, RewardSession.id)
    )
    return [RewardSessionOut.model_validate(session) for session in sessions]


@router.post("/{session_id}/finish")
def finish_session(session_id: int, user: CurrentUser, db: DbSession) -> RewardSessionOut:
    """Закончить раньше срока. Монеты не возвращаются — заказ уже оплачен."""
    session = get_owned(db, RewardSession, session_id, user)
    if session.finished_at is not None or session.ends_at <= utcnow():
        raise HTTPException(status.HTTP_409_CONFLICT, "Время уже вышло")
    session.finished_at = utcnow()
    db.commit()
    return RewardSessionOut.model_validate(session)
