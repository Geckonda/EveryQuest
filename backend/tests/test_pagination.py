"""Пагинация по курсору (летопись, архив квестов) и потолки на число записей."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import auth_tokens, limits
from app.models import Quest, Transaction
from tests.conftest import auth_headers, register

API = "/api/v1"


@pytest.fixture
def headers(client: TestClient) -> dict[str, str]:
    return auth_headers(register(client))


@pytest.fixture
def tier_id(client: TestClient, headers: dict[str, str]) -> int:
    return client.get(f"{API}/tiers", headers=headers).json()[0]["id"]


def manual(client: TestClient, headers: dict[str, str], amount: int) -> None:
    response = client.post(f"{API}/transactions/manual", headers=headers, json={"amount": amount})
    assert response.status_code == 201, response.text


def walk(client: TestClient, headers: dict[str, str], url: str, limit: int) -> list[list[dict]]:
    """Все страницы по курсору."""
    pages, cursor = [], None
    while True:
        sep = "&" if "?" in url else "?"
        query = f"{url}{sep}limit={limit}" + (f"&cursor={cursor}" if cursor else "")
        body = client.get(query, headers=headers).json()
        pages.append(body["items"])
        cursor = body["next_cursor"]
        if cursor is None:
            return pages


def close_new(client: TestClient, headers: dict[str, str], tier_id: int, name: str) -> int:
    quest = client.post(
        f"{API}/quests", headers=headers, json={"name": name, "tier_id": tier_id}
    ).json()
    client.post(f"{API}/quests/{quest['id']}/complete", headers=headers)
    return quest["id"]


# --- летопись ---


def test_transactions_walk_all_pages_in_order(client: TestClient, headers: dict[str, str]) -> None:
    for amount in range(1, 8):
        manual(client, headers, amount)

    pages = walk(client, headers, f"{API}/transactions", limit=3)

    assert [len(p) for p in pages] == [3, 3, 1]
    assert [t["amount"] for p in pages for t in p] == [7, 6, 5, 4, 3, 2, 1]


def test_transactions_new_record_does_not_duplicate(
    client: TestClient, headers: dict[str, str]
) -> None:
    """Сдвиг (offset) задвоил бы строку, если сверху появилась запись; курсор — нет."""
    for amount in range(1, 5):
        manual(client, headers, amount)
    first = client.get(f"{API}/transactions?limit=2", headers=headers).json()

    manual(client, headers, 100)  # пока листали — новый штраф, заказ, поправка
    second = client.get(
        f"{API}/transactions?limit=2&cursor={first['next_cursor']}", headers=headers
    ).json()

    assert [t["amount"] for t in first["items"]] == [4, 3]
    assert [t["amount"] for t in second["items"]] == [2, 1]
    assert second["next_cursor"] is None


def test_transactions_same_timestamp_ordered_by_id(
    client: TestClient, db: Session, headers: dict[str, str]
) -> None:
    """Записи с одинаковым временем не теряются и не дублируются на границе страниц."""
    for amount in range(1, 6):
        manual(client, headers, amount)
    same = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)
    for transaction in db.scalars(select(Transaction)):
        transaction.created_at = same
    db.flush()

    pages = walk(client, headers, f"{API}/transactions", limit=2)
    assert [t["amount"] for p in pages for t in p] == [5, 4, 3, 2, 1]


def test_transactions_cursor_respects_type_filter(
    client: TestClient, headers: dict[str, str]
) -> None:
    for amount in (5, -1, 6, -2, 7):
        manual(client, headers, amount)
    reward = client.post(f"{API}/rewards", headers=headers, json={"name": "Кофе", "price": 1})
    for _ in range(3):
        client.post(f"{API}/rewards/{reward.json()['id']}/purchase", headers=headers)

    pages = walk(client, headers, f"{API}/transactions?type=purchase", limit=2)
    assert [t["type"] for p in pages for t in p] == ["purchase"] * 3


@pytest.mark.parametrize(
    "cursor",
    [
        "garbage",
        "bm90LWEtY3Vyc29y",  # base64 без разделителя
        "MjAyNi0xMC0yMlQxMjowMHx4",  # «2026-10-22T12:00|x» — без пояса и id не число
    ],
)
def test_bad_cursor(client: TestClient, headers: dict[str, str], cursor: str) -> None:
    for url in (f"{API}/transactions", f"{API}/quests/archive"):
        response = client.get(f"{url}?cursor={cursor}", headers=headers)
        assert response.status_code == 422, url


# --- архив квестов ---


def test_archive_pages_newest_closed_first(
    client: TestClient, db: Session, headers: dict[str, str], tier_id: int
) -> None:
    ids = [close_new(client, headers, tier_id, f"Квест {i}") for i in range(5)]
    client.post(f"{API}/quests", headers=headers, json={"name": "Открытый", "tier_id": tier_id})
    # Закрыты в обратном порядке создания: первый — самый свежий.
    base = datetime.now(UTC)
    for shift, quest_id in enumerate(ids):
        db.get(Quest, quest_id).closed_at = base - timedelta(minutes=shift)
    db.flush()

    pages = walk(client, headers, f"{API}/quests/archive", limit=2)

    assert [len(p) for p in pages] == [2, 2, 1]
    assert [q["id"] for p in pages for q in p] == ids  # открытый в архив не попал


def test_archive_new_closure_does_not_duplicate(
    client: TestClient, headers: dict[str, str], tier_id: int
) -> None:
    old = [close_new(client, headers, tier_id, f"Старый {i}") for i in range(4)]
    first = client.get(f"{API}/quests/archive?limit=2", headers=headers).json()
    close_new(client, headers, tier_id, "Новый")  # закрыли, пока листали
    second = client.get(
        f"{API}/quests/archive?limit=2&cursor={first['next_cursor']}", headers=headers
    ).json()

    seen = [q["id"] for q in first["items"] + second["items"]]
    assert sorted(seen) == sorted(old)
    assert len(set(seen)) == 4


def test_archive_is_private(client: TestClient, headers: dict[str, str], tier_id: int) -> None:
    close_new(client, headers, tier_id, "Мой")
    stranger = auth_headers(register(client, email="stranger@example.com"))
    assert client.get(f"{API}/quests/archive", headers=stranger).json() == {
        "items": [],
        "next_cursor": None,
    }


# --- потолки ---


@pytest.fixture
def small_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    """Маленькие потолки — чтобы не создавать по 500 записей."""
    for name in ("MAX_ACTIVE_QUESTS", "MAX_TEMPLATES", "MAX_REWARDS", "MAX_CATEGORIES"):
        monkeypatch.setattr(limits, name, 2)
    # Тиров по умолчанию уже пять — потолок чуть выше.
    monkeypatch.setattr(limits, "MAX_TIERS", 6)


@pytest.mark.usefixtures("small_limits")
def test_active_quests_cap(client: TestClient, headers: dict[str, str], tier_id: int) -> None:
    def create(name: str):
        return client.post(
            f"{API}/quests", headers=headers, json={"name": name, "tier_id": tier_id}
        )

    first = create("Один").json()
    create("Два")
    blocked = create("Три")
    assert blocked.status_code == 409
    assert "Слишком много открытых квестов" in blocked.json()["detail"]

    # Сдали один — место освободилось.
    client.post(f"{API}/quests/{first['id']}/complete", headers=headers)
    assert create("Три").status_code == 201


@pytest.mark.usefixtures("small_limits")
@pytest.mark.parametrize(
    ("url", "body"),
    [
        ("/rewards", {"name": "Кофе", "price": 1}),
        ("/categories", {"name": "Дела"}),
        ("/recurring-quests", {"name": "Зарядка", "frequency": "daily"}),
    ],
)
def test_catalog_caps_count_only_active(
    client: TestClient, headers: dict[str, str], tier_id: int, url: str, body: dict
) -> None:
    if url == "/recurring-quests":
        body = {**body, "tier_id": tier_id}
    if url == "/categories":
        # У нового пользователя уже есть категории по умолчанию — уберём их в архив.
        for category in client.get(f"{API}/categories", headers=headers).json():
            client.patch(
                f"{API}/categories/{category['id']}", headers=headers, json={"is_archived": True}
            )
    made = [client.post(f"{API}{url}", headers=headers, json=body).json() for _ in range(2)]
    assert client.post(f"{API}{url}", headers=headers, json=body).status_code == 409

    # Архивные не считаются: убрали одну — можно создать новую…
    client.patch(f"{API}{url}/{made[0]['id']}", headers=headers, json={"is_archived": True})
    assert client.post(f"{API}{url}", headers=headers, json=body).status_code == 201
    # …но вернуть из архива сверх потолка нельзя.
    restore = client.patch(
        f"{API}{url}/{made[0]['id']}", headers=headers, json={"is_archived": False}
    )
    assert restore.status_code == 409


@pytest.mark.usefixtures("small_limits")
def test_tiers_cap(client: TestClient, headers: dict[str, str]) -> None:
    body = {"name": "Шестой", "level": 5, "default_reward": 1}
    assert client.post(f"{API}/tiers", headers=headers, json=body).status_code == 201
    assert client.post(f"{API}/tiers", headers=headers, json=body).status_code == 409


def test_sessions_cap_evicts_oldest(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_tokens, "MAX_SESSIONS", 3)
    tokens = [register(client, email="hero@example.com", password="secret-pass")]
    for _ in range(3):
        tokens.append(
            client.post(
                f"{API}/auth/login",
                json={"email": "hero@example.com", "password": "secret-pass"},
            ).json()
        )

    devices = client.get(f"{API}/auth/sessions", headers=auth_headers(tokens[-1])).json()
    assert len(devices) == 3
    # Самый давний вход вышел сам; свежие работают.
    assert client.get(f"{API}/me", headers=auth_headers(tokens[0])).status_code == 401
    assert client.get(f"{API}/me", headers=auth_headers(tokens[-1])).status_code == 200
