from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.defaults import DEFAULT_TIERS
from app.economy import default_penalty
from app.jobs import apply_penalties
from app.models import Quest, Transaction
from tests.conftest import auth_headers, register

API = "/api/v1"
TIER_I_REWARD = DEFAULT_TIERS[0][2]


def future(hours: int = 24) -> str:
    return (datetime.now(UTC) + timedelta(hours=hours)).isoformat()


@pytest.fixture
def headers(client: TestClient) -> dict[str, str]:
    return auth_headers(register(client))


@pytest.fixture
def tiers(client: TestClient, headers: dict[str, str]) -> list[dict]:
    return client.get(f"{API}/tiers", headers=headers).json()


@pytest.fixture
def category_id(client: TestClient, headers: dict[str, str]) -> int:
    return client.get(f"{API}/categories", headers=headers).json()[0]["id"]


def create_quest(client: TestClient, headers: dict[str, str], **body) -> dict:
    response = client.post(f"{API}/quests", headers=headers, json={"name": "Пробежка", **body})
    assert response.status_code == 201, response.text
    return response.json()


def balance(client: TestClient, headers: dict[str, str]) -> int:
    return client.get(f"{API}/me", headers=headers).json()["balance"]


# --- создание ---


def test_create_copies_reward_from_tier(
    client: TestClient, headers: dict[str, str], tiers: list[dict], category_id: int
) -> None:
    quest = create_quest(
        client, headers, tier_id=tiers[0]["id"], category_id=category_id, due_at=future()
    )
    assert quest["status"] == "active"
    # Множитель штрафа по умолчанию 1 — штраф равен награде.
    assert (quest["reward"], quest["penalty"]) == (TIER_I_REWARD, TIER_I_REWARD)
    assert quest["category_id"] == category_id


@pytest.mark.parametrize(
    ("reward", "multiplier", "penalty"),
    [
        (10, "1", 10),
        (10, "2", 20),
        (25, "1.5", 38),  # 37.5 — половина вверх
        (10, "0", 0),
        (1, "0.25", 0),
        (2, "0.25", 1),  # 0.5 — половина вверх
        (1_000_000, "10", 1_000_000),  # не больше предела суммы
    ],
)
def test_default_penalty(reward: int, multiplier: str, penalty: int) -> None:
    assert default_penalty(reward, Decimal(multiplier)) == penalty


def test_create_uses_penalty_multiplier(
    client: TestClient, headers: dict[str, str], tiers: list[dict]
) -> None:
    client.patch(f"{API}/me", headers=headers, json={"penalty_multiplier": 2})

    from_tier = create_quest(client, headers, tier_id=tiers[0]["id"])
    assert from_tier["penalty"] == TIER_I_REWARD * 2

    own_reward = create_quest(client, headers, tier_id=tiers[0]["id"], reward=7)
    assert own_reward["penalty"] == 14

    explicit = create_quest(client, headers, tier_id=tiers[0]["id"], reward=7, penalty=3)
    assert explicit["penalty"] == 3


def test_create_with_explicit_reward(
    client: TestClient, headers: dict[str, str], tiers: list[dict]
) -> None:
    quest = create_quest(client, headers, tier_id=tiers[0]["id"], reward=77, penalty=0)
    assert (quest["reward"], quest["penalty"]) == (77, 0)
    assert quest["due_at"] is None


def test_tier_change_does_not_touch_existing_quests(
    client: TestClient, headers: dict[str, str], tiers: list[dict]
) -> None:
    quest = create_quest(client, headers, tier_id=tiers[0]["id"])
    client.patch(f"{API}/tiers/{tiers[0]['id']}", headers=headers, json={"default_reward": 999})
    same = client.get(f"{API}/quests", headers=headers).json()[0]
    assert same["id"] == quest["id"]
    assert same["reward"] == TIER_I_REWARD


