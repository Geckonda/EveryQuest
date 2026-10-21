from typing import Literal, Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Секреты-заглушки из примеров и docker-compose — на проде с ними не стартуем.
_PLACEHOLDER_SECRETS = {"change-me", "dev-secret-change-me", ""}
MIN_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # prod — строгие проверки при старте (секрет, Secure-cookie).
    environment: Literal["dev", "test", "prod"] = "dev"

    database_url: str = "postgresql+psycopg://everyquest:everyquest@localhost:5432/everyquest"

    jwt_secret: str = "change-me"
    jwt_access_ttl_minutes: int = 15
    jwt_refresh_ttl_days: int = 30

    # Refresh-токен в cookie только по HTTPS. Браузеры считают http://localhost безопасным,
    # так что и в разработке можно оставить true; выключают для тестов.
    cookie_secure: bool = True

    cors_origins: list[str] = ["http://localhost:5173"]

    # Планировщик внутри API. По умолчанию выключен: задачи выполняет воркер
    # (python -m app.worker). Включить — для запуска одним процессом без docker.
    scheduler_enabled: bool = False
    scheduler_interval_seconds: int = 300

    @model_validator(mode="after")
    def _strict_in_prod(self) -> Self:
        if self.environment != "prod":
            return self
        if self.jwt_secret in _PLACEHOLDER_SECRETS or len(self.jwt_secret) < MIN_SECRET_LENGTH:
            raise ValueError(
                f"JWT_SECRET не задан или короче {MIN_SECRET_LENGTH} символов. "
                'Сгенерируйте: python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
        if not self.cookie_secure:
            raise ValueError("COOKIE_SECURE=false на проде: refresh-токен ушёл бы по HTTP")
        return self


settings = Settings()
