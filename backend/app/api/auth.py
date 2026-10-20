from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.db import DbSession
from app.defaults import copy_defaults
from app.models import User
from app.schemas import AccessToken, LoginIn, RefreshIn, RegisterIn, TokenPair
from app.security import create_token, decode_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

_EMAIL_TAKEN = "Этот email уже зарегистрирован"


def _token_pair(user_id: int) -> TokenPair:
    return TokenPair(
        access_token=create_token(user_id, "access"),
        refresh_token=create_token(user_id, "refresh"),
    )


def _find_by_email(db: DbSession, email: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.email) == email.lower()))


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(data: RegisterIn, db: DbSession) -> TokenPair:
    if _find_by_email(db, data.email):
        raise HTTPException(status.HTTP_409_CONFLICT, _EMAIL_TAKEN)

    user = User(
        email=data.email.lower(),
        username=data.username,
        password_hash=hash_password(data.password),
        timezone=data.timezone,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        # Параллельная регистрация с тем же email проскочила проверку выше.
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, _EMAIL_TAKEN) from None
    copy_defaults(db, user.id)
    db.commit()
    return _token_pair(user.id)


@router.post("/login")
def login(data: LoginIn, db: DbSession) -> TokenPair:
    user = _find_by_email(db, data.email)
    password_ok = verify_password(user.password_hash if user else None, data.password)
    if user is None or not password_ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный email или пароль")
    return _token_pair(user.id)


@router.post("/refresh")
def refresh(data: RefreshIn, db: DbSession) -> AccessToken:
    user_id = decode_token(data.refresh_token, "refresh")
    if user_id is None or db.get(User, user_id) is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Сессия истекла, войдите заново")
    return AccessToken(access_token=create_token(user_id, "access"))
