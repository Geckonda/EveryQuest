from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.transactions import transaction_out
from app.crud import apply_changes, get_owned
from app.db import DbSession
from app.deps import CurrentUser
from app.economy import InsufficientFunds, purchase
from app.limits import ensure_reward_room
from app.models import Reward
from app.schemas import PurchaseOut, RewardCreate, RewardOut, RewardSessionOut, RewardUpdate

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
    ensure_reward_room(db, user.id)
    reward = Reward(user_id=user.id, **data.model_dump())
    db.add(reward)
    db.commit()
    return RewardOut.model_validate(reward)


@router.patch("/{reward_id}")
def update_reward(
    reward_id: int, data: RewardUpdate, user: CurrentUser, db: DbSession
) -> RewardOut:
    # Архивация трат ничем не ограничена: покупки ссылаются на трату, но остаются в журнале.
    reward = get_owned(db, Reward, reward_id, user)
    changes = data.changes()
    if changes.get("is_archived") is False and reward.is_archived:
        ensure_reward_room(db, user.id)
    apply_changes(reward, changes)
    db.commit()
    return RewardOut.model_validate(reward)


@router.post("/{reward_id}/purchase", responses={400: {"description": "Не хватает монет"}})
def purchase_reward(
    reward_id: int, user: CurrentUser, db: DbSession, queue: bool = True
) -> PurchaseOut:
    """queue=false — трата со временем стартует сразу, параллельно с уже идущими."""
    reward = get_owned(db, Reward, reward_id, user)
    if reward.is_archived:
        raise HTTPException(status.HTTP_409_CONFLICT, "Трата в архиве")
    try:
        transaction, locked_user, session = purchase(db, user.id, reward, queue=queue)
    except InsufficientFunds as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from None
    db.commit()
    return PurchaseOut(
        transaction=transaction_out(db, transaction),
        balance=locked_user.balance,
        session=session and RewardSessionOut.model_validate(session),
    )
