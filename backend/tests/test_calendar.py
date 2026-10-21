from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api import calendar as calendar_api
from app.api import quests as quests_api
from app.api import recurring as recurring_api
from app.models import Quest
from tests.conftest import auth_headers, register

API = "/api/v1"
# Среда, 21 октября 2026, полдень по UTC; в Саратове (UTC+4) — 16:00.
NOW = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)


@pytest.fixture
def headers(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    for module in (calendar_api, quests_api, recurring_api):
        monkeypatch.setattr(module, "utcnow", lambda: NOW)
    headers = auth_headers(register(client))
    client.patch(f"{API}/me", headers=headers, json={"timezone": "Europe/Saratov"})
    return headers


@pytest.fixture
def tier_id(client: TestClient, headers: dict[str, str]) -> int:
    return client.get(f"{API}/tiers", headers=headers).json()[0]["id"]


def get_calendar(client: TestClient, headers: dict[str, str], start: str, end: str) -> dict:
    response = client.get(f"{API}/calendar?start={start}&end={end}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_quests_by_local_dates(
    client: TestClient, db: Session, headers: dict[str, str], tier_id: int
) -> None:
    user_id = client.get(f"{API}/me", headers=headers).json()["id"]

    def add(name: str, due: datetime | None, status: str = "active") -> None:
        reason = None if status == "active" else status
        db.add(
            Quest(
                user_id=user_id,
                tier_id=tier_id,
                name=name,
                reward=1,
                penalty=1,
                due_at=due,
                status=status,
                close_reason=reason,
            )
        )

    add("До диапазона", datetime(2026, 10, 24, 19, 59, tzinfo=UTC))  # 23:59 24-го по Саратову
    add("Первый день", datetime(2026, 10, 24, 20, 0, tzinfo=UTC))  # 00:00 25-го
    add("Сдан", datetime(2026, 10, 26, 10, 0, tzinfo=UTC), status="completed")
    add("Последний день", datetime(2026, 10, 27, 19, 59, tzinfo=UTC))  # 23:59 27-го
    add("После", datetime(2026, 10, 27, 20, 0, tzinfo=UTC))  # 00:00 28-го
    add("Без срока", None)
    db.flush()

    body = get_calendar(client, headers, "2026-10-25", "2026-10-27")
    assert [q["name"] for q in body["quests"]] == ["Первый день", "Сдан", "Последний день"]


def test_forecast_skips_created_and_past(
    client: TestClient, headers: dict[str, str], tier_id: int
) -> None:
    # Ежедневно до 09:00: сегодняшний срок (09:00 по Саратову) уже прошёл — экземпляра нет.
    morning = client.post(
        f"{API}/recurring-quests",
        headers=headers,
        json={"name": "Зарядка", "tier_id": tier_id, "frequency": "daily", "due_time": "09:00"},
    ).json()
    # Ежедневно до 23:59: сегодняшний экземпляр создан сразу — в прогноз не попадает.
    evening = client.post(
        f"{API}/recurring-quests",
        headers=headers,
        json={"name": "Чтение", "tier_id": tier_id, "frequency": "daily"},
    ).json()

    body = get_calendar(client, headers, "2026-10-20", "2026-10-23")

    assert [q["name"] for q in body["quests"]] == ["Чтение"]  # сегодняшний экземпляр
    forecast = [(f["name"], f["period_date"], f["due_at"]) for f in body["forecast"]]
    assert forecast == [
        ("Зарядка", "2026-10-22", "2026-10-22T05:00:00Z"),
        ("Чтение", "2026-10-22", "2026-10-22T19:59:00Z"),
        ("Зарядка", "2026-10-23", "2026-10-23T05:00:00Z"),
        ("Чтение", "2026-10-23", "2026-10-23T19:59:00Z"),
    ]
    assert body["forecast"][0]["recurring_quest_id"] == morning["id"]
    assert body["forecast"][1]["recurring_quest_id"] == evening["id"]


def test_forecast_ignores_paused_and_archived(
    client: TestClient, headers: dict[str, str], tier_id: int
) -> None:
    for patch in ({"is_active": False}, {"is_archived": True}):
        template = client.post(
            f"{API}/recurring-quests",
            headers=headers,
            json={"name": "Пауза", "tier_id": tier_id, "frequency": "daily"},
        ).json()
        client.patch(f"{API}/recurring-quests/{template['id']}", headers=headers, json=patch)

    assert get_calendar(client, headers, "2026-10-22", "2026-10-31")["forecast"] == []


@pytest.mark.parametrize(
    ("start", "end"),
    [("2026-10-10", "2026-10-01"), ("2026-10-01", "2026-12-15")],
)
def test_invalid_range(client: TestClient, headers: dict[str, str], start: str, end: str) -> None:
    response = client.get(f"{API}/calendar?start={start}&end={end}", headers=headers)
    assert response.status_code == 422


def test_foreign_quests_hidden(client: TestClient, headers: dict[str, str], tier_id: int) -> None:
    client.post(
        f"{API}/quests",
        headers=headers,
        json={"name": "Мой", "tier_id": tier_id, "due_at": "2026-10-22T10:00:00Z"},
    )
    stranger = auth_headers(register(client, email="stranger@example.com"))
    assert get_calendar(client, stranger, "2026-10-20", "2026-10-25") == {
        "quests": [],
        "forecast": [],
    }
