from fastapi import APIRouter, status
from sqlalchemy import select

from app.crud import apply_changes, get_owned
from app.db import DbSession
from app.deps import CurrentUser
from app.models import Reward
from app.schemas import RewardCreate, RewardOut, RewardUpdate

router = APIRouter(prefix="/rewards", tags=["rewards"])


@router.get("")
def list_rewards(
    user: CurrentUser, db: DbSession, include_archived: bool = False
) -> list[RewardOut]:
    query = select(Reward).where(Reward.user_id == user.id).order_by(Reward.price, Reward.id)
    if not include_archived:
        query = query.where(Reward.is_archived.is_(False))
    return [RewardOut.model_validate(reward) for reward in db.scalars(query)]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_reward(data: RewardCreate, user: CurrentUser, db: DbSession) -> RewardOut:
    reward = Reward(user_id=user.id, **data.model_dump())
    db.add(reward)
    db.commit()
    return RewardOut.model_validate(reward)


@router.patch("/{reward_id}")
def update_reward(
    reward_id: int, data: RewardUpdate, user: CurrentUser, db: DbSession
) -> RewardOut:
    # Покупок ещё нет, поэтому архивация трат ничем не ограничена.
    reward = get_owned(db, Reward, reward_id, user)
    apply_changes(reward, data.changes())
    db.commit()
    return RewardOut.model_validate(reward)
