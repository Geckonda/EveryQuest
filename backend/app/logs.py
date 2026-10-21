import logging


def configure_logging() -> None:
    """Общий формат логов для API и воркера."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
    # APScheduler пишет о каждом запуске задачи; свои итоги задачи логируют сами.
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
