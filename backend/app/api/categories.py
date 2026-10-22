from fastapi import APIRouter, status
from sqlalchemy import select

from app.crud import apply_changes, ensure_can_archive, get_owned
from app.db import DbSession
from app.deletion import delete_category
from app.deps import CurrentUser
from app.limits import ensure_category_room
from app.models import Category
from app.schemas import ArchiveConflict, CategoryCreate, CategoryOut, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("")
def list_categories(
    user: CurrentUser, db: DbSession, include_archived: bool = False
) -> list[CategoryOut]:
    query = select(Category).where(Category.user_id == user.id).order_by(Category.id)
    if not include_archived:
        query = query.where(Category.is_archived.is_(False))
    return [CategoryOut.model_validate(category) for category in db.scalars(query)]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_category(data: CategoryCreate, user: CurrentUser, db: DbSession) -> CategoryOut:
    ensure_category_room(db, user.id)
    category = Category(user_id=user.id, **data.model_dump())
    db.add(category)
    db.commit()
    return CategoryOut.model_validate(category)


@router.patch("/{category_id}", responses={409: {"model": ArchiveConflict}})
def update_category(
    category_id: int, data: CategoryUpdate, user: CurrentUser, db: DbSession
) -> CategoryOut:
    category = get_owned(db, Category, category_id, user)
    changes = data.changes()
    if changes.get("is_archived") and not category.is_archived:
        ensure_can_archive(db, "category_id", category.id)
    if changes.get("is_archived") is False and category.is_archived:
        ensure_category_room(db, user.id)
    apply_changes(category, changes)
    db.commit()
    return CategoryOut.model_validate(category)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_category(category_id: int, user: CurrentUser, db: DbSession) -> None:
    """Удалить насовсем: квесты и шаблоны этой категории станут «без категории»."""
    delete_category(db, get_owned(db, Category, category_id, user))
    db.commit()
