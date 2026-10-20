from datetime import datetime
from typing import Annotated, Any, ClassVar, Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, model_validator


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
Coins = Annotated[int, Field(ge=0, le=1_000_000)]
TierLevel = Annotated[int, Field(ge=1, le=5)]
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


class RefreshIn(BaseModel):
    refresh_token: str


class AccessToken(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPair(AccessToken):
    refresh_token: str


# --- me ---


class UserOut(ORMModel):
    id: int
    email: str
    username: str
    balance: int
    timezone: str
    created_at: datetime


class UserUpdate(PatchModel):
    username: Username | None = None
    timezone: TimeZoneName | None = None


# --- тиры ---


class TierOut(ORMModel):
    id: int
    name: str
    level: int
    default_reward: int
    default_penalty: int
    color: str | None
    is_archived: bool


class TierCreate(BaseModel):
    name: ShortName
    level: TierLevel
    default_reward: Coins
    default_penalty: Coins
    color: HexColor | None = None


class TierUpdate(PatchModel):
    nullable_fields = frozenset({"color"})

    name: ShortName | None = None
    level: TierLevel | None = None
    default_reward: Coins | None = None
    default_penalty: Coins | None = None
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


# --- ошибки ---


class ArchiveBlocker(BaseModel):
    id: int
    name: str


class ArchiveConflict(BaseModel):
    """detail ответа 409: что мешает архивировать тир или категорию."""

    message: str
    quests: list[ArchiveBlocker]
    recurring_quests: list[ArchiveBlocker]
