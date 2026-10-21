"""Сессии входа: ротация refresh-токена, отзыв, лимиты попыток, проверка секрета."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import auth_tokens, ratelimit
from app.api.auth import REFRESH_COOKIE
from app.config import Settings
from app.jobs import purge_auth
from app.models import AuthAttempt, AuthSession
from tests.conftest import auth_headers, register

API = "/api/v1"
T0 = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)


class Clock:
    def __init__(self) -> None:
        self.now = T0

    def advance(self, **delta: float) -> None:
        self.now += timedelta(**delta)


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    clock = Clock()
    for module in (auth_tokens, ratelimit):
        monkeypatch.setattr(module, "utcnow", lambda: clock.now)
    return clock


def refresh(client: TestClient, token: str | None = None):
    """Обновить токен; token — подсунуть конкретный refresh-токен вместо cookie клиента."""
    if token is not None:
        client.cookies.clear()
        client.cookies.set(REFRESH_COOKIE, token)
    return client.post(f"{API}/auth/refresh")


def current_token(client: TestClient) -> str:
    token = client.cookies.get(REFRESH_COOKIE)
    assert token
    return token


def me(client: TestClient, tokens: dict) -> int:
    return client.get(f"{API}/me", headers=auth_headers(tokens)).status_code


# --- ротация ---


def test_refresh_rotates_token(client: TestClient, clock: Clock) -> None:
    register(client)
    first = current_token(client)

    response = refresh(client)

    assert response.status_code == 200
    assert me(client, response.json()) == 200
    second = current_token(client)
    assert second != first  # токен сменился
    assert refresh(client).status_code == 200  # новым можно пользоваться дальше


def test_refresh_without_cookie_or_with_garbage(client: TestClient) -> None:
    assert client.post(f"{API}/auth/refresh").status_code == 401
    rejected = refresh(client, "garbage")
    assert rejected.status_code == 401
    # Плохая cookie удаляется, чтобы браузер не слал её снова.
    assert 'eq_refresh=""' in rejected.headers["set-cookie"]


def test_parallel_tabs_race_is_tolerated(client: TestClient, clock: Clock) -> None:
    """Вторая вкладка пришла со старым токеном сразу после смены — это не кража."""
    register(client)
    old = current_token(client)
    refresh(client)
    new = current_token(client)

    clock.advance(seconds=5)
    late_tab = refresh(client, old)

    assert late_tab.status_code == 200
    assert me(client, late_tab.json()) == 200
    assert "set-cookie" not in late_tab.headers  # у браузера уже новая cookie
    assert refresh(client, new).status_code == 200  # сессия жива


def test_reused_old_token_revokes_session(client: TestClient, db: Session, clock: Clock) -> None:
    """Старый токен вне окна гонки — его кто-то сохранил. Отзываем сессию целиком."""
    tokens = register(client)
    old = current_token(client)
    refresh(client)
    new = current_token(client)

    clock.advance(minutes=5)
    assert refresh(client, old).status_code == 401

    # Отозвана вся сессия: и новым токеном, и выданным раньше access-токеном не войти.
    assert refresh(client, new).status_code == 401
    assert me(client, tokens) == 401
    assert db.scalar(select(func.count()).where(AuthSession.revoked_at.is_not(None))) == 1


def test_refresh_token_expires(client: TestClient, clock: Clock) -> None:
    register(client)
    clock.advance(days=31)
    assert refresh(client).status_code == 401


def test_refresh_extends_session(client: TestClient, clock: Clock) -> None:
    """Скользящее окно: пользуется раз в неделю — не разлогинивает."""
    register(client)
    for _ in range(6):
        clock.advance(days=7)
        assert refresh(client).status_code == 200


# --- выход ---


def test_logout_revokes_this_device_only(client: TestClient) -> None:
    phone = register(client, email="hero@example.com", password="secret-pass")
    phone_refresh = current_token(client)
    laptop = client.post(
        f"{API}/auth/login", json={"email": "hero@example.com", "password": "secret-pass"}
    ).json()
    laptop_refresh = current_token(client)

    client.cookies.clear()
    client.cookies.set(REFRESH_COOKIE, phone_refresh)
    response = client.post(f"{API}/auth/logout")
    assert response.status_code == 204

    assert me(client, phone) == 401  # access-токен отозванной сессии больше не работает
    assert me(client, laptop) == 200
    assert refresh(client, laptop_refresh).status_code == 200


def test_logout_without_cookie_is_ok(client: TestClient) -> None:
    assert client.post(f"{API}/auth/logout").status_code == 204


def test_logout_all(client: TestClient) -> None:
    phone = register(client, email="hero@example.com", password="secret-pass")
    phone_refresh = current_token(client)
    laptop = client.post(
        f"{API}/auth/login", json={"email": "hero@example.com", "password": "secret-pass"}
    ).json()
    stranger = register(client, email="stranger@example.com")

    response = client.post(f"{API}/auth/logout-all", headers=auth_headers(laptop))

    assert response.status_code == 204
    assert me(client, phone) == me(client, laptop) == 401
    assert refresh(client, phone_refresh).status_code == 401
    assert me(client, stranger) == 200  # чужие сессии не тронуты
    assert client.post(f"{API}/auth/logout-all").status_code == 401


def test_list_and_revoke_devices(client: TestClient) -> None:
    phone = register(client, email="hero@example.com", password="secret-pass")
    laptop = client.post(
        f"{API}/auth/login",
        json={"email": "hero@example.com", "password": "secret-pass"},
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0) Chrome/130.0"},
    ).json()

    devices = client.get(f"{API}/auth/sessions", headers=auth_headers(laptop)).json()
    assert len(devices) == 2
    current = [d for d in devices if d["current"]]
    assert len(current) == 1
    assert "Windows" in current[0]["user_agent"]
    other = next(d for d in devices if not d["current"])

    response = client.post(
        f"{API}/auth/sessions/{other['id']}/revoke", headers=auth_headers(laptop)
    )
    assert response.status_code == 204
    assert "set-cookie" not in response.headers  # своё устройство не тронуто
    assert me(client, phone) == 401
    assert me(client, laptop) == 200
    assert len(client.get(f"{API}/auth/sessions", headers=auth_headers(laptop)).json()) == 1


def test_revoke_current_device_clears_cookie(client: TestClient) -> None:
    tokens = register(client)
    [device] = client.get(f"{API}/auth/sessions", headers=auth_headers(tokens)).json()

    response = client.post(
        f"{API}/auth/sessions/{device['id']}/revoke", headers=auth_headers(tokens)
    )

    assert response.status_code == 204
    assert 'eq_refresh=""' in response.headers["set-cookie"]
    assert me(client, tokens) == 401


def test_cannot_revoke_foreign_or_dead_session(client: TestClient) -> None:
    mine = register(client, email="hero@example.com")
    [my_device] = client.get(f"{API}/auth/sessions", headers=auth_headers(mine)).json()
    stranger = register(client, email="stranger@example.com")

    foreign = client.post(
        f"{API}/auth/sessions/{my_device['id']}/revoke", headers=auth_headers(stranger)
    )
    assert foreign.status_code == 404
    assert me(client, mine) == 200
    assert (
        client.post(
            f"{API}/auth/sessions/999999/revoke", headers=auth_headers(stranger)
        ).status_code
        == 404
    )


# --- лимиты попыток ---


def login(client: TestClient, email: str, password: str, ip: str = "1.1.1.1"):
    return client.post(
        f"{API}/auth/login",
        json={"email": email, "password": password},
        headers={"X-Forwarded-For": ip},
    )


def test_failed_logins_limited_per_email(client: TestClient, clock: Clock) -> None:
    register(client, email="hero@example.com", password="secret-pass")
    for _ in range(5):
        assert login(client, "hero@example.com", "wrong-pass").status_code == 401

    blocked = login(client, "hero@example.com", "secret-pass")
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) > 0
    assert "Слишком много попыток" in blocked.json()["detail"]

    clock.advance(minutes=16)
    assert login(client, "hero@example.com", "secret-pass").status_code == 200


def test_successful_login_resets_email_failures(client: TestClient, clock: Clock) -> None:
    register(client, email="hero@example.com", password="secret-pass")
    for _ in range(4):
        login(client, "hero@example.com", "wrong-pass")
    assert login(client, "hero@example.com", "secret-pass").status_code == 200
    for _ in range(4):
        assert login(client, "hero@example.com", "wrong-pass").status_code == 401


def test_failed_logins_limited_per_ip(client: TestClient, clock: Clock) -> None:
    """Перебор многих email с одного адреса."""
    for i in range(20):
        assert login(client, f"user{i}@example.com", "whatever-pass").status_code == 401
    assert login(client, "other@example.com", "whatever-pass").status_code == 429


def test_registrations_limited_per_ip(client: TestClient, clock: Clock) -> None:
    for i in range(5):
        register(client, email=f"user{i}@example.com")
    response = client.post(
        f"{API}/auth/register",
        json={"email": "sixth@example.com", "username": "Six", "password": "secret-pass"},
    )
    assert response.status_code == 429


def test_purge_removes_old_attempts_and_dead_sessions(
    client: TestClient, db: Session, clock: Clock
) -> None:
    register(client)
    login(client, "hero@example.com", "wrong-pass")
    assert db.scalar(select(func.count()).select_from(AuthAttempt)) == 2  # регистрация + вход

    clock.advance(days=40)
    purge_auth(db, clock.now)

    assert db.scalar(select(func.count()).select_from(AuthAttempt)) == 0
    assert db.scalar(select(func.count()).select_from(AuthSession)) == 0


# --- проверка секрета на проде ---


@pytest.mark.parametrize(
    "secret",
    ["change-me", "dev-secret-change-me", "short-but-not-default"],
)
def test_prod_refuses_weak_secret(secret: str) -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(environment="prod", jwt_secret=secret)


def test_prod_refuses_insecure_cookie() -> None:
    with pytest.raises(ValidationError, match="COOKIE_SECURE"):
        Settings(environment="prod", jwt_secret="x" * 48, cookie_secure=False)


def test_prod_with_strong_secret_and_dev_defaults_ok() -> None:
    assert Settings(environment="prod", jwt_secret="x" * 48).environment == "prod"
    assert Settings(environment="dev", jwt_secret="change-me").jwt_secret == "change-me"
