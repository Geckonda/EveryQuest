"""Фоновые задачи. Каждая идемпотентна: повторный запуск ничего не ломает.

Функции принимают сессию и момент времени — так их можно вызывать из тестов
без планировщика и с любым «сейчас».
"""

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.economy import lock_user, record_transaction
from app.models import Quest

logger = logging.getLogger(__name__)


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
