"""Миграции против моделей.

Остальные тесты строят схему через metadata.create_all — ошибку в миграции они не заметят.
Здесь все миграции накатываются на отдельную пустую базу и схема сверяется с моделями,
а затем откатываются до нуля и накатываются снова — проверка downgrade.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Connection, Engine, create_engine, inspect, text

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from app.db import Base
from tests.conftest import _MAIN_URL

MIGRATIONS_DB_URL = _MAIN_URL.set(database=f"{_MAIN_URL.database}_migrations")
ALEMBIC_DIR = Path(__file__).resolve().parents[1] / "alembic"


@pytest.fixture(scope="module")
def empty_engine() -> Iterator[Engine]:
    """Свежая пустая база на модуль: каждый прогон начинается с нуля."""
    admin = create_engine(_MAIN_URL, isolation_level="AUTOCOMMIT")
    name = MIGRATIONS_DB_URL.database
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    engine = create_engine(MIGRATIONS_DB_URL)
    yield engine
    engine.dispose()
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
    admin.dispose()


def alembic(connection: Connection) -> Config:
    # Без alembic.ini: его fileConfig перенастроил бы логи pytest.
    config = Config()
    config.set_main_option("script_location", str(ALEMBIC_DIR))
    config.attributes["connection"] = connection
    return config


def schema_diff(engine: Engine) -> list:
    with engine.connect() as conn:
        context = MigrationContext.configure(conn, opts={"compare_type": True})
        return compare_metadata(context, Base.metadata)


def user_tables(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names()) - {"alembic_version"}


def test_upgrade_head_matches_models(empty_engine: Engine) -> None:
    with empty_engine.begin() as conn:
        command.upgrade(alembic(conn), "head")

    assert user_tables(empty_engine) == set(Base.metadata.tables)
    # Пустой список — миграции дают ровно ту схему, что описана в моделях.
    assert schema_diff(empty_engine) == []


def test_downgrade_to_base_and_back(empty_engine: Engine) -> None:
    with empty_engine.begin() as conn:
        command.upgrade(alembic(conn), "head")
    with empty_engine.begin() as conn:
        command.downgrade(alembic(conn), "base")
    assert user_tables(empty_engine) == set()

    with empty_engine.begin() as conn:
        command.upgrade(alembic(conn), "head")
    assert schema_diff(empty_engine) == []


def test_single_head() -> None:
    """Две ветки миграций (параллельные правки) — alembic upgrade head упадёт на проде."""
    from alembic.script import ScriptDirectory

    config = Config()
    config.set_main_option("script_location", str(ALEMBIC_DIR))
    assert len(ScriptDirectory.from_config(config).get_heads()) == 1
