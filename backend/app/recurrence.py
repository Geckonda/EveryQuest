"""Расписание повторяющихся квестов — чистые функции без базы данных.

Все даты здесь — локальные даты пользователя (его часовой пояс), кроме due_at (UTC).

Период — отрезок дней, за который создаётся один экземпляр:
- daily, weekly с днями недели, monthly с числом — один день, срок в тот же день;
- weekly без дней — неделя пн–вс, срок в воскресенье;
- monthly без числа — месяц, срок в последний день.

period_date (ключ уникальности экземпляра) — первый день периода.
«Каждые N» отсчитываются от start_date: дни, недели (с понедельника) или месяцы.
"""

import calendar
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Literal, Protocol
from zoneinfo import ZoneInfo

Frequency = Literal["daily", "weekly", "monthly"]

# Сколько дней вперёд искать следующий период (с запасом на «раз в 12 месяцев»).
_LOOKAHEAD_DAYS = 800


class Schedule(Protocol):
    frequency: str
    interval: int
    days_of_week: list[int] | None
    day_of_month: int | None
    due_time: time
    start_date: date
    end_date: date | None


@dataclass(frozen=True)
class Period:
    period_date: date
    due_date: date


def _monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


def _last_day(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def _months_between(start: date, day: date) -> int:
    return (day.year - start.year) * 12 + day.month - start.month


def _in_range(schedule: Schedule, first: date, last: date) -> bool:
    """Период [first, last] пересекается с [start_date, end_date]."""
    if last < schedule.start_date:
        return False
    return schedule.end_date is None or first <= schedule.end_date


def period_for(schedule: Schedule, today: date) -> Period | None:
    """Период, который идёт сегодня (по местной дате), или None, если сегодня не по расписанию."""
    interval = max(schedule.interval, 1)

    if schedule.frequency == "daily":
        if (today - schedule.start_date).days % interval != 0:
            return None
        period = Period(today, today)

    elif schedule.frequency == "weekly":
        monday = _monday(today)
        weeks = (monday - _monday(schedule.start_date)).days // 7
        if weeks % interval != 0:
            return None
        if schedule.days_of_week:
            if today.isoweekday() not in schedule.days_of_week:
                return None
            period = Period(today, today)
        else:
            period = Period(monday, monday + timedelta(days=6))

    elif schedule.frequency == "monthly":
        if _months_between(schedule.start_date, today) % interval != 0:
            return None
        last = _last_day(today.year, today.month)
        if schedule.day_of_month:
            # 31 в 30-дневном месяце (и 29–31 в феврале) — последний день месяца.
            if today.day != min(schedule.day_of_month, last):
                return None
            period = Period(today, today)
        else:
            period = Period(today.replace(day=1), today.replace(day=last))

    else:
        raise ValueError(f"Неизвестная частота: {schedule.frequency}")

    return period if _in_range(schedule, period.period_date, period.due_date) else None


def due_at_for(schedule: Schedule, period: Period, timezone: str) -> datetime:
    """Срок экземпляра в UTC: due_time в последний день периода по времени пользователя."""
    local = datetime.combine(period.due_date, schedule.due_time, tzinfo=ZoneInfo(timezone))
    return local.astimezone(UTC)


def local_today(timezone: str, now: datetime) -> date:
    return now.astimezone(ZoneInfo(timezone)).date()


def next_due_at(schedule: Schedule, timezone: str, now: datetime) -> datetime | None:
    """Ближайший срок экземпляра, который ещё не прошёл (для подсказки в интерфейсе)."""
    today = local_today(timezone, now)
    for offset in range(_LOOKAHEAD_DAYS):
        day = today + timedelta(days=offset)
        if schedule.end_date is not None and day > schedule.end_date:
            return None
        period = period_for(schedule, day)
        # Многодневный период находится и с середины — берём его, если срок ещё впереди.
        if period is not None:
            due = due_at_for(schedule, period, timezone)
            if due > now:
                return due
    return None
