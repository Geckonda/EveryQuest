"""Удаление тиров, категорий, позиций меню и шаблонов — без потери истории."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Quest, RecurringQuest, RewardSession, Tier
from tests.conftest import auth_headers, register
from tests.test_economy import earn

API = "/api/v1"


@pytest.fixture
def headers(client: TestClient) -> dict[str, str]:
    return auth_headers(register(client))


@pytest.fixture
def tiers(client: TestClient, headers: dict[str, str]) -> list[dict]:
    return client.get(f"{API}/tiers", headers=headers).json()


def create_quest(client: TestClient, headers: dict[str, str], **body) -> dict:
    response = client.post(f"{API}/quests", headers=headers, json={"name": "Пробежка", **body})
    assert response.status_code == 201, response.text
    return response.json()


def create_template(client: TestClient, headers: dict[str, str], **body) -> dict:
    response = client.post(
        f"{API}/recurring-quests",
        headers=headers,
        json={"name": "Зарядка", "frequency": "daily", **body},
    )
    assert response.status_code == 201, response.text
    return response.json()


# --- тиры ---


def test_delete_unused_tier(client: TestClient, headers: dict[str, str]) -> None:
    created = client.post(
        f"{API}/tiers", headers=headers, json={"name": "Лишний", "level": 1, "default_reward": 1}
    ).json()

    assert client.delete(f"{API}/tiers/{created['id']}", headers=headers).status_code == 204
    names = [
        t["name"] for t in client.get(f"{API}/tiers?include_archived=true", headers=headers).json()
    ]
    assert "Лишний" not in names


def test_delete_used_tier_asks_where_to_move(
    client: TestClient, db: Session, headers: dict[str, str], tiers: list[dict]
) -> None:
    old, target = tiers[0], tiers[1]
    open_quest = create_quest(client, headers, tier_id=old["id"], reward=7, penalty=3)
    done = create_quest(client, headers, tier_id=old["id"])
    client.post(f"{API}/quests/{done['id']}/complete", headers=headers)
    template = create_template(client, headers, tier_id=old["id"])  # + экземпляр за сегодня

    blocked = client.delete(f"{API}/tiers/{old['id']}", headers=headers)
    assert blocked.status_code == 409
    detail = blocked.json()["detail"]
    assert (detail["quests"], detail["recurring_quests"]) == (3, 1)  # 2 + экземпляр шаблона

    moved = client.delete(f"{API}/tiers/{old['id']}?move_to={target['id']}", headers=headers)
    assert moved.status_code == 204
    assert db.get(Tier, old["id"]) is None
    for quest_id in (open_quest["id"], done["id"]):
        quest = db.get(Quest, quest_id)
        assert quest.tier_id == target["id"]
    # Награда и штраф квеста не меняются — меняется только печать.
    assert (db.get(Quest, open_quest["id"]).reward, db.get(Quest, open_quest["id"]).penalty) == (
        7,
        3,
    )
    assert db.get(RecurringQuest, template["id"]).tier_id == target["id"]


@pytest.mark.parametrize("target", ["same", "archived", "foreign", "missing"])
def test_delete_tier_bad_target(
    client: TestClient, headers: dict[str, str], tiers: list[dict], target: str
) -> None:
    old = tiers[0]
    create_quest(client, headers, tier_id=old["id"])
    if target == "same":
        move_to = old["id"]
    elif target == "archived":
        move_to = tiers[1]["id"]
        client.patch(f"{API}/tiers/{move_to}", headers=headers, json={"is_archived": True})
    elif target == "foreign":
        stranger = auth_headers(register(client, email="stranger@example.com"))
        move_to = client.get(f"{API}/tiers", headers=stranger).json()[0]["id"]
    else:
        move_to = 999_999

    response = client.delete(f"{API}/tiers/{old['id']}?move_to={move_to}", headers=headers)
    assert response.status_code in (404, 422), target
    assert client.get(f"{API}/tiers", headers=headers).json()[0]["id"] == old["id"]


def test_cannot_delete_last_active_tier(
    client: TestClient, headers: dict[str, str], tiers: list[dict]
) -> None:
    for tier in tiers[1:]:
        assert client.delete(f"{API}/tiers/{tier['id']}", headers=headers).status_code == 204

    last = client.delete(f"{API}/tiers/{tiers[0]['id']}", headers=headers)
    assert last.status_code == 409
    assert "последний тир" in last.json()["detail"]


def test_delete_archived_tier_even_if_it_was_last_in_archive(
    client: TestClient, headers: dict[str, str], tiers: list[dict]
) -> None:
    """Архивный тир удаляется спокойно: действующих от этого не убавится."""
    client.patch(f"{API}/tiers/{tiers[4]['id']}", headers=headers, json={"is_archived": True})
    assert client.delete(f"{API}/tiers/{tiers[4]['id']}", headers=headers).status_code == 204


# --- категории ---


def test_delete_category_unlinks_quests_and_templates(
    client: TestClient, db: Session, headers: dict[str, str], tiers: list[dict]
) -> None:
    category = client.get(f"{API}/categories", headers=headers).json()[0]
    quest = create_quest(client, headers, tier_id=tiers[0]["id"], category_id=category["id"])
    template = create_template(client, headers, tier_id=tiers[0]["id"], category_id=category["id"])

    assert client.delete(f"{API}/categories/{category['id']}", headers=headers).status_code == 204

    assert db.get(Quest, quest["id"]).category_id is None
    assert db.get(RecurringQuest, template["id"]).category_id is None
    ids = [
        c["id"]
        for c in client.get(f"{API}/categories?include_archived=true", headers=headers).json()
    ]
    assert category["id"] not in ids


# --- позиции меню ---


def test_delete_ordered_reward_keeps_name_in_chronicle(
    client: TestClient, db: Session, headers: dict[str, str]
) -> None:
    earn(client, headers, 100)
    reward = client.post(
        f"{API}/rewards",
        headers=headers,
        json={"name": "ТикТок", "price": 20, "duration_minutes": 15},
    ).json()
    client.post(f"{API}/rewards/{reward['id']}/purchase", headers=headers)

    assert client.delete(f"{API}/rewards/{reward['id']}", headers=headers).status_code == 204

    page = client.get(f"{API}/transactions?type=purchase", headers=headers).json()
    assert [(t["title"], t["amount"], t["reward_id"]) for t in page["items"]] == [
        ("ТикТок", -20, None)
    ]
    # Идущий сеанс траты остался — со своим названием, без ссылки.
    [session] = client.get(f"{API}/reward-sessions/active", headers=headers).json()
    assert (session["name"], session["reward_id"]) == ("ТикТок", None)
    assert db.scalar(select(func.count()).select_from(RewardSession)) == 1


def test_delete_never_ordered_reward(client: TestClient, headers: dict[str, str]) -> None:
    reward = client.post(
        f"{API}/rewards", headers=headers, json={"name": "Кофе", "price": 5}
    ).json()
    assert client.delete(f"{API}/rewards/{reward['id']}", headers=headers).status_code == 204
    assert client.get(f"{API}/rewards?include_archived=true", headers=headers).json() == []


# --- шаблоны ---


def test_delete_template_keeps_instances(
    client: TestClient, db: Session, headers: dict[str, str], tiers: list[dict]
) -> None:
    template = create_template(client, headers, tier_id=tiers[0]["id"])
    [instance] = db.scalars(select(Quest).where(Quest.recurring_quest_id == template["id"])).all()

    assert (
        client.delete(f"{API}/recurring-quests/{template['id']}", headers=headers).status_code
        == 204
    )

    assert db.get(RecurringQuest, template["id"]) is None
    db.refresh(instance)
    assert (instance.status, instance.recurring_quest_id) == ("active", None)
    # Квест по-прежнему можно сдать.
    assert client.post(f"{API}/quests/{instance.id}/complete", headers=headers).status_code == 200


# --- чужое ---


@pytest.mark.parametrize("resource", ["tiers", "categories", "rewards", "recurring-quests"])
def test_cannot_delete_foreign(
    client: TestClient, headers: dict[str, str], tiers: list[dict], resource: str
) -> None:
    if resource == "rewards":
        target = client.post(
            f"{API}/rewards", headers=headers, json={"name": "Кофе", "price": 5}
        ).json()
    elif resource == "recurring-quests":
        target = create_template(client, headers, tier_id=tiers[0]["id"])
    else:
        target = client.get(f"{API}/{resource}", headers=headers).json()[0]
    stranger = auth_headers(register(client, email="stranger@example.com"))

    assert client.delete(f"{API}/{resource}/{target['id']}", headers=stranger).status_code == 404
    assert client.delete(f"{API}/{resource}/999999", headers=headers).status_code == 404
