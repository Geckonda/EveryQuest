from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.config import settings

TokenType = Literal["access", "refresh"]

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


def create_token(user_id: int, token_type: TokenType) -> str:
    now = datetime.now(UTC)
    ttl = (
        timedelta(minutes=settings.jwt_access_ttl_minutes)
        if token_type == "access"
        else timedelta(days=settings.jwt_refresh_ttl_days)
    )
    payload = {"sub": str(user_id), "type": token_type, "iat": now, "exp": now + ttl}
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def decode_token(token: str, expected_type: TokenType) -> int | None:
    """Возвращает id пользователя или None, если токен невалиден, истёк или другого типа."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
    except jwt.PyJWTError:
        return None
    if payload.get("type") != expected_type:
        return None
    try:
        return int(payload["sub"])
    except (KeyError, ValueError):
        return None
