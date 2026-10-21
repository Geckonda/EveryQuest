from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app import ratelimit
from app.auth_tokens import (
    RefreshRejected,
    is_active,
    revoke_all,
    revoke_by_token,
    rotate,
    start_session,
)
from app.config import settings
from app.db import DbSession
from app.defaults import copy_defaults
from app.deps import CurrentUser
from app.economy import utcnow
from app.models import AuthSession, User
from app.ratelimit import LOGIN_BY_EMAIL, LOGIN_BY_IP, REGISTER_BY_IP, TooManyAttempts
from app.schemas import AccessToken, AuthSessionOut, LoginIn, RegisterIn
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

_EMAIL_TAKEN = "Этот email уже зарегистрирован"
_SESSION_EXPIRED = "Сессия истекла, войдите заново"

# Refresh-токен — только в httpOnly-cookie: скрипт на странице его не прочитает.
# Path — только эндпоинты входа: с остальными запросами cookie не ходит.
REFRESH_COOKIE = "eq_refresh"
REFRESH_COOKIE_PATH = "/api/v1/auth"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        max_age=settings.jwt_refresh_ttl_days * 24 * 60 * 60,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=settings.cookie_secure,
        # Strict: с чужого сайта cookie не отправится — CSRF на /refresh и /logout невозможен.
        samesite="strict",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        REFRESH_COOKIE,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
    )


def _client_ip(request: Request) -> str:
    # За прокси (Vite, Caddy) настоящий адрес приходит в X-Forwarded-For — его
    # подставляет uvicorn с --proxy-headers.
    return request.client.host if request.client else "unknown"


def _too_many(error: TooManyAttempts) -> HTTPException:
    return HTTPException(
        status.HTTP_429_TOO_MANY_REQUESTS,
        str(error),
        headers={"Retry-After": str(int(error.retry_after.total_seconds()) + 1)},
    )


def _sign_in(db: DbSession, request: Request, response: Response, user_id: int) -> AccessToken:
    session, token = start_session(db, user_id, request.headers.get("user-agent"))
    db.commit()
    _set_refresh_cookie(response, token)
    return AccessToken(access_token=create_access_token(user_id, session.id))


def _find_by_email(db: DbSession, email: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.email) == email.lower()))


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(data: RegisterIn, request: Request, response: Response, db: DbSession) -> AccessToken:
    ip = _client_ip(request)
    try:
        ratelimit.check(db, REGISTER_BY_IP, ip=ip)
    except TooManyAttempts as error:
        raise _too_many(error) from None
    # Считаем каждую попытку: и удачную, и с занятым email — иначе лимит обходится.
    ratelimit.record(db, "register", ip=ip)
    db.commit()

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
    return _sign_in(db, request, response, user.id)


@router.post("/login")
def login(data: LoginIn, request: Request, response: Response, db: DbSession) -> AccessToken:
    ip = _client_ip(request)
    try:
        ratelimit.check(db, LOGIN_BY_EMAIL, ip=ip, email=data.email)
        ratelimit.check(db, LOGIN_BY_IP, ip=ip)
    except TooManyAttempts as error:
        raise _too_many(error) from None

    user = _find_by_email(db, data.email)
    password_ok = verify_password(user.password_hash if user else None, data.password)
    if user is None or not password_ok:
        ratelimit.record(db, "login", ip=ip, email=data.email)
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный email или пароль")

    ratelimit.forget_failed_logins(db, data.email)
    return _sign_in(db, request, response, user.id)


@router.post("/refresh", responses={401: {"description": _SESSION_EXPIRED}})
def refresh(request: Request, response: Response, db: DbSession) -> AccessToken:
    token = request.cookies.get(REFRESH_COOKIE)
    try:
        if not token:
            raise RefreshRejected
        refreshed = rotate(db, token)
    except RefreshRejected:
        # Отзыв при подозрении на кражу должен сохраниться, даже если отвечаем ошибкой.
        db.commit()
        # HTTPException отбросил бы изменения response — удаляем cookie в своём ответе.
        rejected = JSONResponse({"detail": _SESSION_EXPIRED}, status.HTTP_401_UNAUTHORIZED)
        _clear_refresh_cookie(rejected)
        return rejected  # type: ignore[return-value]
    db.commit()
    if refreshed.token is not None:
        _set_refresh_cookie(response, refreshed.token)
    session = refreshed.session
    return AccessToken(access_token=create_access_token(session.user_id, session.id))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: DbSession) -> None:
    """Выйти на этом устройстве. Без cookie — тоже 204: выходить уже неоткуда."""
    token = request.cookies.get(REFRESH_COOKIE)
    if token:
        revoke_by_token(db, token)
        db.commit()
    _clear_refresh_cookie(response)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
def logout_all(user: CurrentUser, response: Response, db: DbSession) -> None:
    """Выйти на всех устройствах: все сессии отозваны, access-токены перестают работать сразу."""
    revoke_all(db, user.id)
    db.commit()
    _clear_refresh_cookie(response)


@router.get("/sessions")
def list_sessions(user: CurrentUser, request: Request, db: DbSession) -> list[AuthSessionOut]:
    """Устройства, где выполнен вход: недавно активные сверху, текущее помечено."""
    sessions = db.scalars(
        select(AuthSession)
        .where(
            AuthSession.user_id == user.id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > utcnow(),
        )
        .order_by(AuthSession.last_used_at.desc(), AuthSession.id.desc())
    )
    current = request.state.session_id
    return [
        AuthSessionOut.model_validate(s).model_copy(update={"current": s.id == current})
        for s in sessions
    ]


@router.post("/sessions/{session_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
def revoke_session(
    session_id: int, user: CurrentUser, request: Request, response: Response, db: DbSession
) -> None:
    """Выйти на конкретном устройстве — например, забытом чужом компьютере."""
    session = db.get(AuthSession, session_id)
    if session is None or session.user_id != user.id or not is_active(session):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Не найдено")
    session.revoked_at = utcnow()
    db.commit()
    if session_id == request.state.session_id:
        _clear_refresh_cookie(response)
