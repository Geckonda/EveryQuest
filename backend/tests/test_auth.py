from fastapi.testclient import TestClient

from app.defaults import DEFAULT_CATEGORIES, DEFAULT_TIERS
from app.security import create_access_token
from tests.conftest import auth_headers, register


def test_register_copies_default_tiers_and_categories(client: TestClient) -> None:
    headers = auth_headers(register(client))

    tiers = client.get("/api/v1/tiers", headers=headers).json()
    assert [t["name"] for t in tiers] == [name for name, *_ in DEFAULT_TIERS]
    assert tiers[0]["default_reward"] == DEFAULT_TIERS[0][2]

    categories = client.get("/api/v1/categories", headers=headers).json()
    assert [c["name"] for c in categories] == [name for name, *_ in DEFAULT_CATEGORIES]


def test_register_sets_profile(client: TestClient) -> None:
    tokens = register(client, email="Hero@Example.com", timezone="Europe/Saratov")
    me = client.get("/api/v1/me", headers=auth_headers(tokens)).json()
    assert me["email"] == "hero@example.com"
    assert me["balance"] == 0
    assert me["timezone"] == "Europe/Saratov"


def test_register_duplicate_email_case_insensitive(client: TestClient) -> None:
    register(client, email="hero@example.com")
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "HERO@example.com", "username": "Other", "password": "another-pass"},
    )
    assert response.status_code == 409


def test_register_validation(client: TestClient) -> None:
    base = {"email": "a@example.com", "username": "A", "password": "secret-pass"}
    for bad in ({"timezone": "Mars/Olympus"}, {"password": "short"}, {"email": "not-an-email"}):
        response = client.post("/api/v1/auth/register", json={**base, **bad})
        assert response.status_code == 422, bad


def test_login(client: TestClient) -> None:
    register(client, email="hero@example.com", password="secret-pass")

    ok = client.post(
        "/api/v1/auth/login", json={"email": "HERO@example.com", "password": "secret-pass"}
    )
    assert ok.status_code == 200
    assert client.get("/api/v1/me", headers=auth_headers(ok.json())).status_code == 200

    wrong = client.post(
        "/api/v1/auth/login", json={"email": "hero@example.com", "password": "wrong-pass"}
    )
    assert wrong.status_code == 401

    unknown = client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "secret-pass"}
    )
    assert unknown.status_code == 401


def test_register_and_login_set_refresh_cookie(client: TestClient) -> None:
    """Refresh-токен — только в httpOnly-cookie, в теле ответа его нет."""
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "hero@example.com", "username": "Hero", "password": "secret-pass"},
    )
    assert "refresh_token" not in response.json()
    cookie = response.headers["set-cookie"]
    assert cookie.startswith("eq_refresh=")
    for flag in ("HttpOnly", "Path=/api/v1/auth", "SameSite=strict"):
        assert flag in cookie, flag

    login = client.post(
        "/api/v1/auth/login", json={"email": "hero@example.com", "password": "secret-pass"}
    )
    assert login.headers["set-cookie"].startswith("eq_refresh=")


def test_protected_endpoints_require_token(client: TestClient) -> None:
    for path in ("/api/v1/me", "/api/v1/tiers", "/api/v1/categories"):
        assert client.get(path).status_code == 401
        assert client.get(path, headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_token_of_missing_session_rejected(client: TestClient) -> None:
    headers = {"Authorization": f"Bearer {create_access_token(999_999, 999_999)}"}
    assert client.get("/api/v1/me", headers=headers).status_code == 401


def test_update_me(client: TestClient) -> None:
    headers = auth_headers(register(client))

    response = client.patch(
        "/api/v1/me", headers=headers, json={"username": "Новое имя", "timezone": "Asia/Tokyo"}
    )
    assert response.status_code == 200
    assert response.json()["username"] == "Новое имя"
    assert response.json()["timezone"] == "Asia/Tokyo"

    bad = client.patch("/api/v1/me", headers=headers, json={"timezone": "Nowhere"})
    assert bad.status_code == 422


def test_penalty_multiplier(client: TestClient) -> None:
    headers = auth_headers(register(client))
    assert client.get("/api/v1/me", headers=headers).json()["penalty_multiplier"] == 1

    response = client.patch("/api/v1/me", headers=headers, json={"penalty_multiplier": 1.5})
    assert response.status_code == 200
    assert response.json()["penalty_multiplier"] == 1.5  # число, а не строка «1.50»

    for bad in (-1, 10.01, 1.234, None):
        rejected = client.patch("/api/v1/me", headers=headers, json={"penalty_multiplier": bad})
        assert rejected.status_code == 422, bad


def test_default_due_time(client: TestClient) -> None:
    headers = auth_headers(register(client))
    # По умолчанию — как было до настройки: конец дня.
    assert client.get("/api/v1/me", headers=headers).json()["default_due_time"] == "23:59:00"

    response = client.patch("/api/v1/me", headers=headers, json={"default_due_time": "18:30"})
    assert response.status_code == 200
    assert response.json()["default_due_time"] == "18:30:00"
    assert client.get("/api/v1/me", headers=headers).json()["default_due_time"] == "18:30:00"

    for bad in ("25:00", "18:30:15", "18:30+03:00", "вечер", None):
        rejected = client.patch("/api/v1/me", headers=headers, json={"default_due_time": bad})
        assert rejected.status_code == 422, bad


def test_users_see_only_their_own_data(client: TestClient) -> None:
    first = auth_headers(register(client, email="first@example.com"))
    second = auth_headers(register(client, email="second@example.com"))

    first_ids = {t["id"] for t in client.get("/api/v1/tiers", headers=first).json()}
    second_ids = {t["id"] for t in client.get("/api/v1/tiers", headers=second).json()}
    assert len(first_ids) == len(second_ids) == len(DEFAULT_TIERS)
    assert first_ids.isdisjoint(second_ids)
