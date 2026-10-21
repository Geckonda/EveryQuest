from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Quest, RecurringQuest
from tests.conftest import auth_headers, register

API = "/api/v1"


@pytest.fixture
def headers(client: TestClient) -> dict[str, str]:
    return auth_headers(register(client))


def first_id(client: TestClient, headers: dict[str, str], resource: str) -> int:
    return client.get(f"{API}/{resource}", headers=headers).json()[0]["id"]


def add_quest(db: Session, user_id: int, tier_id: int, **fields) -> Quest:
    quest = Quest(user_id=user_id, tier_id=tier_id, name="Пробежка", reward=10, penalty=5, **fields)
    db.add(quest)
    db.flush()
    return quest


def add_template(db: Session, user_id: int, tier_id: int, **fields) -> RecurringQuest:
    template = RecurringQuest(
        user_id=user_id,
        tier_id=tier_id,
        name="Зарядка",
        reward=10,
        penalty=5,
        frequency="daily",
        start_date=date(2026, 1, 1),
        **fields,
    )
    db.add(template)
    db.flush()
    return template


def me_id(client: TestClient, headers: dict[str, str]) -> int:
    return client.get(f"{API}/me", headers=headers).json()["id"]


# --- тиры ---


def test_create_and_update_tier(client: TestClient, headers: dict[str, str]) -> None:
    created = client.post(
        f"{API}/tiers",
        headers=headers,
        json={"name": "Эпик", "level": 5, "default_reward": 500},
    )
    assert created.status_code == 201
    tier = created.json()
    assert tier["color"] is None

    updated = client.patch(
        f"{API}/tiers/{tier['id']}", headers=headers, json={"name": "Легенда", "color": "#ff8800"}
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Легенда"
    assert updated.json()["default_reward"] == 500  # не переданное поле не меняется

    cleared = client.patch(f"{API}/tiers/{tier['id']}", headers=headers, json={"color": None})
    assert cleared.json()["color"] is None


@pytest.mark.parametrize(
    "body",
    [
        {"name": None},
        {"level": 6},
        {"default_reward": -1},
        {"color": "red"},
        {"name": ""},
    ],
)
def test_update_tier_validation(client: TestClient, headers: dict[str, str], body: dict) -> None:
    tier_id = first_id(client, headers, "tiers")
    assert client.patch(f"{API}/tiers/{tier_id}", headers=headers, json=body).status_code == 422


def test_archive_and_restore_tier(client: TestClient, headers: dict[str, str]) -> None:
    tier_id = first_id(client, headers, "tiers")

    archived = client.patch(f"{API}/tiers/{tier_id}", headers=headers, json={"is_archived": True})
    assert archived.status_code == 200

    active_ids = {t["id"] for t in client.get(f"{API}/tiers", headers=headers).json()}
    assert tier_id not in active_ids
    all_tiers = client.get(f"{API}/tiers?include_archived=true", headers=headers).json()
    assert tier_id in {t["id"] for t in all_tiers}

    restored = client.patch(f"{API}/tiers/{tier_id}", headers=headers, json={"is_archived": False})
    assert restored.json()["is_archived"] is False


def test_archive_tier_blocked_by_active_quest_and_template(
    client: TestClient, db: Session, headers: dict[str, str]
) -> None:
    user_id, tier_id = me_id(client, headers), first_id(client, headers, "tiers")
    quest = add_quest(db, user_id, tier_id)
    template = add_template(db, user_id, tier_id, is_active=False)  # пауза тоже мешает

    response = client.patch(f"{API}/tiers/{tier_id}", headers=headers, json={"is_archived": True})

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["quests"] == [{"id": quest.id, "name": "Пробежка"}]
    assert detail["recurring_quests"] == [{"id": template.id, "name": "Зарядка"}]
    assert client.get(f"{API}/tiers", headers=headers).json()[0]["id"] == tier_id


def test_archive_tier_allowed_with_finished_quests(
    client: TestClient, db: Session, headers: dict[str, str]
) -> None:
    user_id, tier_id = me_id(client, headers), first_id(client, headers, "tiers")
    add_quest(db, user_id, tier_id, status="completed", close_reason="completed")
    add_quest(db, user_id, tier_id, status="failed", close_reason="expired")
    add_template(db, user_id, tier_id, is_archived=True)

    response = client.patch(f"{API}/tiers/{tier_id}", headers=headers, json={"is_archived": True})
    assert response.status_code == 200


def test_rename_tier_with_active_quest_allowed(
    client: TestClient, db: Session, headers: dict[str, str]
) -> None:
    user_id, tier_id = me_id(client, headers), first_id(client, headers, "tiers")
    add_quest(db, user_id, tier_id)

    response = client.patch(f"{API}/tiers/{tier_id}", headers=headers, json={"name": "Новое"})
    assert response.status_code == 200


# --- категории ---


def test_category_crud_and_archive_conflict(
    client: TestClient, db: Session, headers: dict[str, str]
) -> None:
    created = client.post(
        f"{API}/categories",
        headers=headers,
        json={"name": "Музыка", "description": "Гитара", "color": "#123abc"},
    )
    assert created.status_code == 201
    category_id = created.json()["id"]

    cleared = client.patch(
        f"{API}/categories/{category_id}", headers=headers, json={"description": None}
    )
    assert cleared.json()["description"] is None

    user_id, tier_id = me_id(client, headers), first_id(client, headers, "tiers")
    add_quest(db, user_id, tier_id, category_id=category_id)

    blocked = client.patch(
        f"{API}/categories/{category_id}", headers=headers, json={"is_archived": True}
    )
    assert blocked.status_code == 409
    assert len(blocked.json()["detail"]["quests"]) == 1


# --- траты ---


def test_reward_crud(client: TestClient, headers: dict[str, str]) -> None:
    assert client.get(f"{API}/rewards", headers=headers).json() == []

    created = client.post(
        f"{API}/rewards",
        headers=headers,
        json={"name": "Серия сериала", "price": 30, "duration_minutes": 45},
    )
    assert created.status_code == 201
    reward_id = created.json()["id"]

    client.post(f"{API}/rewards", headers=headers, json={"name": "Кофе", "price": 10})
    names = [r["name"] for r in client.get(f"{API}/rewards", headers=headers).json()]
    assert names == ["Кофе", "Серия сериала"]  # по цене

    updated = client.patch(
        f"{API}/rewards/{reward_id}",
        headers=headers,
        json={"price": 40, "duration_minutes": None, "is_archived": True},
    )
    assert updated.status_code == 200
    assert updated.json()["price"] == 40
    assert updated.json()["duration_minutes"] is None
    assert len(client.get(f"{API}/rewards", headers=headers).json()) == 1


@pytest.mark.parametrize(
    "body",
    [
        {"name": "Без цены"},
        {"name": "Минус", "price": -5},
        {"name": "", "price": 5},
        {"name": "Ноль минут", "price": 5, "duration_minutes": 0},
    ],
)
def test_reward_validation(client: TestClient, headers: dict[str, str], body: dict) -> None:
    assert client.post(f"{API}/rewards", headers=headers, json=body).status_code == 422


# --- изоляция ---


@pytest.mark.parametrize("resource", ["tiers", "categories", "rewards"])
def test_cannot_touch_other_users_objects(client: TestClient, resource: str) -> None:
    owner = auth_headers(register(client, email="owner@example.com"))
    stranger = auth_headers(register(client, email="stranger@example.com"))
    if resource == "rewards":
        client.post(f"{API}/rewards", headers=owner, json={"name": "Кино", "price": 50})
    obj_id = first_id(client, owner, resource)

    response = client.patch(f"{API}/{resource}/{obj_id}", headers=stranger, json={"name": "Моё"})
    assert response.status_code == 404
    assert client.get(f"{API}/{resource}", headers=owner).json()[0]["name"] != "Моё"


def test_missing_object_returns_404(client: TestClient, headers: dict[str, str]) -> None:
    response = client.patch(f"{API}/tiers/999999", headers=headers, json={"name": "X"})
    assert response.status_code == 404
