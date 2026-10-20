from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta

import pytest

from app.recurrence import Period, due_at_for, local_today, next_due_at, period_for


@dataclass
class S:
    """Расписание для тестов — те же поля, что у RecurringQuest."""

    frequency: str
    interval: int = 1
    days_of_week: list[int] | None = None
    day_of_month: int | None = None
    due_time: time = field(default_factory=lambda: time(23, 59))
    start_date: date = date(2026, 1, 1)
    end_date: date | None = None


def days(start: date, count: int) -> list[date]:
    return [start + timedelta(days=i) for i in range(count)]


def matching(schedule: S, start: date, count: int) -> list[date]:
    """Дни, в которые начинается период."""
    return sorted(
        {p.period_date for d in days(start, count) if (p := period_for(schedule, d)) is not None}
    )


# --- daily ---


def test_daily_every_day() -> None:
    assert period_for(S("daily"), date(2026, 10, 21)) == Period(
        date(2026, 10, 21), date(2026, 10, 21)
    )


def test_daily_every_third_day_from_start() -> None:
    schedule = S("daily", interval=3, start_date=date(2026, 10, 1))
    assert matching(schedule, date(2026, 10, 1), 10) == [
        date(2026, 10, 1),
        date(2026, 10, 4),
        date(2026, 10, 7),
        date(2026, 10, 10),
    ]


def test_daily_respects_start_and_end() -> None:
    schedule = S("daily", start_date=date(2026, 10, 5), end_date=date(2026, 10, 7))
    assert matching(schedule, date(2026, 10, 1), 10) == days(date(2026, 10, 5), 3)


# --- weekly ---


def test_weekly_selected_days() -> None:
    # Пн, ср, пт. 19 октября 2026 — понедельник.
    schedule = S("weekly", days_of_week=[1, 3, 5])
    assert matching(schedule, date(2026, 10, 19), 7) == [
        date(2026, 10, 19),
        date(2026, 10, 21),
        date(2026, 10, 23),
    ]


def test_weekly_every_two_weeks_counts_from_start_week() -> None:
    # Старт в среду 21.10 — неделя старта (с пн 19.10) считается первой.
    schedule = S("weekly", interval=2, days_of_week=[1], start_date=date(2026, 10, 21))
    assert matching(schedule, date(2026, 10, 19), 35) == [
        date(2026, 11, 2),  # пн 19.10 раньше старта, 26.10 — нечётная неделя
        date(2026, 11, 16),
    ]


def test_weekly_without_days_is_whole_week_due_sunday() -> None:
    schedule = S("weekly")
    wednesday = date(2026, 10, 21)
    assert period_for(schedule, wednesday) == Period(date(2026, 10, 19), date(2026, 10, 25))


def test_weekly_without_days_created_midweek_counts_current_week() -> None:
    """Шаблон, созданный в среду, даёт экземпляр за текущую неделю."""
    schedule = S("weekly", start_date=date(2026, 10, 21))
    assert period_for(schedule, date(2026, 10, 21)) == Period(
        date(2026, 10, 19), date(2026, 10, 25)
    )


def test_weekly_without_days_ending_midweek() -> None:
    schedule = S("weekly", start_date=date(2026, 10, 1), end_date=date(2026, 10, 20))
    assert period_for(schedule, date(2026, 10, 22)) is not None  # неделя началась до конца
    assert period_for(schedule, date(2026, 10, 27)) is None


# --- monthly ---


def test_monthly_on_day() -> None:
    schedule = S("monthly", day_of_month=15)
    assert matching(schedule, date(2026, 10, 1), 62) == [date(2026, 10, 15), date(2026, 11, 15)]


@pytest.mark.parametrize(
    ("day_of_month", "month_start", "expected"),
    [
        (31, date(2026, 2, 1), date(2026, 2, 28)),  # февраль обычного года
        (31, date(2028, 2, 1), date(2028, 2, 29)),  # високосный
        (30, date(2026, 2, 1), date(2026, 2, 28)),
        (29, date(2026, 2, 1), date(2026, 2, 28)),
        (29, date(2028, 2, 1), date(2028, 2, 29)),
        (31, date(2026, 4, 1), date(2026, 4, 30)),
        (31, date(2026, 12, 1), date(2026, 12, 31)),
    ],
)
def test_monthly_day_beyond_month_end_is_last_day(
    day_of_month: int, month_start: date, expected: date
) -> None:
    schedule = S("monthly", day_of_month=day_of_month)
    month_days = [d for d in days(month_start, 31) if d.month == month_start.month]
    assert matching(schedule, month_start, len(month_days)) == [expected]


