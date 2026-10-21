from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth_tokens import is_active
from app.db import DbSession
from app.models import AuthSession, User
from app.security import decode_access_token

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    claims = decode_access_token(credentials.credentials) if credentials else None
    user = None
    if claims is not None:
        user_id, session_id = claims
        # Сессию проверяем на каждом запросе: «выйти на всех устройствах» действует сразу,
        # а не через 15 минут, когда истечёт access-токен.
        session = db.get(AuthSession, session_id)
        if is_active(session) and session is not None and session.user_id == user_id:
            user = db.get(User, user_id)
            # Список устройств помечает текущее — эндпоинтам нужен id сессии запроса.
            request.state.session_id = session_id
    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Требуется вход",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
