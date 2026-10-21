from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud import apply_changes, check_quest_refs, get_owned
from app.db import DbSession
from app.deps import CurrentUser
from app.economy import default_penalty, lock_quest, lock_user, record_transaction, utcnow
from app.models import Quest, User
from app.schemas import QuestClosed, QuestCreate, QuestOut, QuestStatus, QuestUpdate

router = APIRouter(prefix="/quests", tags=["quests"])


def _check_due_at(due_at: datetime | None) -> None:
    if due_at is not None and due_at <= utcnow():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Срок уже прошёл")


def _ensure_active(quest: Quest) -> None:
    """Менять и выполнять можно только активный квест, срок которого не истёк.

    Просроченный, но ещё не обработанный планировщиком квест уже считается проваленным.
    """
    if quest.status != "active":
        raise HTTPException(status.HTTP_409_CONFLICT, "Квест уже не активен")
    if quest.due_at is not None and quest.due_at <= utcnow():
        raise HTTPException(status.HTTP_409_CONFLICT, "Срок квеста истёк")


@router.get("")
def list_quests(
    user: CurrentUser,
    db: DbSession,
    status_: Annotated[QuestStatus | None, Query(alias="status")] = None,
    category_id: int | None = None,
    tier_id: int | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[QuestOut]:
    query = select(Quest).where(Quest.user_id == user.id)
    if status_ is not None:
        query = query.where(Quest.status == status_)
    if category_id is not None:
        query = query.where(Quest.category_id == category_id)
    if tier_id is not None:
        query = query.where(Quest.tier_id == tier_id)
    if status_ == "active":
        # Сначала горящие; без срока — в конце.
        query = query.order_by(Quest.due_at.asc().nulls_last(), Quest.id)
    else:
        query = query.order_by(Quest.id.desc())
    quests = db.scalars(query.limit(limit).offset(offset))
    return [QuestOut.model_validate(quest) for quest in quests]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_quest(data: QuestCreate, user: CurrentUser, db: DbSession) -> QuestOut:
    tier = check_quest_refs(db, user, data.tier_id, data.category_id)
    _check_due_at(data.due_at)
    reward = tier.default_reward if data.reward is None else data.reward
    quest = Quest(
        user_id=user.id,
        tier_id=tier.id,
        category_id=data.category_id,
        name=data.name,
        description=data.description,
        reward=reward,
        penalty=(
            default_penalty(reward, user.penalty_multiplier)
            if data.penalty is None
            else data.penalty
        ),
        due_at=data.due_at,
        status="active",
    )
    db.add(quest)
    db.commit()
    return QuestOut.model_validate(quest)


@router.patch("/{quest_id}")
def update_quest(quest_id: int, data: QuestUpdate, user: CurrentUser, db: DbSession) -> QuestOut:
    quest = get_owned(db, Quest, quest_id, user)
    _ensure_active(quest)
    changes = data.changes()

    if "tier_id" in changes or "category_id" in changes:
        tier = check_quest_refs(
            db,
            user,
            changes.get("tier_id", quest.tier_id),
            changes.get("category_id", quest.category_id),
        )
        if tier.id != quest.tier_id:
            # Сменили тир и не задали награду явно — берём награду нового тира и штраф от неё.
            changes.setdefault("reward", tier.default_reward)
            changes.setdefault(
                "penalty", default_penalty(changes["reward"], user.penalty_multiplier)
            )
    if "due_at" in changes:
        _check_due_at(changes["due_at"])
    if changes.get("status") == "archived":
        changes |= {"close_reason": "archived", "closed_at": utcnow()}

    apply_changes(quest, changes)
    db.commit()
    return QuestOut.model_validate(quest)


def _lock_active(db: Session, user: User, quest_id: int) -> tuple[User, Quest]:
    """Блокировки в общем порядке (пользователь → квест) и проверка, что квест ещё открыт."""
    locked_user = lock_user(db, user.id)
    quest = lock_quest(db, quest_id, user.id)
    if quest is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Не найдено")
    _ensure_active(quest)
    return locked_user, quest


@router.post("/{quest_id}/complete")
def complete_quest(quest_id: int, user: CurrentUser, db: DbSession) -> QuestClosed:
    locked_user, quest = _lock_active(db, user, quest_id)
    quest.status = quest.close_reason = "completed"
    quest.closed_at = utcnow()
    record_transaction(db, locked_user, quest.reward, "quest_reward", quest_id=quest.id)
    db.commit()
    return QuestClosed(quest=QuestOut.model_validate(quest), balance=locked_user.balance)


@router.post("/{quest_id}/fail")
def fail_quest(quest_id: int, user: CurrentUser, db: DbSession) -> QuestClosed:
    """Признать квест проваленным до срока: штраф списывается полностью, как при просрочке.

    В минус уйти можно — это штраф, а не покупка.
    """
    locked_user, quest = _lock_active(db, user, quest_id)
    quest.status = "failed"
    quest.close_reason = "abandoned"
    quest.closed_at = utcnow()
    quest.penalty_applied = True
    if quest.penalty:
        record_transaction(db, locked_user, -quest.penalty, "penalty", quest_id=quest.id)
    db.commit()
    return QuestClosed(quest=QuestOut.model_validate(quest), balance=locked_user.balance)
