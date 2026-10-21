from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import quests as quests_api
from app.api import recurring as recurring_api
from app.defaults import DEFAULT_TIERS
from app.jobs import apply_penalties, generate_recurring
from app.models import Quest, User
from tests.conftest import auth_headers, register

API = "/api/v1"
# Среда, 21 октября 2026, полдень по UTC.
NOW = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)


@pytest.fixture
def now(monkeypatch: pytest.MonkeyPatch) -> datetime:
    """Замораживает «сейчас» для API; задачи получают его аргументом."""
    monkeypatch.setattr(recurring_api, "utcnow", lambda: NOW)
    monkeypatch.setattr(quests_api, "utcnow", lambda: NOW)
    return NOW


@pytest.fixture
def headers(client: TestClient, now: datetime) -> dict[str, str]:
    return auth_headers(register(client))


@pytest.fixture
def tier_id(client: TestClient, headers: dict[str, str]) -> int:
    return client.get(f"{API}/tiers", headers=headers).json()[0]["id"]


def create(client: TestClient, headers: dict[str, str], tier_id: int, **body) -> dict:
    response = client.post(
        f"{API}/recurring-quests",
        headers=headers,
        json={"name": "Зарядка", "tier_id": tier_id, "frequency": "daily", **body},
    )
    assert response.status_code == 201, response.text
    return response.json()


def instances(db: Session, template_id: int) -> list[Quest]:
    return list(
        db.scalars(
            select(Quest).where(Quest.recurring_quest_id == template_id).order_by(Quest.period_date)
        )
    )


# --- создание ---


def test_penalty_from_multiplier(
    client: TestClient, db: Session, headers: dict[str, str], tier_id: int
) -> None:
    client.patch(f"{API}/me", headers=headers, json={"penalty_multiplier": 0.5})
    template = create(client, headers, tier_id, reward=15)

    assert template["penalty"] == 8  # 7.5 — половина вверх
    [quest] = instances(db, template["id"])
    assert quest.penalty == 8


def test_daily_creates_instance_for_today(
    client: TestClient, db: Session, headers: dict[str, str], tier_id: int
) -> None:
    template = create(client, headers, tier_id)

    assert template["start_date"] == "2026-10-21"
    assert template["due_time"] == "23:59:00"
    assert (template["reward"], template["penalty"]) == (DEFAULT_TIERS[0][2],) * 2
    assert template["next_due_at"] == "2026-10-21T23:59:00Z"

    [quest] = instances(db, template["id"])
    assert quest.period_date == date(2026, 10, 21)
    assert quest.due_at == datetime(2026, 10, 21, 23, 59, tzinfo=UTC)
    assert quest.status == "active"
    assert quest.name == "Зарядка"

    active = client.get(f"{API}/quests?status=active", headers=headers).json()
    assert [q["recurring_quest_id"] for q in active] == [template["id"]]


def test_no_instance_when_todays_due_time_passed(
    client: TestClient, db: Session, headers: dict[str, str], tier_id: int
) -> None:
    """Создан в 12:00 с due_time 09:00 — сегодняшний экземпляр сразу провалился бы."""
    template = create(client, headers, tier_id, due_time="09:00")
    assert instances(db, template["id"]) == []
    assert template["next_due_at"] == "2026-10-22T09:00:00Z"


def test_instance_in_user_timezone(client: TestClient, db: Session, now: datetime) -> None:
    """В Токио (UTC+9) в 12:00 UTC уже 21:00 — экземпляр за 21-е, срок 23:59 по Токио."""
    headers = auth_headers(register(client, timezone="Asia/Tokyo"))
    tier_id = client.get(f"{API}/tiers", headers=headers).json()[0]["id"]

    template = create(client, headers, tier_id)

    [quest] = instances(db, template["id"])
    assert quest.period_date == date(2026, 10, 21)
    assert quest.due_at == datetime(2026, 10, 21, 14, 59, tzinfo=UTC)


def test_weekly_without_days_due_sunday(
    client: TestClient, db: Session, headers: dict[str, str], tier_id: int
) -> None:
    template = create(client, headers, tier_id, frequency="weekly")
    [quest] = instances(db, template["id"])
    assert quest.period_date == date(2026, 10, 19)  # понедельник
    assert quest.due_at == datetime(2026, 10, 25, 23, 59, tzinfo=UTC)  # воскресенье


def test_weekly_on_other_day_waits(
    client: TestClient, db: Session, headers: dict[str, str], tier_id: int
) -> None:
    template = create(client, headers, tier_id, frequency="weekly", days_of_week=[5, 1, 1])
    assert template["days_of_week"] == [1, 5]
    assert instances(db, template["id"]) == []
    assert template["next_due_at"] == "2026-10-23T23:59:00Z"  # пятница


