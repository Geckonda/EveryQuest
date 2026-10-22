"""Потолки на число записей, которые фронт загружает целиком.

Пагинация там неудобна: выпадающему списку тиров нужны все тиры, фильтрам доски —
все открытые квесты. Поэтому ограничено создание. Потолки с большим запасом: человек
в них не упрётся, а база и телефон защищены от тысяч записей (скрипт, ошибка, баг).

Справочники считаются без архивных: их не удалить (на них ссылаются летопись и старые
квесты), и потолок вместе с архивом заблокировал бы раздел навсегда.
"""

from fastapi import HTTPException, status
from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import Session

from app.models import Category, Quest, RecurringQuest, Reward, Tier

MAX_ACTIVE_QUESTS = 500
MAX_TEMPLATES = 100
MAX_REWARDS = 200
MAX_CATEGORIES = 50
MAX_TIERS = 20
# Активных сессий входа (устройств) на пользователя; при входе сверх — выходит самая давняя.
MAX_SESSIONS = 20


def ensure_room(
    db: Session,
    model: type,
    condition: ColumnElement[bool],
    limit: int,
    message: str,
) -> None:
    """409, если записей по условию уже limit или больше."""
    count = db.scalar(select(func.count()).select_from(model).where(condition))
    if count is not None and count >= limit:
        raise HTTPException(status.HTTP_409_CONFLICT, message)


def ensure_quest_room(db: Session, user_id: int) -> None:
    ensure_room(
        db,
        Quest,
        (Quest.user_id == user_id) & (Quest.status == "active"),
        MAX_ACTIVE_QUESTS,
        f"Слишком много открытых квестов ({MAX_ACTIVE_QUESTS}) — сдайте или снимите часть",
    )


def ensure_template_room(db: Session, user_id: int) -> None:
    ensure_room(
        db,
        RecurringQuest,
        (RecurringQuest.user_id == user_id) & RecurringQuest.is_archived.is_(False),
        MAX_TEMPLATES,
        f"Слишком много повторяющихся квестов ({MAX_TEMPLATES}) — уберите ненужные в архив",
    )


def ensure_reward_room(db: Session, user_id: int) -> None:
    ensure_room(
        db,
        Reward,
        (Reward.user_id == user_id) & Reward.is_archived.is_(False),
        MAX_REWARDS,
        f"В меню таверны уже {MAX_REWARDS} позиций — уберите ненужные в архив",
    )


def ensure_category_room(db: Session, user_id: int) -> None:
    ensure_room(
        db,
        Category,
        (Category.user_id == user_id) & Category.is_archived.is_(False),
        MAX_CATEGORIES,
        f"Слишком много категорий ({MAX_CATEGORIES}) — уберите ненужные в архив",
    )


def ensure_tier_room(db: Session, user_id: int) -> None:
    ensure_room(
        db,
        Tier,
        (Tier.user_id == user_id) & Tier.is_archived.is_(False),
        MAX_TIERS,
        f"Слишком много тиров ({MAX_TIERS}) — уберите ненужные в архив",
    )
