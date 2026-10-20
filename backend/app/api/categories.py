from fastapi import APIRouter
from sqlalchemy import select

from app.db import DbSession
from app.deps import CurrentUser
from app.models import Category
from app.schemas import CategoryOut

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("")
def list_categories(
    user: CurrentUser, db: DbSession, include_archived: bool = False
) -> list[CategoryOut]:
    query = select(Category).where(Category.user_id == user.id).order_by(Category.id)
    if not include_archived:
        query = query.where(Category.is_archived.is_(False))
    return [CategoryOut.model_validate(category) for category in db.scalars(query)]
