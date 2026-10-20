"""Фоновые задачи. Каждая идемпотентна: повторный запуск ничего не ломает.

Функции принимают сессию и момент времени — так их можно вызывать из тестов
без планировщика и с любым «сейчас».
"""

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.economy import lock_user, record_transaction
from app.models import Quest, RecurringQuest, User
from app.recurrence import due_at_for, local_today, period_for

logger = logging.getLogger(__name__)


def generate_instance(db: Session, template: RecurringQuest, timezone: str, now: datetime) -> bool:
    """Создаёт экземпляр шаблона за текущий период, если его ещё нет. True — создан.

    Задним числом не создаём: если срок периода уже прошёл (шаблон создан после due_time,
    сервер был выключен), экземпляр сразу провалился бы со штрафом за квест,
    которого пользователь не видел.
    """
    period = period_for(template, local_today(timezone, now))
    if period is None:
        return False
    due_at = due_at_for(template, period, timezone)
    if due_at <= now:
        return False

    # Дубликаты отсекает UNIQUE (recurring_quest_id, period_date) — в том числе,
    # если экземпляр уже выполнен: за этот период второй не появится.
    # rowcount здесь ненадёжен (psycopg 3 отдаёт -1) — узнаём о вставке через RETURNING.
    created_id = db.scalar(
        insert(Quest)
        .values(
            user_id=template.user_id,
            tier_id=template.tier_id,
            category_id=template.category_id,
            recurring_quest_id=template.id,
            period_date=period.period_date,
            name=template.name,
            description=template.description,
            reward=template.reward,
            penalty=template.penalty,
            due_at=due_at,
            status="active",
        )
        .on_conflict_do_nothing(index_elements=["recurring_quest_id", "period_date"])
        .returning(Quest.id)
    )
    return created_id is not None


def generate_recurring(db: Session, now: datetime) -> int:
    """Создаёт экземпляры всех активных шаблонов за текущий период по времени их владельцев."""
    rows = db.execute(
        select(RecurringQuest, User.timezone)
        .join(User, User.id == RecurringQuest.user_id)
        .where(RecurringQuest.is_active.is_(True), RecurringQuest.is_archived.is_(False))
        .order_by(RecurringQuest.id)
    ).all()
    created = sum(generate_instance(db, template, tz, now) for template, tz in rows)
    db.commit()
    if created:
        logger.info("Повторяющиеся: создано экземпляров — %d", created)
    return created


def apply_penalties(db: Session, now: datetime) -> int:
    """Проваливает просроченные активные квесты и списывает штраф. Возвращает их число.

    Каждый квест — отдельная транзакция БД. Блокировки в том же порядке, что и при
    выполнении квеста (пользователь → квест), поэтому гонка «выполнить в последнюю
    секунду» против штрафа безопасна: кто первым взял блокировку, тот и решил судьбу квеста.
    """
    candidates = db.execute(
        select(Quest.id, Quest.user_id)
        .where(
            Quest.status == "active",
            Quest.due_at < now,
            Quest.penalty_applied.is_(False),
        )
        .order_by(Quest.user_id, Quest.id)
    ).all()

    penalized = 0
    for quest_id, user_id in candidates:
        user = lock_user(db, user_id)
        quest = db.execute(
            select(Quest)
            .where(Quest.id == quest_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).scalar_one()
        # Пока ждали блокировку, квест могли выполнить или убрать.
        if quest.status != "active" or quest.penalty_applied or quest.due_at is None:
            db.commit()  # ничего не меняли — просто отпускаем блокировки
            continue

        quest.status = "failed"
        quest.penalty_applied = True
        if quest.penalty:
            record_transaction(db, user, -quest.penalty, "penalty", quest_id=quest.id)
        db.commit()
        penalized += 1

    if penalized:
        logger.info("Штрафы: провалено квестов — %d", penalized)
    return penalized
