"""Ограничение частоты входов и регистраций — защита от перебора паролей.

Счётчики в Postgres, а не в памяти процесса: воркеров uvicorn может быть несколько,
и перезапуск API не обнуляет лимиты.
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Literal

from sqlalchemy import ColumnElement, delete, func, select
from sqlalchemy.orm import Session

from app.economy import utcnow
from app.models import AuthAttempt

AttemptKind = Literal["login", "register"]


@dataclass(frozen=True)
class Limit:
    kind: AttemptKind
    by: Literal["ip", "email"]
    max_attempts: int
    window: timedelta


# Неудачные входы — и по email (перебор пароля одного человека с разных адресов),
# и по IP (перебор многих email с одного адреса). Регистрации — по IP.
LOGIN_BY_EMAIL = Limit("login", "email", 5, timedelta(minutes=15))
LOGIN_BY_IP = Limit("login", "ip", 20, timedelta(minutes=15))
REGISTER_BY_IP = Limit("register", "ip", 5, timedelta(hours=1))

# Старше этого попытки не нужны ни одному лимиту — воркер их удаляет.
KEEP_ATTEMPTS = timedelta(days=1)


class TooManyAttempts(Exception):  # noqa: N818 — доменная ошибка
    def __init__(self, retry_after: timedelta) -> None:
        minutes = max(1, round(retry_after.total_seconds() / 60))
        super().__init__(f"Слишком много попыток. Попробуйте через {minutes} мин")
        self.retry_after = retry_after


def check(db: Session, limit: Limit, *, ip: str, email: str | None = None) -> None:
    """Бросает TooManyAttempts, если лимит исчерпан."""
    since = utcnow() - limit.window
    column: ColumnElement[str | None] = AuthAttempt.ip if limit.by == "ip" else AuthAttempt.email
    value = ip if limit.by == "ip" else (email or "").lower()
    count, oldest = db.execute(
        select(func.count(), func.min(AuthAttempt.created_at)).where(
            AuthAttempt.kind == limit.kind, column == value, AuthAttempt.created_at > since
        )
    ).one()
    if count >= limit.max_attempts:
        # Лимит освободится, когда самая старая попытка выпадет из окна.
        raise TooManyAttempts(oldest + limit.window - utcnow())


def record(db: Session, kind: AttemptKind, *, ip: str, email: str | None = None) -> None:
    # Время — тем же utcnow, что и в check: окно и записи считаются по одним часам.
    db.add(
        AuthAttempt(kind=kind, ip=ip, email=email.lower() if email else None, created_at=utcnow())
    )
    db.flush()


def forget_failed_logins(db: Session, email: str) -> None:
    """Вошёл — прошлые ошибки ввода пароля больше не считаются против него."""
    db.execute(
        delete(AuthAttempt).where(AuthAttempt.kind == "login", AuthAttempt.email == email.lower())
    )


def purge_old(db: Session) -> int:
    result = db.execute(
        delete(AuthAttempt)
        .where(AuthAttempt.created_at < utcnow() - KEEP_ATTEMPTS)
        .returning(AuthAttempt.id)
    )
    return len(result.all())
