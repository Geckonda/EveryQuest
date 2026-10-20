from fastapi import APIRouter

from app.db import DbSession
from app.deps import CurrentUser
from app.schemas import UserOut, UserUpdate

router = APIRouter(prefix="/me", tags=["me"])


@router.get("")
def get_me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.patch("")
def update_me(data: UserUpdate, user: CurrentUser, db: DbSession) -> UserOut:
    for field, value in data.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(user, field, value)
    db.commit()
    return UserOut.model_validate(user)
