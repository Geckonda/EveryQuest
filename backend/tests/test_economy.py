import threading

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app.main import app
from app.models import Quest, Transaction, User
from tests.conftest import auth_headers, register

API = "/api/v1"


@pytest.fixture
def headers(client: TestClient) -> dict[str, str]:
    return auth_headers(register(client))


def balance(client: TestClient, headers: dict[str, str]) -> int:
    return client.get(f"{API}/me", headers=headers).json()["balance"]


def earn(client: TestClient, headers: dict[str, str], amount: int) -> None:
    """Заработать монеты честно — выполнив квест."""
    tier_id = client.get(f"{API}/tiers", headers=headers).json()[0]["id"]
    quest = client.post(
        f"{API}/quests",
        headers=headers,
        json={"name": "Работа", "tier_id": tier_id, "reward": amount},
    ).json()
    assert client.post(f"{API}/quests/{quest['id']}/complete", headers=headers).status_code == 200


def create_reward(client: TestClient, headers: dict[str, str], price: int, **extra) -> dict:
    response = client.post(
        f"{API}/rewards", headers=headers, json={"name": "Кино", "price": price, **extra}
    )
    assert response.status_code == 201
    return response.json()


# --- покупки ---


def test_purchase(client: TestClient, headers: dict[str, str]) -> None:
    earn(client, headers, 100)
    reward = create_reward(client, headers, 30)

    response = client.post(f"{API}/rewards/{reward['id']}/purchase", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["balance"] == 70
    assert body["transaction"]["amount"] == -30
    assert body["transaction"]["type"] == "purchase"
    assert body["transaction"]["title"] == "Кино"
    assert balance(client, headers) == 70


def test_purchase_with_exact_balance(client: TestClient, headers: dict[str, str]) -> None:
    earn(client, headers, 30)
    reward = create_reward(client, headers, 30)
    assert client.post(f"{API}/rewards/{reward['id']}/purchase", headers=headers).status_code == 200
    assert balance(client, headers) == 0


def test_purchase_insufficient_funds(client: TestClient, headers: dict[str, str]) -> None:
    earn(client, headers, 20)
    reward = create_reward(client, headers, 30)

    response = client.post(f"{API}/rewards/{reward['id']}/purchase", headers=headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "Не хватает монет: нужно 30, на счету 20"
    assert balance(client, headers) == 20


def test_cannot_buy_when_in_debt(client: TestClient, db: Session, headers: dict[str, str]) -> None:
    user_id = client.get(f"{API}/me", headers=headers).json()["id"]
    db.get(User, user_id).balance = -10  # как после штрафа
    db.flush()
    free = create_reward(client, headers, 0)
    paid = create_reward(client, headers, 5)

    assert client.post(f"{API}/rewards/{paid['id']}/purchase", headers=headers).status_code == 400
    assert client.post(f"{API}/rewards/{free['id']}/purchase", headers=headers).status_code == 400


def test_purchase_archived_or_foreign_reward(client: TestClient, headers: dict[str, str]) -> None:
    earn(client, headers, 100)
    reward = create_reward(client, headers, 10)
    client.patch(f"{API}/rewards/{reward['id']}", headers=headers, json={"is_archived": True})

    archived = client.post(f"{API}/rewards/{reward['id']}/purchase", headers=headers)
    assert archived.status_code == 409

    stranger = auth_headers(register(client, email="stranger@example.com"))
    foreign = client.post(f"{API}/rewards/{reward['id']}/purchase", headers=stranger)
    assert foreign.status_code == 404
    assert balance(client, headers) == 100


# --- ручная корректировка ---


def test_manual_transaction(client: TestClient, headers: dict[str, str]) -> None:
    plus = client.post(
        f"{API}/transactions/manual", headers=headers, json={"amount": 50, "note": "Бонус"}
    )
    assert plus.status_code == 201
    assert plus.json()["balance"] == 50
    assert plus.json()["transaction"]["note"] == "Бонус"

    minus = client.post(f"{API}/transactions/manual", headers=headers, json={"amount": -50})
    assert minus.status_code == 201
    assert minus.json()["balance"] == 0


@pytest.mark.parametrize("amount", [0, -1])
def test_manual_transaction_rejected(
    client: TestClient, headers: dict[str, str], amount: int
) -> None:
    """Ноль бессмыслен; в минус вручную уйти нельзя — только от штрафов."""
    response = client.post(f"{API}/transactions/manual", headers=headers, json={"amount": amount})
    assert response.status_code in (400, 422)
    assert balance(client, headers) == 0


# --- журнал ---


def test_transactions_history(client: TestClient, headers: dict[str, str]) -> None:
    earn(client, headers, 100)
    reward = create_reward(client, headers, 30)
    client.post(f"{API}/rewards/{reward['id']}/purchase", headers=headers)
    client.post(
        f"{API}/transactions/manual", headers=headers, json={"amount": 5, "note": "Найдено"}
    )

    page = client.get(f"{API}/transactions", headers=headers).json()
    assert page["total"] == 3
    summary = [(t["type"], t["amount"], t["balance_after"], t["title"]) for t in page["items"]]
    assert summary == [
        ("manual", 5, 75, None),
        ("purchase", -30, 70, "Кино"),
        ("quest_reward", 100, 100, "Работа"),
    ]

    first = client.get(f"{API}/transactions?limit=1&offset=1", headers=headers).json()
    assert first["total"] == 3
    assert [t["type"] for t in first["items"]] == ["purchase"]

    only_purchases = client.get(f"{API}/transactions?type=purchase", headers=headers).json()
    assert only_purchases["total"] == 1

    stranger = auth_headers(register(client, email="stranger@example.com"))
    assert client.get(f"{API}/transactions", headers=stranger).json() == {"items": [], "total": 0}


def test_balance_matches_transactions_sum(
    client: TestClient, db: Session, headers: dict[str, str]
) -> None:
    """balance в users — кэш; он всегда равен сумме журнала."""
    earn(client, headers, 40)
    earn(client, headers, 25)
    reward = create_reward(client, headers, 50)
    client.post(f"{API}/rewards/{reward['id']}/purchase", headers=headers)
    client.post(f"{API}/transactions/manual", headers=headers, json={"amount": -5})

    user_id = client.get(f"{API}/me", headers=headers).json()["id"]
    total = db.scalar(select(func.sum(Transaction.amount)).where(Transaction.user_id == user_id))
    assert total == balance(client, headers) == 10


# --- параллельные запросы ---


def run_concurrently(n: int, request) -> list[int]:
    """Запускает n запросов одновременно, возвращает коды ответов.

    request(client, i) получает номер потока — чтобы смешивать разные запросы.
    """
    barrier = threading.Barrier(n)
    codes: list[int] = []

    def worker(i: int) -> None:
        with TestClient(app) as client:
            barrier.wait()
            codes.append(request(client, i).status_code)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return sorted(codes)


@pytest.mark.usefixtures("committing_db")
def test_concurrent_purchases_do_not_overspend(engine: Engine) -> None:
    with TestClient(app) as client:
        headers = auth_headers(register(client, email="race-buy@example.com"))
        earn(client, headers, 30)
        reward = create_reward(client, headers, 30)

    codes = run_concurrently(
        5, lambda c, _: c.post(f"{API}/rewards/{reward['id']}/purchase", headers=headers)
    )

    assert codes == [200, 400, 400, 400, 400]
    with TestClient(app) as client:
        assert balance(client, headers) == 0


@pytest.mark.usefixtures("committing_db")
def test_concurrent_completion_rewards_once(engine: Engine) -> None:
    with TestClient(app) as client:
        headers = auth_headers(register(client, email="race-quest@example.com"))
        tier_id = client.get(f"{API}/tiers", headers=headers).json()[0]["id"]
        quest = client.post(
            f"{API}/quests", headers=headers, json={"name": "Гонка", "tier_id": tier_id}
        ).json()

    codes = run_concurrently(
        5, lambda c, _: c.post(f"{API}/quests/{quest['id']}/complete", headers=headers)
    )

    assert codes == [200, 409, 409, 409, 409]
    with Session(engine) as session:
        rewards = session.scalar(
            select(func.count()).select_from(Transaction).where(Transaction.quest_id == quest["id"])
        )
        assert rewards == 1
        assert session.get(Quest, quest["id"]).status == "completed"


@pytest.mark.usefixtures("committing_db")
def test_concurrent_complete_and_fail(engine: Engine) -> None:
    """Сдача и провал одновременно: побеждает один, деньги двигаются один раз."""
    with TestClient(app) as client:
        headers = auth_headers(register(client, email="race-fail@example.com"))
        tier_id = client.get(f"{API}/tiers", headers=headers).json()[0]["id"]
        quest = client.post(
            f"{API}/quests",
            headers=headers,
            json={"name": "Гонка", "tier_id": tier_id, "reward": 10, "penalty": 5},
        ).json()

    actions = ["complete", "fail"] * 3
    codes = run_concurrently(
        len(actions),
        lambda c, i: c.post(f"{API}/quests/{quest['id']}/{actions[i]}", headers=headers),
    )

    assert codes == [200, 409, 409, 409, 409, 409]
    with Session(engine) as session:
        final = session.get(Quest, quest["id"])
        types = session.scalars(
            select(Transaction.type).where(Transaction.quest_id == quest["id"])
        ).all()
        user_balance = session.scalar(select(User.balance).where(User.id == final.user_id))
    assert (final.status, types, user_balance) in [
        ("completed", ["quest_reward"], 10),
        ("failed", ["penalty"], -5),
    ]
