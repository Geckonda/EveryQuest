"""Общие операции над объектами пользователя: поиск с проверкой владельца, правки, архивация."""

from typing import Any, Literal, Protocol

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Quest, RecurringQuest, User
from app.schemas import ArchiveBlocker, ArchiveConflict


class Owned(Protocol):
    id: Any
    user_id: Any


def get_owned[T: Owned](db: Session, model: type[T], obj_id: int, user: User) -> T:
    """Чужой объект неотличим от несуществующего — 404, а не 403."""
    obj = db.get(model, obj_id)
    if obj is None or obj.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Не найдено")
    return obj


def apply_changes(obj: object, changes: dict[str, Any]) -> None:
    for field, value in changes.items():
        setattr(obj, field, value)


def ensure_can_archive(db: Session, field: Literal["tier_id", "category_id"], obj_id: int) -> None:
    """Тир или категорию нельзя архивировать, пока на них ссылаются активные квесты или шаблоны.

    Шаблон на паузе тоже мешает: после снятия с паузы он создавал бы квесты в архивном объекте.
    """
    quests = db.execute(
        select(Quest.id, Quest.name)
        .where(getattr(Quest, field) == obj_id, Quest.status == "active")
        .order_by(Quest.id)
    ).all()
    templates = db.execute(
        select(RecurringQuest.id, RecurringQuest.name)
        .where(getattr(RecurringQuest, field) == obj_id, RecurringQuest.is_archived.is_(False))
        .order_by(RecurringQuest.id)
    ).all()
    if not quests and not templates:
        return

    conflict = ArchiveConflict(
        message="Сначала завершите или перенесите активные квесты и шаблоны",
        quests=[ArchiveBlocker(id=row.id, name=row.name) for row in quests],
        recurring_quests=[ArchiveBlocker(id=row.id, name=row.name) for row in templates],
    )
    raise HTTPException(status.HTTP_409_CONFLICT, detail=conflict.model_dump())
