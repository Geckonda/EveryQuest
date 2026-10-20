from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app import models  # noqa: F401  — регистрирует таблицы в metadata
from app.config import settings
from app.db import Base, get_db
from app.main import app

_MAIN_URL = make_url(settings.database_url)
TEST_DB_URL = _MAIN_URL.set(database=f"{_MAIN_URL.database}_test")


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    """Отдельная база <имя>_test, схема пересоздаётся на каждый прогон."""
    admin = create_engine(_MAIN_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": TEST_DB_URL.database},
        )
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{TEST_DB_URL.database}"'))
    admin.dispose()

    test_engine = create_engine(TEST_DB_URL)
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    """Каждый тест — во внешней транзакции, которая откатывается; commit в коде — savepoint."""
    with engine.connect() as conn:
        outer = conn.begin()
        session = Session(
            bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        yield session
        session.close()
        outer.rollback()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def register(
    client: TestClient, email: str = "hero@example.com", password: str = "secret-pass", **extra
) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "username": "Hero", "password": password, **extra},
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth_headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}
