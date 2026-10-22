"""Сессии входа и ротация refresh-токенов.

Функции не делают commit — это решает вызывающий код.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import settings
from app.economy import utcnow
from app.limits import MAX_SESSIONS
from app.models import AuthSession
from app.security import hash_token, new_refresh_token

# Две вкладки обновили токен одновременно: вторая пришла со старым. В этом окне
# это гонка, а не кража — выдаём access-токен, cookie у браузера уже новая.
ROTATION_GRACE = timedelta(seconds=30)


class RefreshRejected(Exception):  # noqa: N818 — доменная ошибка
    """Токен неизвестен, истёк или отозван — нужно войти заново."""


@dataclass
class Refreshed:
    session: AuthSession
    # None — гонка вкладок: новый токен уже у браузера, cookie не трогаем.
    token: str | None


def _evict_oldest(db: Session, user_id: int, now: datetime) -> None:
    """Освобождает место под новую сессию: сверх MAX_SESSIONS выходят самые давние.

    Иначе каждый вход (скрипт, частые входы) копил бы сессии на 30 дней — сотнями.
    """
    alive = db.scalars(
        select(AuthSession)
        .where(
            AuthSession.user_id == user_id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now,
        )
        .order_by(AuthSession.last_used_at.desc(), AuthSession.id.desc())
        .offset(MAX_SESSIONS - 1)
    ).all()
    for session in alive:
        session.revoked_at = now


def start_session(db: Session, user_id: int, user_agent: str | None) -> tuple[AuthSession, str]:
    token = new_refresh_token()
    now = utcnow()
    _evict_oldest(db, user_id, now)
    session = AuthSession(
        user_id=user_id,
        token_hash=hash_token(token),
        user_agent=(user_agent or "")[:300] or None,
        last_used_at=now,
        expires_at=now + timedelta(days=settings.jwt_refresh_ttl_days),
    )
    db.add(session)
    db.flush()
    return session, token


def rotate(db: Session, token: str) -> Refreshed:
    """Меняет refresh-токен сессии. Старый токен вне окна гонки — признак кражи: отзыв."""
    now = utcnow()
    hashed = hash_token(token)
    # Блокировка строки: две вкладки не провернут ротацию одновременно.
    session = db.scalar(
        select(AuthSession).where(AuthSession.token_hash == hashed).with_for_update()
    )
    if session is None:
        reused = db.scalar(
            select(AuthSession).where(AuthSession.previous_token_hash == hashed).with_for_update()
        )
        if reused is None or reused.revoked_at is not None or reused.expires_at <= now:
            raise RefreshRejected
        if reused.rotated_at is not None and now - reused.rotated_at <= ROTATION_GRACE:
            reused.last_used_at = now
            return Refreshed(reused, None)
        # Старым токеном воспользовались позже — его кто-то сохранил. Отзываем сессию.
        reused.revoked_at = now
        db.flush()
        raise RefreshRejected

    if session.revoked_at is not None or session.expires_at <= now:
        raise RefreshRejected

    new_token = new_refresh_token()
    session.previous_token_hash = session.token_hash
    session.token_hash = hash_token(new_token)
    session.rotated_at = now
    session.last_used_at = now
    # Скользящее окно: пока пользуются — не разлогинивает.
    session.expires_at = now + timedelta(days=settings.jwt_refresh_ttl_days)
    db.flush()
    return Refreshed(session, new_token)


def revoke_by_token(db: Session, token: str) -> None:
    hashed = hash_token(token)
    db.execute(
        update(AuthSession)
        .where(AuthSession.token_hash == hashed, AuthSession.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )


def revoke_all(db: Session, user_id: int) -> int:
    """Выйти на всех устройствах. Возвращает число отозванных сессий."""
    result = db.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=utcnow())
        .returning(AuthSession.id)
    )
    return len(result.all())


def is_active(session: AuthSession | None) -> bool:
    return session is not None and session.revoked_at is None and session.expires_at > utcnow()
