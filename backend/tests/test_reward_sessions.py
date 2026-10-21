from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import economy
from app.api import reward_sessions as sessions_api
from app.models import RewardSession
from tests.conftest import auth_headers, register
from tests.test_economy import create_reward, earn

API = "/api/v1"
T0 = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)


class Clock:
    """Управляемое «сейчас» для покупок и сеансов."""

    def __init__(self) -> None:
        self.now = T0

    def at(self, minutes: float) -> str:
        """Момент T0 + minutes в формате ответа API."""
        return (T0 + timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z")


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    clock = Clock()
    for module in (economy, sessions_api):
        monkeypatch.setattr(module, "utcnow", lambda: clock.now)
    return clock


@pytest.fixture
def headers(client: TestClient, clock: Clock) -> dict[str, str]:
    headers = auth_headers(register(client))
    earn(client, headers, 200)
    return headers


def buy(client: TestClient, headers: dict[str, str], reward_id: int, queue: bool = True) -> dict:
    response = client.post(
        f"{API}/rewards/{reward_id}/purchase?queue={str(queue).lower()}", headers=headers
    )
    assert response.status_code == 200, response.text
    return response.json()


def active(client: TestClient, headers: dict[str, str]) -> list[dict]:
    return client.get(f"{API}/reward-sessions/active", headers=headers).json()


def timeline(client: TestClient, headers: dict[str, str]) -> list[tuple[str, str, str]]:
    return [(s["name"], s["started_at"], s["ends_at"]) for s in active(client, headers)]


def finish(client: TestClient, headers: dict[str, str], session_id: int) -> int:
    return client.post(f"{API}/reward-sessions/{session_id}/finish", headers=headers).status_code


def test_purchase_with_duration_starts_session(
    client: TestClient, headers: dict[str, str], clock: Clock
) -> None:
    reward = create_reward(client, headers, 20, name="ТикТок", duration_minutes=20)

    session = buy(client, headers, reward["id"])["session"]

    assert (session["name"], session["reward_id"]) == ("ТикТок", reward["id"])
    assert (session["started_at"], session["ends_at"]) == (clock.at(0), clock.at(20))
    assert session["finished_at"] is None
    assert [s["id"] for s in active(client, headers)] == [session["id"]]


def test_purchase_without_duration_has_no_session(
    client: TestClient, headers: dict[str, str]
) -> None:
    reward = create_reward(client, headers, 20)
    assert buy(client, headers, reward["id"])["session"] is None
    assert active(client, headers) == []


def test_name_is_kept_after_rename(client: TestClient, headers: dict[str, str]) -> None:
    reward = create_reward(client, headers, 10, name="Сериал", duration_minutes=45)
    buy(client, headers, reward["id"])
    client.patch(f"{API}/rewards/{reward['id']}", headers=headers, json={"name": "Кино"})
    assert active(client, headers)[0]["name"] == "Сериал"


# --- очередь ---


def test_queue_chains_purchases(client: TestClient, headers: dict[str, str], clock: Clock) -> None:
    """Два ТикТока по 15 минут — 30 минут подряд, а не параллельно."""
    tiktok = create_reward(client, headers, 10, name="ТикТок", duration_minutes=15)
    series = create_reward(client, headers, 10, name="Сериал", duration_minutes=45)

    buy(client, headers, tiktok["id"])
    clock.now = T0 + timedelta(minutes=5)
    buy(client, headers, tiktok["id"])
    buy(client, headers, series["id"])

    assert timeline(client, headers) == [
        ("ТикТок", clock.at(0), clock.at(15)),
        ("ТикТок", clock.at(15), clock.at(30)),
        ("Сериал", clock.at(30), clock.at(75)),
    ]


def test_parallel_purchase_starts_now(
    client: TestClient, headers: dict[str, str], clock: Clock
) -> None:
    tiktok = create_reward(client, headers, 10, name="ТикТок", duration_minutes=15)
    series = create_reward(client, headers, 10, name="Сериал", duration_minutes=45)

    buy(client, headers, series["id"])
    clock.now = T0 + timedelta(minutes=5)
    buy(client, headers, tiktok["id"], queue=False)
    # Следующий в очередь — за последней из идущих, то есть за сериалом.
    buy(client, headers, tiktok["id"])

    assert timeline(client, headers) == [
        ("Сериал", clock.at(0), clock.at(45)),
        ("ТикТок", clock.at(5), clock.at(20)),
        ("ТикТок", clock.at(45), clock.at(60)),
    ]


def test_queue_after_expired_starts_now(
    client: TestClient, headers: dict[str, str], clock: Clock
) -> None:
    tiktok = create_reward(client, headers, 10, name="ТикТок", duration_minutes=15)
    buy(client, headers, tiktok["id"])
    clock.now = T0 + timedelta(minutes=20)  # первый уже закончился

    session = buy(client, headers, tiktok["id"])["session"]

    assert session["started_at"] == clock.at(20)
    assert timeline(client, headers) == [("ТикТок", clock.at(20), clock.at(35))]


def test_finish_early_pulls_queue_forward(
    client: TestClient, headers: dict[str, str], clock: Clock
) -> None:
    tiktok = create_reward(client, headers, 10, name="ТикТок", duration_minutes=15)
    series = create_reward(client, headers, 10, name="Сериал", duration_minutes=45)
    first = buy(client, headers, tiktok["id"])["session"]
    buy(client, headers, tiktok["id"])
    buy(client, headers, series["id"])

    clock.now = T0 + timedelta(minutes=10)
    assert finish(client, headers, first["id"]) == 200

    # Второй ТикТок начинается сразу, сериал — за ним, длительности сохранены.
    assert timeline(client, headers) == [
        ("ТикТок", clock.at(10), clock.at(25)),
        ("Сериал", clock.at(25), clock.at(70)),
    ]
    # Монеты не возвращаются.
    assert client.get(f"{API}/me", headers=headers).json()["balance"] == 170


def test_cancel_waiting_pulls_later_forward(
    client: TestClient, headers: dict[str, str], clock: Clock
) -> None:
    tiktok = create_reward(client, headers, 10, name="ТикТок", duration_minutes=15)
    series = create_reward(client, headers, 10, name="Сериал", duration_minutes=45)
    buy(client, headers, tiktok["id"])
    waiting = buy(client, headers, tiktok["id"])["session"]
    buy(client, headers, series["id"])

    clock.now = T0 + timedelta(minutes=5)
    assert finish(client, headers, waiting["id"]) == 200

    assert timeline(client, headers) == [
        ("ТикТок", clock.at(0), clock.at(15)),
        ("Сериал", clock.at(15), clock.at(60)),
    ]


def test_finish_parallel_does_not_pull_past_running(
    client: TestClient, headers: dict[str, str], clock: Clock
) -> None:
    """Очередь стоит за самой долгой из идущих: досрочный конец короткой её не сдвигает."""
    tiktok = create_reward(client, headers, 10, name="ТикТок", duration_minutes=15)
    series = create_reward(client, headers, 10, name="Сериал", duration_minutes=45)
    buy(client, headers, series["id"])
    short = buy(client, headers, tiktok["id"], queue=False)["session"]
    buy(client, headers, tiktok["id"])  # в очереди с 45-й минуты

    clock.now = T0 + timedelta(minutes=5)
    assert finish(client, headers, short["id"]) == 200

    assert timeline(client, headers) == [
        ("Сериал", clock.at(0), clock.at(45)),
        ("ТикТок", clock.at(45), clock.at(60)),
    ]


def test_finish_twice_expired_or_foreign(
    client: TestClient, db: Session, headers: dict[str, str], clock: Clock
) -> None:
    reward = create_reward(client, headers, 10, duration_minutes=5)
    session_id = buy(client, headers, reward["id"])["session"]["id"]

    stranger = auth_headers(register(client, email="stranger@example.com"))
    assert finish(client, stranger, session_id) == 404
    assert active(client, stranger) == []

    clock.now = T0 + timedelta(minutes=6)
    assert finish(client, headers, session_id) == 409
    assert active(client, headers) == []

    other = buy(client, headers, reward["id"])["session"]
    assert finish(client, headers, other["id"]) == 200
    assert finish(client, headers, other["id"]) == 409
    assert db.get(RewardSession, other["id"]).finished_at == clock.now
