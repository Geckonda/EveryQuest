"""Удаление справочников и шаблонов — без потери истории.

Архив остаётся для того, что ещё пригодится, но создать по ошибке тир или позицию меню
и не иметь возможности их убрать — неудобно. Поэтому удалить можно всё; ссылки
обрабатываются так, чтобы старые квесты и летопись остались целы:

- категория — просто ярлык: квесты и шаблоны становятся «без категории»;
- тир — обязательное поле квеста: если тир используется, квесты и шаблоны переносятся
  в другой тир (награды и штрафы скопированы в квест при создании и не меняются);
- позиция меню — название сохраняется в записях летописи, сеансы трат хранят своё;
- шаблон — созданные по нему квесты остаются обычными.

Функции не делают commit — это решает вызывающий код.
"""

from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models import Category, Quest, RecurringQuest, Reward, RewardSession, Tier, Transaction


@dataclass
class TierUsage:
    quests: int
    templates: int

    @property
    def used(self) -> bool:
        return bool(self.quests or self.templates)


def tier_usage(db: Session, tier_id: int) -> TierUsage:
    """Все квесты (и закрытые — у них тоже печать тира) и все шаблоны (и архивные)."""

    def count(model: type[Quest] | type[RecurringQuest]) -> int:
        return (
            db.scalar(select(func.count()).select_from(model).where(model.tier_id == tier_id)) or 0
        )

    return TierUsage(quests=count(Quest), templates=count(RecurringQuest))


def delete_tier(db: Session, tier: Tier, move_to: Tier | None) -> None:
    """move_to — куда перенести квесты и шаблоны; обязателен, если тир используется."""
    if not tier.is_archived:
        active = db.scalar(
            select(func.count())
            .select_from(Tier)
            .where(Tier.user_id == tier.user_id, Tier.is_archived.is_(False))
        )
        if active == 1:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Это последний тир — без него квесты будет не в чем создавать",
            )

    usage = tier_usage(db, tier.id)
    if usage.used:
        if move_to is None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail={
                    "message": "Тир используется — выберите, куда перенести его квесты",
                    "quests": usage.quests,
                    "recurring_quests": usage.templates,
                },
            )
        if move_to.id == tier.id or move_to.user_id != tier.user_id or move_to.is_archived:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Перенести можно только в другой действующий тир",
            )
        for model in (Quest, RecurringQuest):
            db.execute(update(model).where(model.tier_id == tier.id).values(tier_id=move_to.id))
    db.delete(tier)
    db.flush()


def delete_category(db: Session, category: Category) -> None:
    for model in (Quest, RecurringQuest):
        db.execute(update(model).where(model.category_id == category.id).values(category_id=None))
    db.delete(category)
    db.flush()


def delete_reward(db: Session, reward: Reward) -> None:
    # Летопись показывает название заказа — сохраняем его в самих записях.
    db.execute(
        update(Transaction)
        .where(Transaction.reward_id == reward.id)
        .values(title_snapshot=reward.name, reward_id=None)
    )
    # Сеанс траты хранит своё название (снимок при заказе) — ссылка больше не нужна.
    db.execute(
        update(RewardSession).where(RewardSession.reward_id == reward.id).values(reward_id=None)
    )
    db.delete(reward)
    db.flush()


def delete_template(db: Session, template: RecurringQuest) -> None:
    # Уже созданные экземпляры (на доске и в архиве) остаются — как обычные квесты.
    db.execute(
        update(Quest).where(Quest.recurring_quest_id == template.id).values(recurring_quest_id=None)
    )
    db.delete(template)
    db.flush()
