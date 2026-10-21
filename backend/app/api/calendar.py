from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, tuple_

from app.db import DbSession
from app.deps import CurrentUser
from app.economy import utcnow
from app.models import Quest, RecurringQuest
from app.recurrence import due_at_for, occurrences
from app.schemas import CalendarOut, ForecastQuest, QuestOut

router = APIRouter(prefix="/calendar", tags=["calendar"])

# Месячная сетка — 6 недель; с запасом.
MAX_DAYS = 62


@router.get("")
def calendar(start: date, end: date, user: CurrentUser, db: DbSession) -> CalendarOut:
    """Квесты со сроком в [start, end] (местные даты пользователя) и прогноз повторяющихся."""
    if end < start:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Конец раньше начала")
    if (end - start).days + 1 > MAX_DAYS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"Не больше {MAX_DAYS} дней за раз"
        )

    zone = ZoneInfo(user.timezone)
    since = datetime.combine(start, time(), tzinfo=zone)
    until = datetime.combine(end + timedelta(days=1), time(), tzinfo=zone)
    quests = db.scalars(
        select(Quest)
        .where(Quest.user_id == user.id, Quest.due_at >= since, Quest.due_at < until)
        .order_by(Quest.due_at, Quest.id)
    ).all()

    now = utcnow()
    templates = db.scalars(
        select(RecurringQuest).where(
            RecurringQuest.user_id == user.id,
            RecurringQuest.is_active.is_(True),
            RecurringQuest.is_archived.is_(False),
        )
    ).all()
    candidates = [
        (template, period, due_at)
        for template in templates
        for period in occurrences(template, start, end)
        # Прошедшие периоды задним числом не создаются — в прогноз их не берём.
        if (due_at := due_at_for(template, period, user.timezone)) > now
    ]
    # Экземпляр за период уже создан (на доске или закрыт) — он есть в quests, не дублируем.
    existing = set()
    if candidates:
        existing = set(
            db.execute(
                select(Quest.recurring_quest_id, Quest.period_date).where(
                    tuple_(Quest.recurring_quest_id, Quest.period_date).in_(
                        [(t.id, p.period_date) for t, p, _ in candidates]
                    )
                )
            ).all()
        )
    forecast = [
        ForecastQuest(
            recurring_quest_id=template.id,
            period_date=period.period_date,
            name=template.name,
            tier_id=template.tier_id,
            category_id=template.category_id,
            reward=template.reward,
            penalty=template.penalty,
            due_at=due_at,
        )
        for template, period, due_at in candidates
        if (template.id, period.period_date) not in existing
    ]
    forecast.sort(key=lambda f: (f.due_at, f.recurring_quest_id))

    return CalendarOut(quests=[QuestOut.model_validate(q) for q in quests], forecast=forecast)
