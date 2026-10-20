from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.crud import apply_changes, check_quest_refs, get_owned
from app.db import DbSession
from app.deps import CurrentUser
from app.economy import utcnow
from app.jobs import generate_instance
from app.models import RecurringQuest, User
from app.recurrence import local_today, next_due_at
from app.schemas import (
    RecurringQuestCreate,
    RecurringQuestOut,
    RecurringQuestUpdate,
    check_schedule,
)

router = APIRouter(prefix="/recurring-quests", tags=["recurring-quests"])


def _out(template: RecurringQuest, user: User) -> RecurringQuestOut:
    out = RecurringQuestOut.model_validate(template)
    if template.is_active and not template.is_archived:
        out.next_due_at = next_due_at(template, user.timezone, utcnow())
    return out


@router.get("")
def list_recurring(
    user: CurrentUser, db: DbSession, include_archived: bool = False
) -> list[RecurringQuestOut]:
    query = (
        select(RecurringQuest).where(RecurringQuest.user_id == user.id).order_by(RecurringQuest.id)
    )
    if not include_archived:
        query = query.where(RecurringQuest.is_archived.is_(False))
    return [_out(template, user) for template in db.scalars(query)]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_recurring(
    data: RecurringQuestCreate, user: CurrentUser, db: DbSession
) -> RecurringQuestOut:
    tier = check_quest_refs(db, user, data.tier_id, data.category_id)
    now = utcnow()
    start_date = data.start_date or local_today(user.timezone, now)
    if data.end_date is not None and data.end_date < start_date:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Дата окончания раньше даты начала"
        )

    template = RecurringQuest(
        user_id=user.id,
        **data.model_dump(exclude={"start_date", "reward", "penalty"}),
        start_date=start_date,
        reward=tier.default_reward if data.reward is None else data.reward,
        penalty=tier.default_penalty if data.penalty is None else data.penalty,
        is_active=True,
    )
    db.add(template)
    db.flush()
    # Экземпляр за текущий период — сразу, не дожидаясь планировщика.
    generate_instance(db, template, user.timezone, now)
    db.commit()
    return _out(template, user)


@router.patch("/{template_id}")
def update_recurring(
    template_id: int, data: RecurringQuestUpdate, user: CurrentUser, db: DbSession
) -> RecurringQuestOut:
    """Изменения касаются только будущих экземпляров; уже созданный квест не меняется."""
    template = get_owned(db, RecurringQuest, template_id, user)
    changes = data.changes()

    if "tier_id" in changes or "category_id" in changes:
        tier = check_quest_refs(
            db,
            user,
            changes.get("tier_id", template.tier_id),
            changes.get("category_id", template.category_id),
        )
        if tier.id != template.tier_id:
            changes.setdefault("reward", tier.default_reward)
            changes.setdefault("penalty", tier.default_penalty)

    # Расписание проверяется целиком: например, смена weekly → daily с прежними днями недели.
    merged = {
        field: changes.get(field, getattr(template, field))
        for field in ("frequency", "days_of_week", "day_of_month", "start_date", "end_date")
    }
    try:
        days = check_schedule(**merged)
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from None
    if "days_of_week" in changes:
        changes["days_of_week"] = days

    apply_changes(template, changes)
    db.flush()
    if template.is_active and not template.is_archived:
        # Сняли с паузы или сдвинули расписание на сегодня — экземпляр появится сразу.
        generate_instance(db, template, user.timezone, utcnow())
    db.commit()
    return _out(template, user)
