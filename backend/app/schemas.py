from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field


def _check_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ValueError("Неизвестный часовой пояс") from error
    return value


TimeZoneName = Annotated[str, AfterValidator(_check_timezone)]
Username = Annotated[str, Field(min_length=1, max_length=64)]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


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


class UserUpdate(BaseModel):
    username: Username | None = None
    timezone: TimeZoneName | None = None


# --- справочники ---


class TierOut(ORMModel):
    id: int
    name: str
    level: int
    default_reward: int
    default_penalty: int
    color: str | None
    is_archived: bool


class CategoryOut(ORMModel):
    id: int
    name: str
    description: str | None
    color: str | None
    is_archived: bool
