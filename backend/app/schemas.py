from datetime import date, datetime, time
from decimal import Decimal
from typing import Annotated, Any, ClassVar, Literal, Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    model_validator,
)


def _check_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ValueError("Неизвестный часовой пояс") from error
    return value


TimeZoneName = Annotated[str, AfterValidator(_check_timezone)]
Username = Annotated[str, Field(min_length=1, max_length=64)]
ShortName = Annotated[str, Field(min_length=1, max_length=64)]
LongName = Annotated[str, Field(min_length=1, max_length=200)]
Description = Annotated[str, Field(max_length=2000)]
HexColor = Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}$")]
Coins = Annotated[int, Field(ge=0, le=1_000_000)]  # верхняя граница = economy.MAX_COINS
TierLevel = Annotated[int, Field(ge=1, le=5)]
PenaltyMultiplier = Annotated[Decimal, Field(ge=0, le=10, decimal_places=2)]
# До недели — с запасом для таймера трат.
DurationMinutes = Annotated[int, Field(ge=1, le=7 * 24 * 60)]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PatchModel(BaseModel):
    """Тело PATCH: передаются только изменяемые поля.

    Явный null допустим лишь для полей из nullable_fields — остальные NOT NULL в базе.
    """

    nullable_fields: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="after")
    def _forbid_nulls(self) -> Self:
        for name in self.model_fields_set:
            if getattr(self, name) is None and name not in self.nullable_fields:
                raise ValueError(f"Поле {name} не может быть пустым")
        return self

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


# --- auth ---


class RegisterIn(BaseModel):
    email: EmailStr
    username: Username
    password: str = Field(min_length=8, max_length=128)
    timezone: TimeZoneName = "UTC"


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class AuthSessionOut(ORMModel):
    """Устройство, с которого выполнен вход."""

    id: int
    user_agent: str | None
    created_at: datetime
    # Обновляется при каждом обновлении токена — то есть не реже раза в 15 минут работы.
    last_used_at: datetime
    current: bool = False


class AccessToken(BaseModel):
    """Refresh-токен в теле не отдаётся — он в httpOnly-cookie."""

    access_token: str
    token_type: str = "bearer"


# --- me ---


class UserOut(ORMModel):
    id: int
    email: str
    username: str
    balance: int
    timezone: str
    # Число, а не Decimal: иначе в JSON уйдёт строкой «1.00».
    penalty_multiplier: float
    created_at: datetime


class UserUpdate(PatchModel):
    username: Username | None = None
    timezone: TimeZoneName | None = None
    penalty_multiplier: PenaltyMultiplier | None = None


# --- тиры ---


class TierOut(ORMModel):
    id: int
    name: str
    level: int
    default_reward: int
    color: str | None
    is_archived: bool


class TierCreate(BaseModel):
    name: ShortName
    level: TierLevel
    default_reward: Coins
    color: HexColor | None = None


class TierUpdate(PatchModel):
    nullable_fields = frozenset({"color"})

    name: ShortName | None = None
    level: TierLevel | None = None
    default_reward: Coins | None = None
    color: HexColor | None = None
    is_archived: bool | None = None


# --- категории ---


class CategoryOut(ORMModel):
    id: int
    name: str
    description: str | None
    color: str | None
    is_archived: bool


class CategoryCreate(BaseModel):
    name: ShortName
    description: Description | None = None
    color: HexColor | None = None


class CategoryUpdate(PatchModel):
    nullable_fields = frozenset({"description", "color"})

    name: ShortName | None = None
    description: Description | None = None
    color: HexColor | None = None
    is_archived: bool | None = None


# --- траты ---


class RewardOut(ORMModel):
    id: int
    name: str
    description: str | None
    price: int
    duration_minutes: int | None
    is_archived: bool
    created_at: datetime


class RewardCreate(BaseModel):
    name: LongName
    description: Description | None = None
    price: Coins
    duration_minutes: DurationMinutes | None = None


class RewardUpdate(PatchModel):
    nullable_fields = frozenset({"description", "duration_minutes"})

    name: LongName | None = None
    description: Description | None = None
    price: Coins | None = None
    duration_minutes: DurationMinutes | None = None
    is_archived: bool | None = None


# --- квесты ---

QuestStatus = Literal["active", "completed", "failed", "archived"]
CloseReason = Literal["completed", "expired", "abandoned", "archived"]


class QuestOut(ORMModel):
    id: int
    name: str
    description: str | None
    tier_id: int
    category_id: int | None
    recurring_quest_id: int | None
    period_date: date | None
    reward: int
    penalty: int
    status: QuestStatus
    created_at: datetime
    due_at: datetime | None
    closed_at: datetime | None
    close_reason: CloseReason | None
    penalty_applied: bool


class QuestCreate(BaseModel):
    name: LongName
    description: Description | None = None
    tier_id: int
    category_id: int | None = None
    # Не переданы: награда — из тира, штраф — награда × множитель пользователя.
    reward: Coins | None = None
    penalty: Coins | None = None
    due_at: AwareDatetime | None = None


class QuestUpdate(PatchModel):
    nullable_fields = frozenset({"description", "category_id", "due_at"})

    name: LongName | None = None
    description: Description | None = None
    tier_id: int | None = None
    category_id: int | None = None
    reward: Coins | None = None
    penalty: Coins | None = None
    due_at: AwareDatetime | None = None
    # Убрать квест без штрафа. Вернуть из архива нельзя.
    status: Literal["archived"] | None = None


