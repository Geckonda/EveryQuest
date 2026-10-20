import threading
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app import jobs
from app.config import settings
from app.jobs import apply_penalties
from app.main import app
from app.models import Quest, Tier, Transaction, User
from app.scheduler import create_scheduler
from tests.conftest import auth_headers, register

API = "/api/v1"
NOW = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)


@pytest.fixture
def user_id(client: TestClient) -> int:
    headers = auth_headers(register(client))
    return client.get(f"{API}/me", headers=headers).json()["id"]


def add_quest(db: Session, user_id: int, **fields) -> Quest:
    tier_id = db.scalar(select(Tier.id).where(Tier.user_id == user_id).limit(1))
    defaults = {"name": "Пробежка", "reward": 10, "penalty": 5, "status": "active"}
    quest = Quest(user_id=user_id, tier_id=tier_id, **{**defaults, **fields})
    db.add(quest)
    db.commit()
    return quest


def penalty_count(db: Session, quest_id: int) -> int:
    return db.scalar(
        select(func.count())
        .select_from(Transaction)
        .where(Transaction.quest_id == quest_id, Transaction.type == "penalty")
    )


def test_overdue_quest_fails_with_penalty(db: Session, user_id: int) -> None:
    quest = add_quest(db, user_id, penalty=25, due_at=NOW - timedelta(minutes=1))

    assert apply_penalties(db, NOW) == 1

    db.refresh(quest)
    assert quest.status == "failed"
    assert quest.penalty_applied is True
    assert quest.completed_at is None
    assert db.get(User, user_id).balance == -25  # в минус можно — от штрафов
    transaction = db.scalars(select(Transaction).where(Transaction.quest_id == quest.id)).one()
    assert (transaction.type, transaction.amount, transaction.balance_after) == (
        "penalty",
        -25,
        -25,
    )


def test_penalty_is_applied_once(db: Session, user_id: int) -> None:
    """Идемпотентность: повторный запуск (например, после рестарта сервера) не штрафует снова."""
    quest = add_quest(db, user_id, due_at=NOW - timedelta(hours=1))

    assert apply_penalties(db, NOW) == 1
    assert apply_penalties(db, NOW) == 0
    assert apply_penalties(db, NOW + timedelta(days=1)) == 0

    assert penalty_count(db, quest.id) == 1
    assert db.get(User, user_id).balance == -5


def test_untouched_quests(db: Session, user_id: int) -> None:
    untouched = [
        add_quest(db, user_id, due_at=NOW + timedelta(minutes=1)),  # ещё не срок
        add_quest(db, user_id, due_at=NOW),  # ровно сейчас — ещё не просрочен
        add_quest(db, user_id, due_at=None),  # без срока
        add_quest(db, user_id, due_at=NOW - timedelta(hours=1), status="completed"),
        add_quest(db, user_id, due_at=NOW - timedelta(hours=1), status="archived"),
    ]

    assert apply_penalties(db, NOW) == 0

    for quest in untouched:
        db.refresh(quest)
        assert quest.penalty_applied is False
    assert db.get(User, user_id).balance == 0


def test_zero_penalty_fails_without_transaction(db: Session, user_id: int) -> None:
    quest = add_quest(db, user_id, penalty=0, due_at=NOW - timedelta(minutes=1))

    assert apply_penalties(db, NOW) == 1

    db.refresh(quest)
    assert quest.status == "failed"
    assert penalty_count(db, quest.id) == 0


def test_penalties_for_several_users(client: TestClient, db: Session) -> None:
    ids = []
    for email in ("a@example.com", "b@example.com"):
        headers = auth_headers(register(client, email=email))
        ids.append(client.get(f"{API}/me", headers=headers).json()["id"])
    for uid in ids:
        add_quest(db, uid, penalty=5, due_at=NOW - timedelta(hours=2))
        add_quest(db, uid, penalty=7, due_at=NOW - timedelta(hours=1))

    assert apply_penalties(db, NOW) == 4
    assert [db.get(User, uid).balance for uid in ids] == [-12, -12]


