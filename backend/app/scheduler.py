"""Планировщик фоновых задач: штрафы и генерация повторяющихся квестов.

Живёт в отдельном процессе (app/worker.py, сервис worker в docker-compose), а не в API:
воркеров uvicorn может быть несколько, а задачи должны идти по одному разу.
Каждый прогон берёт advisory lock Postgres — даже если запущены два воркера
(или включён планировщик в API), прогон второго просто пропускается.
"""

import logging
from datetime import UTC, datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.base import BaseScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from app.config import settings
from app.db import engine as default_engine
from app.economy import utcnow
from app.jobs import apply_penalties, generate_recurring, purge_auth

logger = logging.getLogger(__name__)

# Ключ advisory lock задач — произвольное число, общее для всех процессов приложения.
JOBS_LOCK_KEY = 0x45515553  # «EQUS»


def run_jobs(bind: Engine | None = None) -> bool:
    """Сначала штрафы за прошлые периоды, затем экземпляры за текущие. False — пропущено.

    Одна задача, а не две: порядок важен и не зависит от того, какая успела раньше.
    Блокировка держится на отдельном соединении всё время прогона; задачи работают
    своими сессиями — advisory lock уровня сессии этому не мешает.
    """
    bind = bind or default_engine
    with bind.connect() as lock:
        if not lock.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": JOBS_LOCK_KEY}):
            logger.info("Задачи уже выполняет другой процесс — пропускаю")
            return False
        try:
            now = utcnow()
            with Session(bind, expire_on_commit=False) as db:
                apply_penalties(db, now)
            with Session(bind, expire_on_commit=False) as db:
                generate_recurring(db, now)
            with Session(bind, expire_on_commit=False) as db:
                purge_auth(db, now)
        finally:
            lock.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": JOBS_LOCK_KEY})
            lock.commit()
    return True


def create_scheduler(*, blocking: bool = False) -> BaseScheduler:
    """blocking — для отдельного процесса-воркера; иначе фоновый поток внутри API."""
    scheduler: BaseScheduler = (
        BlockingScheduler(timezone=UTC) if blocking else BackgroundScheduler(timezone=UTC)
    )
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
