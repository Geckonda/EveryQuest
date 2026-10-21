"""Процесс фоновых задач: python -m app.worker.

Отдельно от API: перезапуск или масштабирование API не трогают штрафы и генерацию,
а падение задачи не роняет API.
"""

import logging
import signal

from app.logs import configure_logging
from app.scheduler import create_scheduler

logger = logging.getLogger("app.worker")


def main() -> None:
    configure_logging()
    scheduler = create_scheduler(blocking=True)

    # docker compose stop шлёт SIGTERM — даём текущему прогону закончиться.
    def stop(signum: int, _frame: object) -> None:
        logger.info("Сигнал %s — останавливаю планировщик", signal.Signals(signum).name)
        scheduler.shutdown(wait=True)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    logger.info("Воркер запущен")
    scheduler.start()  # блокирует до shutdown


if __name__ == "__main__":
    main()