def test_monthly_without_day_due_end_of_month(
    client: TestClient, db: Session, headers: dict[str, str], tier_id: int
) -> None:
    template = create(client, headers, tier_id, frequency="monthly")
    [quest] = instances(db, template["id"])
    assert quest.period_date == date(2026, 10, 1)
    assert quest.due_at == datetime(2026, 10, 31, 23, 59, tzinfo=UTC)


def test_future_start_date(
    client: TestClient, db: Session, headers: dict[str, str], tier_id: int
) -> None:
    template = create(client, headers, tier_id, start_date="2026-11-01")
    assert instances(db, template["id"]) == []
    assert template["next_due_at"] == "2026-11-01T23:59:00Z"


@pytest.mark.parametrize(
    "body",
    [
        {"frequency": "daily", "days_of_week": [1]},
        {"frequency": "weekly", "day_of_month": 5},
        {"frequency": "monthly", "days_of_week": [1]},
        {"frequency": "weekly", "days_of_week": [8]},
        {"frequency": "monthly", "day_of_month": 32},
        {"frequency": "yearly"},
        {"interval": 0},
        {"start_date": "2026-11-10", "end_date": "2026-11-01"},
        {"end_date": "2026-10-01"},  # раньше start_date по умолчанию (сегодня)
        {"due_time": "25:00"},
    ],
)
def test_create_validation(
    client: TestClient, headers: dict[str, str], tier_id: int, body: dict
) -> None:
    payload = {"name": "Q", "tier_id": tier_id, "frequency": "daily", **body}
    response = client.post(f"{API}/recurring-quests", headers=headers, json=payload)
    assert response.status_code == 422, body


def test_foreign_refs_and_objects(
    client: TestClient, headers: dict[str, str], tier_id: int
) -> None:
    template = create(client, headers, tier_id)
    stranger = auth_headers(register(client, email="stranger@example.com"))

    foreign_tier = client.post(
        f"{API}/recurring-quests",
        headers=stranger,
        json={"name": "Q", "tier_id": tier_id, "frequency": "daily"},
    )
    assert foreign_tier.status_code == 422
    patch = client.patch(
        f"{API}/recurring-quests/{template['id']}", headers=stranger, json={"name": "Моё"}
    )
    assert patch.status_code == 404
    assert client.get(f"{API}/recurring-quests", headers=stranger).json() == []


# --- изменение ---


def test_edit_affects_only_future_instances(
    client: TestClient, db: Session, headers: dict[str, str], tier_id: int
) -> None:
    template = create(client, headers, tier_id)
    client.patch(
        f"{API}/recurring-quests/{template['id']}",
        headers=headers,
        json={"name": "Зарядка 2.0", "reward": 99},
    )

    generate_recurring(db, NOW + timedelta(days=1))

    today, tomorrow = instances(db, template["id"])
    assert (today.name, today.reward) == ("Зарядка", DEFAULT_TIERS[0][2])
    assert (tomorrow.name, tomorrow.reward) == ("Зарядка 2.0", 99)


def test_patch_schedule_consistency(
    client: TestClient, headers: dict[str, str], tier_id: int
) -> None:
    template = create(client, headers, tier_id, frequency="weekly", days_of_week=[1])
    url = f"{API}/recurring-quests/{template['id']}"

    broken = client.patch(url, headers=headers, json={"frequency": "daily"})
    assert broken.status_code == 422

    fixed = client.patch(url, headers=headers, json={"frequency": "daily", "days_of_week": None})
    assert fixed.status_code == 200
    assert fixed.json()["days_of_week"] is None


def test_change_tier_takes_its_reward(
    client: TestClient, headers: dict[str, str], tier_id: int
) -> None:
    template = create(client, headers, tier_id)
    tiers = client.get(f"{API}/tiers", headers=headers).json()
    response = client.patch(
        f"{API}/recurring-quests/{template['id']}",
        headers=headers,
        json={"tier_id": tiers[3]["id"]},
    )
    assert response.json()["reward"] == DEFAULT_TIERS[3][2]


