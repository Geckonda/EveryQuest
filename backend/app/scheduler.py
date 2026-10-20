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
from app.jobs import apply_penalties

logger = logging.getLogger(__name__)


def run_penalties() -> None:
    with SessionLocal() as db:
        apply_penalties(db, utcnow())


def create_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=UTC)
    scheduler.add_job(
        run_penalties,
        "interval",
        seconds=settings.scheduler_interval_seconds,
        id="penalties",
        # Сразу при старте — догнать всё, что просрочилось, пока сервер был выключен.
        next_run_time=datetime.now(UTC),
        max_instances=1,
        coalesce=True,
    )
    return scheduler
