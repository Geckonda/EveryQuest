from fastapi import APIRouter

from app.crud import apply_changes
from app.db import DbSession
from app.deps import CurrentUser
from app.schemas import UserOut, UserUpdate

router = APIRouter(prefix="/me", tags=["me"])


@router.get("")
def get_me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.patch("")
def update_me(data: UserUpdate, user: CurrentUser, db: DbSession) -> UserOut:
    apply_changes(user, data.changes())
    db.commit()
    return UserOut.model_validate(user)
