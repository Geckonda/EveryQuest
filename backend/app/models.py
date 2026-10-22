from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

# Все даты-время хранятся в UTC (timestamptz).
TZDateTime = DateTime(timezone=True)


def created_at_column() -> Mapped[datetime]:
    return mapped_column(TZDateTime, server_default=func.now(), nullable=False)


def user_fk() -> Mapped[int]:
    return mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("penalty_multiplier BETWEEN 0 AND 10", name="penalty_multiplier_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    # Кэш суммы transactions.amount; может быть отрицательным.
    balance: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    # IANA, напр. 'Europe/Saratov'.
    timezone: Mapped[str] = mapped_column(Text, server_default="UTC", nullable=False)
    # Штраф нового квеста по умолчанию = награда × множитель.
    penalty_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), server_default="1", nullable=False
    )
    created_at: Mapped[datetime] = created_at_column()


class AuthSession(Base):
    """Сессия входа — одно устройство. Refresh-токен хранится только хэшем.

    Токен меняется при каждом обновлении (ротация). Предыдущий хэш помнится, чтобы
    отличить гонку двух вкладок (старый токен сразу после смены) от кражи (старый
    токен позже) — во втором случае сессия отзывается.
    """

    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = user_fk()
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    previous_token_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    rotated_at: Mapped[datetime | None] = mapped_column(TZDateTime)
    user_agent: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = created_at_column()
    last_used_at: Mapped[datetime] = created_at_column()
    expires_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(TZDateTime)


class AuthAttempt(Base):
    """Неудачный вход или регистрация — для ограничения частоты попыток."""

    __tablename__ = "auth_attempts"
    __table_args__ = (
        CheckConstraint("kind IN ('login', 'register')", name="kind"),
        Index("ix_auth_attempts_kind_ip_created_at", "kind", "ip", "created_at"),
        Index("ix_auth_attempts_kind_email_created_at", "kind", "email", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    ip: Mapped[str] = mapped_column(String(64), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320))
    created_at: Mapped[datetime] = created_at_column()


class Tier(Base):
    __tablename__ = "tiers"
    __table_args__ = (CheckConstraint("level BETWEEN 1 AND 5", name="level_range"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = user_fk()
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    default_reward: Mapped[int] = mapped_column(Integer, nullable=False)
    color: Mapped[str | None] = mapped_column(String(16))
    is_archived: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = user_fk()
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    color: Mapped[str | None] = mapped_column(String(16))
    is_archived: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)


class RecurringQuest(Base):
    """Шаблон, по которому планировщик создаёт квесты-экземпляры."""

    __tablename__ = "recurring_quests"
    __table_args__ = (
        CheckConstraint("frequency IN ('daily', 'weekly', 'monthly')", name="frequency"),
        CheckConstraint('"interval" >= 1', name="interval_positive"),
        CheckConstraint("day_of_month BETWEEN 1 AND 31", name="day_of_month_range"),
        CheckConstraint("days_of_week <@ ARRAY[1,2,3,4,5,6,7]::smallint[]", name="days_of_week"),
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name="date_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = user_fk()
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    tier_id: Mapped[int] = mapped_column(ForeignKey("tiers.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    reward: Mapped[int] = mapped_column(Integer, nullable=False)
    penalty: Mapped[int] = mapped_column(Integer, nullable=False)
    frequency: Mapped[str] = mapped_column(String(16), nullable=False)
    interval: Mapped[int] = mapped_column(SmallInteger, server_default="1", nullable=False)
    days_of_week: Mapped[list[int] | None] = mapped_column(ARRAY(SmallInteger))
    # 31 = последний день месяца.
    day_of_month: Mapped[int | None] = mapped_column(SmallInteger)
    # Локальное время пользователя.
    due_time: Mapped[time] = mapped_column(Time, server_default=text("'23:59'"), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    created_at: Mapped[datetime] = created_at_column()


class Quest(Base):
    """Конкретный квест: разовый или экземпляр повторяющегося."""

    __tablename__ = "quests"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'completed', 'failed', 'archived')", name="status"),
        # Причина закрытия обязана соответствовать статусу; у активного её нет.
        CheckConstraint(
            "(status = 'active' AND close_reason IS NULL)"
            " OR (status = 'completed' AND close_reason = 'completed')"
            " OR (status = 'failed' AND close_reason IN ('expired', 'abandoned'))"
            " OR (status = 'archived' AND close_reason = 'archived')",
            name="close_reason",
        ),
        # У закрытого квеста всегда есть момент закрытия — по нему листается архив.
        CheckConstraint("(status = 'active') = (closed_at IS NULL)", name="closed_at"),
        Index("ix_quests_user_id_closed_at_id", "user_id", "closed_at", "id"),
        UniqueConstraint("recurring_quest_id", "period_date"),
        Index("ix_quests_status_due_at", "status", "due_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = user_fk()
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    tier_id: Mapped[int] = mapped_column(ForeignKey("tiers.id"), nullable=False)
    recurring_quest_id: Mapped[int | None] = mapped_column(ForeignKey("recurring_quests.id"))
    period_date: Mapped[date | None] = mapped_column(Date)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    reward: Mapped[int] = mapped_column(Integer, nullable=False)
    penalty: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), server_default="active", nullable=False)
    created_at: Mapped[datetime] = created_at_column()
    due_at: Mapped[datetime | None] = mapped_column(TZDateTime)
    # Когда квест закрыт любым способом; у проваленного по сроку — сам срок.
    closed_at: Mapped[datetime | None] = mapped_column(TZDateTime)
    # completed | expired (срок вышел) | abandoned (провален вручную) | archived (снят).
    close_reason: Mapped[str | None] = mapped_column(String(16))
    penalty_applied: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)


class Reward(Base):
    """«Трата» — развлечение, которое оплачивается монетами."""

    __tablename__ = "rewards"
    __table_args__ = (CheckConstraint("price >= 0", name="price_non_negative"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = user_fk()
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    # Задел под таймер трат.
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    is_archived: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    created_at: Mapped[datetime] = created_at_column()


class RewardSession(Base):
    """Идущая трата с длительностью: «ТикТок на 20 минут» — с момента заказа."""

    __tablename__ = "reward_sessions"
    __table_args__ = (
        CheckConstraint("ends_at > started_at", name="ends_after_start"),
        Index("ix_reward_sessions_user_id_ends_at", "user_id", "ends_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reward_id: Mapped[int] = mapped_column(ForeignKey("rewards.id"), nullable=False)
    # Одна покупка — один сеанс.
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id"), unique=True, nullable=False
    )
    # Название на момент заказа: трату могут переименовать, пока сеанс идёт.
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    started_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)
    # Закончили раньше срока; NULL — шёл до ends_at.
    finished_at: Mapped[datetime | None] = mapped_column(TZDateTime)


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint(
            "type IN ('quest_reward', 'penalty', 'purchase', 'manual', 'reversal')", name="type"
        ),
        # С id: летопись листается курсором (created_at, id) — по индексу с любой глубины.
        Index("ix_transactions_user_id_created_at_id", "user_id", "created_at", "id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    # +награда, −штраф, −покупка; reversal — отмена ошибочной сдачи или провала квеста.
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    quest_id: Mapped[int | None] = mapped_column(ForeignKey("quests.id"))
    reward_id: Mapped[int | None] = mapped_column(ForeignKey("rewards.id"))
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    # Комментарий к ручной корректировке.
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()