@pytest.mark.parametrize(
    ("body", "reason"),
    [
        ({"due_at": "2020-01-01T00:00:00Z"}, "срок в прошлом"),
        ({"due_at": "2030-01-01T00:00:00"}, "без часового пояса"),
        ({"reward": -1}, "отрицательная награда"),
        ({"name": ""}, "пустое имя"),
    ],
)
def test_create_validation(
    client: TestClient, headers: dict[str, str], tiers: list[dict], body: dict, reason: str
) -> None:
    payload = {"name": "Q", "tier_id": tiers[0]["id"], **body}
    response = client.post(f"{API}/quests", headers=headers, json=payload)
    assert response.status_code == 422, reason


def test_create_with_archived_or_foreign_refs(
    client: TestClient, headers: dict[str, str], tiers: list[dict], category_id: int
) -> None:
    client.patch(f"{API}/tiers/{tiers[4]['id']}", headers=headers, json={"is_archived": True})
    archived = client.post(
        f"{API}/quests", headers=headers, json={"name": "Q", "tier_id": tiers[4]["id"]}
    )
    assert archived.status_code == 422

    stranger = auth_headers(register(client, email="stranger@example.com"))
    foreign_tier = client.post(
        f"{API}/quests", headers=stranger, json={"name": "Q", "tier_id": tiers[0]["id"]}
    )
    assert foreign_tier.status_code == 422

    own_tier = client.get(f"{API}/tiers", headers=stranger).json()[0]["id"]
    foreign_category = client.post(
        f"{API}/quests",
        headers=stranger,
        json={"name": "Q", "tier_id": own_tier, "category_id": category_id},
    )
    assert foreign_category.status_code == 422


# --- список ---


def test_list_filters_and_order(
    client: TestClient, headers: dict[str, str], tiers: list[dict], category_id: int
) -> None:
    later = create_quest(client, headers, name="Позже", tier_id=tiers[0]["id"], due_at=future(48))
    no_due = create_quest(client, headers, name="Без срока", tier_id=tiers[1]["id"])
    sooner = create_quest(
        client,
        headers,
        name="Скоро",
        tier_id=tiers[0]["id"],
        category_id=category_id,
        due_at=future(1),
    )
    client.post(f"{API}/quests/{later['id']}/complete", headers=headers)

    active = client.get(f"{API}/quests?status=active", headers=headers).json()
    assert [q["id"] for q in active] == [sooner["id"], no_due["id"]]

    completed = client.get(f"{API}/quests?status=completed", headers=headers).json()
    assert [q["id"] for q in completed] == [later["id"]]

    by_category = client.get(f"{API}/quests?category_id={category_id}", headers=headers).json()
    assert [q["id"] for q in by_category] == [sooner["id"]]

    by_tier = client.get(f"{API}/quests?tier_id={tiers[1]['id']}", headers=headers).json()
    assert [q["id"] for q in by_tier] == [no_due["id"]]

    assert client.get(f"{API}/quests?status=nope", headers=headers).status_code == 422


def test_list_archive_pages(
    client: TestClient, db: Session, headers: dict[str, str], tiers: list[dict]
) -> None:
    """Архив: несколько статусов сразу, свежезакрытые сверху, постранично."""
    done = create_quest(client, headers, name="Сдан", tier_id=tiers[0]["id"])
    failed = create_quest(client, headers, name="Провален", tier_id=tiers[0]["id"])
    removed = create_quest(client, headers, name="Снят", tier_id=tiers[0]["id"])
    create_quest(client, headers, name="Висит", tier_id=tiers[0]["id"])
    client.post(f"{API}/quests/{done['id']}/complete", headers=headers)
    client.post(f"{API}/quests/{failed['id']}/fail", headers=headers)
    client.patch(f"{API}/quests/{removed['id']}", headers=headers, json={"status": "archived"})
    # Сданный закрыт позже всех — должен быть первым, хотя создан раньше.
    db.get(Quest, done["id"]).closed_at = datetime.now(UTC) + timedelta(minutes=1)
    db.flush()

    url = f"{API}/quests?status=completed&status=failed&status=archived"
    first = client.get(f"{url}&limit=2", headers=headers).json()
    second = client.get(f"{url}&limit=2&offset=2", headers=headers).json()
    assert [q["id"] for q in first] == [done["id"], removed["id"]]
    assert [q["id"] for q in second] == [failed["id"]]


