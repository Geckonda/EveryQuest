"""Шаблоны, которые копируются новому пользователю при регистрации."""

from sqlalchemy.orm import Session

from app.models import Category, Tier

DEFAULT_TIERS = [
    # (name, level, reward, penalty, color)
    ("I", 1, 10, 5, "#8c959f"),
    ("II", 2, 25, 10, "#2da44e"),
    ("III", 3, 50, 25, "#0969da"),
    ("IV", 4, 100, 50, "#8250df"),
    ("V", 5, 200, 100, "#cf222e"),
]

DEFAULT_CATEGORIES = [
    # (name, description, color)
    ("Здоровье", "Спорт, сон, питание, врачи", "#2da44e"),
    ("Работа", "Рабочие задачи и карьера", "#0969da"),
    ("Учёба", "Курсы, книги, новые навыки", "#8250df"),
    ("Дом", "Уборка, быт, покупки", "#bf8700"),
    ("Люди", "Семья, друзья, встречи", "#e16f24"),
    ("Хобби", "Творчество и личные проекты", "#bf3989"),
]


def copy_defaults(db: Session, user_id: int) -> None:
    db.add_all(
        Tier(
            user_id=user_id,
            name=name,
            level=level,
            default_reward=reward,
            default_penalty=penalty,
            color=color,
        )
        for name, level, reward, penalty, color in DEFAULT_TIERS
    )
    db.add_all(
        Category(user_id=user_id, name=name, description=description, color=color)
        for name, description, color in DEFAULT_CATEGORIES
    )