def test_failed_quest_visible_via_api(client: TestClient, db: Session) -> None:
    headers = auth_headers(register(client))
    user_id = client.get(f"{API}/me", headers=headers).json()["id"]
    quest = add_quest(db, user_id, due_at=NOW - timedelta(minutes=1))

    apply_penalties(db, NOW)

    failed = client.get(f"{API}/quests?status=failed", headers=headers).json()
    assert [q["id"] for q in failed] == [quest.id]
    assert client.post(f"{API}/quests/{quest.id}/complete", headers=headers).status_code == 409
    assert client.get(f"{API}/me", headers=headers).json()["balance"] == -5


# --- гонка «выполнить в последнюю секунду» против штрафа ---


def test_quest_completed_between_selection_and_lock(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Детерминированно воспроизводит опасный порядок: задача выбрала квест-кандидат,
    но до блокировки его успели выполнить. Штраф поверх награды списываться не должен."""
    headers = auth_headers(register(client))
    tier_id = client.get(f"{API}/tiers", headers=headers).json()[0]["id"]
    due = datetime.now(UTC) + timedelta(hours=1)
    quest = client.post(
        f"{API}/quests",
        headers=headers,
        json={
            "name": "Впритык",
            "tier_id": tier_id,
            "reward": 10,
            "penalty": 5,
            "due_at": due.isoformat(),
        },
    ).json()

    real_lock_user = jobs.lock_user

    def complete_then_lock(session: Session, user_id: int) -> User:
        response = client.post(f"{API}/quests/{quest['id']}/complete", headers=headers)
        assert response.status_code == 200
        return real_lock_user(session, user_id)

    monkeypatch.setattr(jobs, "lock_user", complete_then_lock)

    assert apply_penalties(db, due + timedelta(minutes=1)) == 0
    assert client.get(f"{API}/me", headers=headers).json()["balance"] == 10
    assert penalty_count(db, quest["id"]) == 0


@pytest.mark.usefixtures("committing_db")
@pytest.mark.parametrize("attempt", range(5))
def test_complete_vs_penalty_race(engine: Engine, attempt: int) -> None:
    """Квест ещё не просрочен для API (реальное «сейчас»), но планировщик уже считает его
    просроченным (его «сейчас» в будущем). Ровно одно из двух должно победить."""
    with TestClient(app) as client:
        headers = auth_headers(register(client, email=f"race-penalty-{attempt}@example.com"))
        tier_id = client.get(f"{API}/tiers", headers=headers).json()[0]["id"]
        due = datetime.now(UTC) + timedelta(hours=1)
        quest = client.post(
            f"{API}/quests",
            headers=headers,
            json={
                "name": "Гонка",
                "tier_id": tier_id,
                "reward": 10,
                "penalty": 5,
                "due_at": due.isoformat(),
            },
        ).json()

    barrier = threading.Barrier(2)

    def complete() -> None:
        with TestClient(app) as client:
            barrier.wait()
            client.post(f"{API}/quests/{quest['id']}/complete", headers=headers)

    def penalize() -> None:
        with Session(engine) as session:
            barrier.wait()
            apply_penalties(session, due + timedelta(minutes=1))

    threads = [threading.Thread(target=complete), threading.Thread(target=penalize)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    with Session(engine) as session:
        final = session.get(Quest, quest["id"])
        types = session.scalars(
            select(Transaction.type).where(Transaction.quest_id == quest["id"])
        ).all()
        balance = session.scalar(select(User.balance).where(User.id == final.user_id))
    outcome = (final.status, sorted(types), balance)
    assert outcome in [
        ("completed", ["quest_reward"], 10),
        ("failed", ["penalty"], -5),
    ]


# --- планировщик ---


def test_scheduler_disabled_in_tests() -> None:
    assert settings.scheduler_enabled is False


def test_scheduler_has_quests_job() -> None:
    scheduler = create_scheduler()
    job = scheduler.get_job("quests")
    assert job is not None
    assert job.trigger.interval == timedelta(seconds=settings.scheduler_interval_seconds)