def test_active_list_is_not_capped(
    client: TestClient, db: Session, headers: dict[str, str], tiers: list[dict]
) -> None:
    db.add_all(
        Quest(
            user_id=client.get(f"{API}/me", headers=headers).json()["id"],
            tier_id=tiers[0]["id"],
            name=f"Квест {i}",
            reward=1,
            penalty=1,
        )
        for i in range(120)
    )
    db.flush()

    assert len(client.get(f"{API}/quests?status=active", headers=headers).json()) == 120
    assert len(client.get(f"{API}/quests", headers=headers).json()) == 100


# --- изменение ---


def test_update_quest(client: TestClient, headers: dict[str, str], tiers: list[dict]) -> None:
    quest = create_quest(client, headers, tier_id=tiers[0]["id"], due_at=future())

    renamed = client.patch(
        f"{API}/quests/{quest['id']}", headers=headers, json={"name": "Заплыв", "due_at": None}
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Заплыв"
    assert renamed.json()["due_at"] is None

    retiered = client.patch(
        f"{API}/quests/{quest['id']}", headers=headers, json={"tier_id": tiers[2]["id"]}
    )
    assert retiered.json()["reward"] == DEFAULT_TIERS[2][2]

    explicit = client.patch(
        f"{API}/quests/{quest['id']}",
        headers=headers,
        json={"tier_id": tiers[3]["id"], "reward": 1},
    )
    assert explicit.json()["reward"] == 1
    assert explicit.json()["penalty"] == 1  # от заданной награды, а не от награды тира


def test_archive_quest(client: TestClient, headers: dict[str, str], tiers: list[dict]) -> None:
    quest = create_quest(client, headers, tier_id=tiers[0]["id"])

    archived = client.patch(
        f"{API}/quests/{quest['id']}", headers=headers, json={"status": "archived"}
    )
    assert archived.json()["status"] == "archived"
    assert archived.json()["close_reason"] == "archived"
    assert archived.json()["closed_at"] is not None

    for body in ({"status": "active"}, {"status": "completed"}):
        response = client.patch(f"{API}/quests/{quest['id']}", headers=headers, json=body)
        assert response.status_code in (409, 422)
    for action in ("complete", "fail"):
        response = client.post(f"{API}/quests/{quest['id']}/{action}", headers=headers)
        assert response.status_code == 409
    assert balance(client, headers) == 0


def test_cannot_touch_other_users_quest(
    client: TestClient, headers: dict[str, str], tiers: list[dict]
) -> None:
    quest = create_quest(client, headers, tier_id=tiers[0]["id"])
    stranger = auth_headers(register(client, email="stranger@example.com"))

    patch = client.patch(f"{API}/quests/{quest['id']}", headers=stranger, json={"name": "Моё"})
    assert patch.status_code == 404
    for action in ("complete", "fail"):
        response = client.post(f"{API}/quests/{quest['id']}/{action}", headers=stranger)
        assert response.status_code == 404
    assert client.get(f"{API}/quests", headers=stranger).json() == []
    assert balance(client, stranger) == 0


# --- выполнение ---


def test_complete_credits_reward_once(
    client: TestClient, db: Session, headers: dict[str, str], tiers: list[dict]
) -> None:
    quest = create_quest(client, headers, tier_id=tiers[2]["id"], due_at=future())

    response = client.post(f"{API}/quests/{quest['id']}/complete", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["quest"]["status"] == "completed"
    assert body["quest"]["close_reason"] == "completed"
    assert body["quest"]["closed_at"] is not None
    assert body["balance"] == quest["reward"]
    assert balance(client, headers) == quest["reward"]

    again = client.post(f"{API}/quests/{quest['id']}/complete", headers=headers)
    assert again.status_code == 409
    assert balance(client, headers) == quest["reward"]

    transactions = db.scalars(select(Transaction).where(Transaction.quest_id == quest["id"])).all()
    assert [(t.type, t.amount, t.balance_after) for t in transactions] == [
        ("quest_reward", quest["reward"], quest["reward"])
    ]


def test_balance_accumulates(
    client: TestClient, headers: dict[str, str], tiers: list[dict]
) -> None:
    rewards = []
    for tier in tiers[:3]:
        quest = create_quest(client, headers, tier_id=tier["id"])
        client.post(f"{API}/quests/{quest['id']}/complete", headers=headers)
        rewards.append(quest["reward"])
    assert balance(client, headers) == sum(rewards)


def test_cannot_complete_or_edit_overdue_quest(
    client: TestClient, db: Session, headers: dict[str, str], tiers: list[dict]
) -> None:
    quest = create_quest(client, headers, tier_id=tiers[0]["id"], due_at=future())
    # Срок истёк, а планировщик штрафов ещё не успел обработать квест.
    db.get(Quest, quest["id"]).due_at = datetime.now(UTC) - timedelta(minutes=1)
    db.flush()

    complete = client.post(f"{API}/quests/{quest['id']}/complete", headers=headers)
    assert complete.status_code == 409
    assert complete.json()["detail"] == "Срок квеста истёк"

    extend = client.patch(f"{API}/quests/{quest['id']}", headers=headers, json={"due_at": future()})
    assert extend.status_code == 409
    # Провалить вручную тоже нельзя: штраф спишет планировщик, иначе он списался бы дважды.
    fail = client.post(f"{API}/quests/{quest['id']}/fail", headers=headers)
    assert fail.status_code == 409
    assert balance(client, headers) == 0


# --- провал вручную ---


def test_fail_charges_full_penalty_once(
    client: TestClient, db: Session, headers: dict[str, str], tiers: list[dict]
) -> None:
    quest = create_quest(client, headers, tier_id=tiers[1]["id"], penalty=30, due_at=future())

    response = client.post(f"{API}/quests/{quest['id']}/fail", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert (body["quest"]["status"], body["quest"]["close_reason"]) == ("failed", "abandoned")
    assert body["quest"]["penalty_applied"] is True
    assert body["quest"]["closed_at"] is not None
    assert body["balance"] == -30  # в минус можно — это штраф

    for action in ("fail", "complete"):
        again = client.post(f"{API}/quests/{quest['id']}/{action}", headers=headers)
        assert again.status_code == 409
    assert balance(client, headers) == -30

    transactions = db.scalars(select(Transaction).where(Transaction.quest_id == quest["id"])).all()
    assert [(t.type, t.amount) for t in transactions] == [("penalty", -30)]


def test_fail_without_due_date_and_zero_penalty(
    client: TestClient, db: Session, headers: dict[str, str], tiers: list[dict]
) -> None:
    quest = create_quest(client, headers, tier_id=tiers[0]["id"], penalty=0)

    response = client.post(f"{API}/quests/{quest['id']}/fail", headers=headers)
    assert response.status_code == 200
    assert response.json()["balance"] == 0
    assert db.scalars(select(Transaction).where(Transaction.quest_id == quest["id"])).all() == []


def test_failed_quest_is_not_penalized_again(
    client: TestClient, db: Session, headers: dict[str, str], tiers: list[dict]
) -> None:
    quest = create_quest(client, headers, tier_id=tiers[0]["id"], penalty=5, due_at=future(1))
    client.post(f"{API}/quests/{quest['id']}/fail", headers=headers)

    assert apply_penalties(db, datetime.now(UTC) + timedelta(hours=2)) == 0
    assert balance(client, headers) == -5


def test_archiving_tier_blocked_by_quest_created_via_api(
    client: TestClient, headers: dict[str, str], tiers: list[dict]
) -> None:
    quest = create_quest(client, headers, tier_id=tiers[0]["id"])
    blocked = client.patch(
        f"{API}/tiers/{tiers[0]['id']}", headers=headers, json={"is_archived": True}
    )
    assert blocked.status_code == 409

    client.post(f"{API}/quests/{quest['id']}/complete", headers=headers)
    allowed = client.patch(
        f"{API}/tiers/{tiers[0]['id']}", headers=headers, json={"is_archived": True}
    )
    assert allowed.status_code == 200
