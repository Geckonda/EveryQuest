from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://everyquest:everyquest@localhost:5432/everyquest"

    jwt_secret: str = "change-me"
    jwt_access_ttl_minutes: int = 15
    jwt_refresh_ttl_days: int = 30

    cors_origins: list[str] = ["http://localhost:5173"]

    # Планировщик внутри API. По умолчанию выключен: задачи выполняет воркер
    # (python -m app.worker). Включить — для запуска одним процессом без docker.
    scheduler_enabled: bool = False
    scheduler_interval_seconds: int = 300


settings = Settings()