def test_pause_and_resume(
    client: TestClient,
    db: Session,
    headers: dict[str, str],
    tier_id: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    template = create(client, headers, tier_id)
    url = f"{API}/recurring-quests/{template['id']}"

    paused = client.patch(url, headers=headers, json={"is_active": False})
    assert paused.json()["next_due_at"] is None
    tomorrow = NOW + timedelta(days=1)
    assert generate_recurring(db, tomorrow) == 0
    # Текущий экземпляр при паузе остаётся.
    assert [q.status for q in instances(db, template["id"])] == ["active"]

    # Снятие с паузы сразу создаёт экземпляр за текущий период.
    monkeypatch.setattr(recurring_api, "utcnow", lambda: tomorrow)
    resumed = client.patch(url, headers=headers, json={"is_active": True})
    assert resumed.json()["next_due_at"] == "2026-10-22T23:59:00Z"
    assert [q.period_date for q in instances(db, template["id"])] == [
        date(2026, 10, 21),
        date(2026, 10, 22),
    ]


def test_archive_template_keeps_instance(
    client: TestClient, db: Session, headers: dict[str, str], tier_id: int
) -> None:
    template = create(client, headers, tier_id)
    url = f"{API}/recurring-quests/{template['id']}"

    client.patch(url, headers=headers, json={"is_archived": True})

    assert client.get(f"{API}/recurring-quests", headers=headers).json() == []
    archived = client.get(f"{API}/recurring-quests?include_archived=true", headers=headers).json()
    assert archived[0]["next_due_at"] is None
    assert generate_recurring(db, NOW + timedelta(days=1)) == 0
    assert [q.status for q in instances(db, template["id"])] == ["active"]


# --- планировщик ---


def test_generation_is_idempotent(
    client: TestClient, db: Session, headers: dict[str, str], tier_id: int
) -> None:
    template = create(client, headers, tier_id)
    assert generate_recurring(db, NOW) == 0  # уже создан при создании шаблона
    assert generate_recurring(db, NOW + timedelta(minutes=5)) == 0
    assert len(instances(db, template["id"])) == 1


def test_completed_instance_is_not_recreated(
    client: TestClient, db: Session, headers: dict[str, str], tier_id: int
) -> None:
    template = create(client, headers, tier_id)
    [quest] = instances(db, template["id"])
    assert client.post(f"{API}/quests/{quest.id}/complete", headers=headers).status_code == 200

    assert generate_recurring(db, NOW + timedelta(hours=1)) == 0
    assert len(instances(db, template["id"])) == 1


def test_missed_instance_penalized_and_next_created(
    client: TestClient, db: Session, headers: dict[str, str], tier_id: int
) -> None:
    """Полный цикл суток: вчерашний не выполнен → штраф; сегодняшний создан."""
    template = create(client, headers, tier_id)
    next_morning = datetime(2026, 10, 22, 0, 5, tzinfo=UTC)

    assert apply_penalties(db, next_morning) == 1
    assert generate_recurring(db, next_morning) == 1

    yesterday, today = instances(db, template["id"])
    assert (yesterday.status, yesterday.penalty_applied) == ("failed", True)
    assert (today.status, today.period_date) == ("active", date(2026, 10, 22))
    user_id = client.get(f"{API}/me", headers=headers).json()["id"]
    assert db.get(User, user_id).balance == -DEFAULT_TIERS[0][2]


def test_no_backfill_after_downtime(
    client: TestClient, db: Session, headers: dict[str, str], tier_id: int
) -> None:
    """Сервер лежал трое суток: пропущенные дни не создаются задним числом."""
    template = create(client, headers, tier_id, due_time="09:00", start_date="2026-10-22")
    back_online = datetime(2026, 10, 25, 10, 0, tzinfo=UTC)  # 25-е, после 09:00

    assert generate_recurring(db, back_online) == 0
    assert instances(db, template["id"]) == []

    assert generate_recurring(db, back_online + timedelta(days=1) - timedelta(hours=3)) == 1


def test_monthly_last_day_in_february(
    client: TestClient, db: Session, headers: dict[str, str], tier_id: int
) -> None:
    template = create(client, headers, tier_id, frequency="monthly", day_of_month=31)
    assert [q.period_date for q in instances(db, template["id"])] == []  # 21 октября

    for day in (datetime(2026, 10, 31, 1, tzinfo=UTC), datetime(2027, 2, 28, 1, tzinfo=UTC)):
        assert generate_recurring(db, day) == 1
    assert generate_recurring(db, datetime(2027, 2, 27, 1, tzinfo=UTC)) == 0
    assert [q.period_date for q in instances(db, template["id"])] == [
        date(2026, 10, 31),
        date(2027, 2, 28),
    ]


def test_end_date_stops_generation(
    client: TestClient, db: Session, headers: dict[str, str], tier_id: int
) -> None:
    template = create(client, headers, tier_id, end_date="2026-10-22")
    assert generate_recurring(db, datetime(2026, 10, 22, 1, tzinfo=UTC)) == 1
    assert generate_recurring(db, datetime(2026, 10, 23, 1, tzinfo=UTC)) == 0
    assert len(instances(db, template["id"])) == 2


def test_timezone_change_moves_day_boundary(
    client: TestClient, db: Session, headers: dict[str, str], tier_id: int
) -> None:
    """Пользователь улетел в Токио: новый день для него начинается по токийскому времени."""
    template = create(client, headers, tier_id)
    client.patch(f"{API}/me", headers=headers, json={"timezone": "Asia/Tokyo"})

    # 15:30 UTC 21-го — в Токио уже 00:30 22-го.
    assert generate_recurring(db, datetime(2026, 10, 21, 15, 30, tzinfo=UTC)) == 1
    _, tokyo_day = instances(db, template["id"])
    assert tokyo_day.period_date == date(2026, 10, 22)
    assert tokyo_day.due_at == datetime(2026, 10, 22, 14, 59, tzinfo=UTC)