class QuestPage(BaseModel):
    """Страница архива квестов: свежезакрытые сверху."""

    items: list[QuestOut]
    next_cursor: str | None = None


class QuestClosed(BaseModel):
    """Ответ на сдачу или провал квеста: квест и новый баланс."""

    quest: QuestOut
    balance: int


# --- повторяющиеся квесты ---

Frequency = Literal["daily", "weekly", "monthly"]
Interval = Annotated[int, Field(ge=1, le=365)]
DayOfMonth = Annotated[int, Field(ge=1, le=31)]
DaysOfWeek = list[Annotated[int, Field(ge=1, le=7)]]


def check_schedule(
    frequency: str,
    days_of_week: list[int] | None,
    day_of_month: int | None,
    start_date: date | None,
    end_date: date | None,
) -> list[int] | None:
    """Проверяет согласованность расписания; возвращает нормализованные дни недели."""
    if frequency != "weekly" and days_of_week:
        raise ValueError("Дни недели задаются только для еженедельных квестов")
    if frequency != "monthly" and day_of_month is not None:
        raise ValueError("Число месяца задаётся только для ежемесячных квестов")
    if start_date and end_date and end_date < start_date:
        raise ValueError("Дата окончания раньше даты начала")
    return sorted(set(days_of_week)) if days_of_week else None


class RecurringQuestOut(ORMModel):
    id: int
    name: str
    description: str | None
    tier_id: int
    category_id: int | None
    reward: int
    penalty: int
    frequency: Frequency
    interval: int
    days_of_week: list[int] | None
    day_of_month: int | None
    due_time: time
    start_date: date
    end_date: date | None
    is_active: bool
    is_archived: bool
    created_at: datetime
    # Ближайший срок будущего экземпляра; None — на паузе, в архиве или расписание закончилось.
    next_due_at: datetime | None = None


class RecurringQuestCreate(BaseModel):
    name: LongName
    description: Description | None = None
    tier_id: int
    category_id: int | None = None
    reward: Coins | None = None
    penalty: Coins | None = None
    frequency: Frequency
    interval: Interval = 1
    days_of_week: DaysOfWeek | None = None
    day_of_month: DayOfMonth | None = None
    due_time: time = time(23, 59)
    # Не передана — сегодня по времени пользователя.
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def _schedule(self) -> Self:
        self.days_of_week = check_schedule(
            self.frequency, self.days_of_week, self.day_of_month, self.start_date, self.end_date
        )
        return self


class RecurringQuestUpdate(PatchModel):
    nullable_fields = frozenset(
        {"description", "category_id", "days_of_week", "day_of_month", "end_date"}
    )

    name: LongName | None = None
    description: Description | None = None
    tier_id: int | None = None
    category_id: int | None = None
    reward: Coins | None = None
    penalty: Coins | None = None
    frequency: Frequency | None = None
    interval: Interval | None = None
    days_of_week: DaysOfWeek | None = None
    day_of_month: DayOfMonth | None = None
    due_time: time | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_active: bool | None = None
    is_archived: bool | None = None


# --- календарь ---


class ForecastQuest(BaseModel):
    """Будущий экземпляр повторяющегося квеста: появится на доске в начале своего периода."""

    recurring_quest_id: int
    period_date: date
    name: str
    tier_id: int
    category_id: int | None
    reward: int
    penalty: int
    due_at: datetime


class CalendarOut(BaseModel):
    # Квесты со сроком в диапазоне — любого статуса.
    quests: list[QuestOut]
    forecast: list[ForecastQuest]


# --- транзакции ---

TransactionType = Literal["quest_reward", "penalty", "purchase", "manual", "reversal"]


class TransactionOut(ORMModel):
    id: int
    amount: int
    type: TransactionType
    quest_id: int | None
    reward_id: int | None
    note: str | None
    balance_after: int
    created_at: datetime
    # Название квеста или траты — чтобы журнал читался без лишних запросов.
    title: str | None = None


class TransactionPage(BaseModel):
    items: list[TransactionOut]
    # Только на первой странице (без курсора): пересчитывать всё на каждой — дорого.
    total: int | None = None
    # Курсор следующей страницы; None — дальше записей нет.
    next_cursor: str | None = None


class BalanceChange(BaseModel):
    transaction: TransactionOut
    balance: int


# --- идущие траты ---


class RewardSessionOut(ORMModel):
    id: int
    reward_id: int | None
    name: str
    started_at: datetime
    ends_at: datetime
    finished_at: datetime | None


class PurchaseOut(BalanceChange):
    # Есть, если у траты задана длительность.
    session: RewardSessionOut | None = None


class DaySummary(BaseModel):
    """Итог дня: все суммы положительные, кроме manual (поправка может быть в обе стороны)."""

    date: date
    earned: int
    spent: int
    penalties: int
    manual: int


class ManualTransactionIn(BaseModel):
    amount: Annotated[int, Field(ge=-1_000_000, le=1_000_000)]
    note: Description | None = None

    @model_validator(mode="after")
    def _non_zero(self) -> Self:
        if self.amount == 0:
            raise ValueError("Сумма не может быть нулевой")
        return self


# --- ошибки ---


class ArchiveBlocker(BaseModel):
    id: int
    name: str


class ArchiveConflict(BaseModel):
    """detail ответа 409: что мешает архивировать тир или категорию."""

    message: str
    quests: list[ArchiveBlocker]
    recurring_quests: list[ArchiveBlocker]