def test_monthly_without_day_is_whole_month() -> None:
    schedule = S("monthly")
    assert period_for(schedule, date(2026, 2, 10)) == Period(date(2026, 2, 1), date(2026, 2, 28))
    assert period_for(schedule, date(2028, 2, 10)) == Period(date(2028, 2, 1), date(2028, 2, 29))


def test_monthly_every_two_months_across_year() -> None:
    schedule = S("monthly", interval=2, day_of_month=1, start_date=date(2026, 11, 1))
    assert matching(schedule, date(2026, 11, 1), 150) == [
        date(2026, 11, 1),
        date(2027, 1, 1),
        date(2027, 3, 1),
    ]


# --- часовые пояса ---


NOW_UTC = datetime(2026, 10, 21, 16, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("timezone", "expected"),
    [
        ("UTC", date(2026, 10, 21)),
        ("Asia/Tokyo", date(2026, 10, 22)),  # UTC+9: уже 01:00 следующего дня
        ("America/Los_Angeles", date(2026, 10, 21)),  # UTC−7: 09:00
        ("Pacific/Kiritimati", date(2026, 10, 22)),  # UTC+14
        ("Pacific/Pago_Pago", date(2026, 10, 21)),  # UTC−11
    ],
)
def test_local_today(timezone: str, expected: date) -> None:
    assert local_today(timezone, NOW_UTC) == expected


def test_due_at_converted_to_utc() -> None:
    schedule = S("daily", due_time=time(23, 59))
    period = Period(date(2026, 10, 21), date(2026, 10, 21))
    assert due_at_for(schedule, period, "Europe/Saratov") == datetime(
        2026, 10, 21, 19, 59, tzinfo=UTC
    )  # Саратов UTC+4
    assert due_at_for(schedule, period, "Asia/Tokyo") == datetime(2026, 10, 21, 14, 59, tzinfo=UTC)


def test_due_at_follows_daylight_saving() -> None:
    """В Берлине зимой UTC+1, летом UTC+2 — 23:59 по местному везде 23:59."""
    schedule = S("daily", due_time=time(23, 59))
    winter = due_at_for(schedule, Period(date(2026, 1, 15), date(2026, 1, 15)), "Europe/Berlin")
    summer = due_at_for(schedule, Period(date(2026, 7, 15), date(2026, 7, 15)), "Europe/Berlin")
    assert winter.hour == 22
    assert summer.hour == 21


def test_due_at_on_missing_dst_hour_does_not_crash() -> None:
    """29.03.2026 в Берлине часов 02:00–03:00 нет; zoneinfo сдвигает время, а не падает."""
    schedule = S("daily", due_time=time(2, 30))
    due = due_at_for(schedule, Period(date(2026, 3, 29), date(2026, 3, 29)), "Europe/Berlin")
    assert due.date() == date(2026, 3, 29)


# --- следующий срок ---


def test_next_due_today_if_not_passed() -> None:
    schedule = S("daily", due_time=time(23, 59))
    now = datetime(2026, 10, 21, 10, 0, tzinfo=UTC)
    assert next_due_at(schedule, "UTC", now) == datetime(2026, 10, 21, 23, 59, tzinfo=UTC)


def test_next_due_tomorrow_if_today_passed() -> None:
    schedule = S("daily", due_time=time(9, 0))
    now = datetime(2026, 10, 21, 10, 0, tzinfo=UTC)
    assert next_due_at(schedule, "UTC", now) == datetime(2026, 10, 22, 9, 0, tzinfo=UTC)


def test_next_due_none_after_end() -> None:
    schedule = S("daily", end_date=date(2026, 10, 20))
    assert next_due_at(schedule, "UTC", datetime(2026, 10, 21, tzinfo=UTC)) is None


def test_next_due_yearly_via_monthly_interval() -> None:
    schedule = S("monthly", interval=12, day_of_month=1, start_date=date(2026, 1, 1))
    due = next_due_at(schedule, "UTC", datetime(2026, 10, 21, tzinfo=UTC))
    assert due is not None
    assert due.date() == date(2027, 1, 1)
