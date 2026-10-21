import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.config import settings

_ALGORITHM = "HS256"
_hasher = PasswordHasher()
# Хэш для сравнения, когда пользователя нет: время ответа не выдаёт, есть ли email в базе.
_DUMMY_HASH = _hasher.hash("dummy-password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def _verify(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def verify_password(password_hash: str | None, password: str) -> bool:
    """password_hash=None — пользователь не найден; хэш всё равно считается ради времени ответа."""
    if password_hash is None:
        _verify(_DUMMY_HASH, password)
        return False
    return _verify(password_hash, password)


def create_access_token(user_id: int, session_id: int) -> str:
    """Короткоживущий JWT; sid — сессия, по которой его выдали (её можно отозвать)."""
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "sid": session_id,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_ttl_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> tuple[int, int] | None:
    """(id пользователя, id сессии) или None, если токен невалиден или истёк."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
    except jwt.PyJWTError:
        return None
    if payload.get("type") != "access":
        return None
    try:
        return int(payload["sub"]), int(payload["sid"])
    except (KeyError, TypeError, ValueError):
        return None


def new_refresh_token() -> str:
    """Refresh-токен — случайная строка, а не JWT: проверяется по базе, отзывается удалением."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """В базе — только SHA-256: утечка дампа не даёт войти. Соль не нужна, токен случайный."""
    return hashlib.sha256(token.encode()).hexdigest()
