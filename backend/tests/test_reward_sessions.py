from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import RewardSession
from tests.conftest import auth_headers, register
from tests.test_economy import create_reward, earn

API = "/api/v1"


@pytest.fixture
def headers(client: TestClient) -> dict[str, str]:
    headers = auth_headers(register(client))
    earn(client, headers, 100)
    return headers


def buy(client: TestClient, headers: dict[str, str], reward_id: int) -> dict:
    response = client.post(f"{API}/rewards/{reward_id}/purchase", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def active(client: TestClient, headers: dict[str, str]) -> list[dict]:
    return client.get(f"{API}/reward-sessions/active", headers=headers).json()


def test_purchase_with_duration_starts_session(client: TestClient, headers: dict[str, str]) -> None:
    reward = create_reward(client, headers, 20, name="ТикТок", duration_minutes=20)

    body = buy(client, headers, reward["id"])

    session = body["session"]
    assert (session["name"], session["reward_id"]) == ("ТикТок", reward["id"])
    started = datetime.fromisoformat(session["started_at"])
    assert datetime.fromisoformat(session["ends_at"]) - started == timedelta(minutes=20)
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


def test_active_sorted_and_expired_hidden(
    client: TestClient, db: Session, headers: dict[str, str]
) -> None:
    long = create_reward(client, headers, 10, name="Игры", duration_minutes=120)
    short = create_reward(client, headers, 10, name="ТикТок", duration_minutes=15)
    expired = create_reward(client, headers, 10, name="Кофе", duration_minutes=10)
    long_id = buy(client, headers, long["id"])["session"]["id"]
    short_id = buy(client, headers, short["id"])["session"]["id"]
    expired_id = buy(client, headers, expired["id"])["session"]["id"]
    # Время «Кофе» уже вышло.
    session = db.get(RewardSession, expired_id)
    session.started_at -= timedelta(minutes=11)
    session.ends_at -= timedelta(minutes=11)
    db.flush()

    assert [s["id"] for s in active(client, headers)] == [short_id, long_id]


def test_finish_early(client: TestClient, db: Session, headers: dict[str, str]) -> None:
    reward = create_reward(client, headers, 30, duration_minutes=30)
    session = buy(client, headers, reward["id"])["session"]

    finished = client.post(f"{API}/reward-sessions/{session['id']}/finish", headers=headers)
    assert finished.status_code == 200
    assert finished.json()["finished_at"] is not None
    assert active(client, headers) == []
    # Монеты не возвращаются.
    assert client.get(f"{API}/me", headers=headers).json()["balance"] == 70

    again = client.post(f"{API}/reward-sessions/{session['id']}/finish", headers=headers)
    assert again.status_code == 409


def test_finish_expired_or_foreign(
    client: TestClient, db: Session, headers: dict[str, str]
) -> None:
    reward = create_reward(client, headers, 10, duration_minutes=5)
    session_id = buy(client, headers, reward["id"])["session"]["id"]

    stranger = auth_headers(register(client, email="stranger@example.com"))
    foreign = client.post(f"{API}/reward-sessions/{session_id}/finish", headers=stranger)
    assert foreign.status_code == 404
    assert active(client, stranger) == []

    session = db.get(RewardSession, session_id)
    session.started_at -= timedelta(minutes=6)
    session.ends_at -= timedelta(minutes=6)
    db.flush()
    late = client.post(f"{API}/reward-sessions/{session_id}/finish", headers=headers)
    assert late.status_code == 409
