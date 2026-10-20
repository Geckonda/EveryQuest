"""APScheduler внутри процесса FastAPI.

Ограничение: при нескольких воркерах uvicorn у каждого будет свой планировщик.
Задачи идемпотентны и блокируют строки, поэтому дублей не будет, но работа — лишняя.
Для MVP хватает одного воркера.
"""

import logging
from datetime import UTC, datetime

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.db import SessionLocal
from app.economy import utcnow
from app.jobs import apply_penalties, generate_recurring

logger = logging.getLogger(__name__)


def run_jobs() -> None:
    """Сначала штрафы за прошлые периоды, затем экземпляры за текущие.

    Одна задача, а не две: порядок важен и не зависит от того, какая успела раньше.
    """
    now = utcnow()
    with SessionLocal() as db:
        apply_penalties(db, now)
    with SessionLocal() as db:
        generate_recurring(db, now)


def create_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=UTC)
    scheduler.add_job(
        run_jobs,
        "interval",
        seconds=settings.scheduler_interval_seconds,
        id="quests",
        # Сразу при старте — догнать всё, что накопилось, пока сервер был выключен.
        next_run_time=datetime.now(UTC),
        max_instances=1,
        coalesce=True,
    )
    return scheduler
