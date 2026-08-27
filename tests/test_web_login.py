# -*- coding: utf-8 -*-
"""
Phase 16C — تست‌های /login و /logout.

این تست‌ها لایه HTTP (FastAPI) را از طریق FakeDatabase بررسی می‌کنند؛ به
هیچ SQL Server واقعی نیاز ندارند و منطق auth_service/web_session_service
را با آن‌هایی که در tests/test_auth_service.py و
tests/test_web_session_service.py مستقیماً پوشش داده شده، دوباره تست
نمی‌کنند — فقط اتصال صحیح این سرویس‌ها به endpoint های وب را بررسی
می‌کنند.
"""

from fastapi.testclient import TestClient

import services.auth_service as auth_service
import services.web_session_service as web_session_service
from tests._fake_database import FakeDatabase
from utils.security import hash_password
from web.app import app

client = TestClient(app)


def setup_function():
    FakeDatabase.reset()
    auth_service.Database = FakeDatabase
    web_session_service.Database = FakeDatabase
    client.cookies.clear()

    password_hash, salt = hash_password("correct-horse")
    FakeDatabase.users = [
        {
            "ID": 1,
            "Username": "davar",
            "PasswordHash": password_hash,
            "PasswordSalt": salt,
            "FullName": "Davar",
            "IsAdmin": True,
            "IsActive": True,
            "LastLogin": None,
        }
    ]


def test_login_with_correct_credentials_returns_200():
    response = client.post(
        "/login", json={"username": "davar", "password": "correct-horse"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_login_with_correct_credentials_sets_session_cookie():
    response = client.post(
        "/login", json={"username": "davar", "password": "correct-horse"}
    )
    assert "storeapp_session" in response.cookies


def test_login_response_never_contains_password_fields():
    response = client.post(
        "/login", json={"username": "davar", "password": "correct-horse"}
    )
    body = response.text
    assert "PasswordHash" not in body
    assert "PasswordSalt" not in body


def test_login_with_wrong_password_returns_401():
    response = client.post(
        "/login", json={"username": "davar", "password": "wrong-password"}
    )
    assert response.status_code == 401
    assert "storeapp_session" not in response.cookies


def test_login_with_unknown_username_returns_401():
    response = client.post(
        "/login", json={"username": "nobody", "password": "whatever"}
    )
    assert response.status_code == 401


def test_login_creates_a_web_session_row():
    client.post("/login", json={"username": "davar", "password": "correct-horse"})

    assert len(FakeDatabase.web_sessions) == 1
    assert FakeDatabase.web_sessions[0]["UserRef"] == 1


def test_logout_revokes_the_session():
    client.post("/login", json={"username": "davar", "password": "correct-horse"})

    response = client.post("/logout")

    assert response.status_code == 200
    assert FakeDatabase.web_sessions[0]["IsRevoked"] is True


def test_logout_without_any_session_does_not_error():
    response = client.post("/logout")
    assert response.status_code == 200


class _BrokenDatabase:
    """شبیه‌سازی نبود دسترسی واقعی به SQL Server (مثل این sandbox)."""

    def __init__(self, *args, **kwargs):
        raise RuntimeError("simulated: no real SQL Server available")


def test_login_reports_db_failure_as_503_not_raw_500():
    auth_service.Database = _BrokenDatabase

    response = client.post(
        "/login", json={"username": "davar", "password": "correct-horse"}
    )

    assert response.status_code == 503
    assert response.json()["status"] == "error"


def test_logout_with_db_failure_still_returns_200():
    web_session_service.Database = _BrokenDatabase

    response = client.post("/logout")

    assert response.status_code == 200
