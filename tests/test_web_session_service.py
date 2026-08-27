# -*- coding: utf-8 -*-

from datetime import timedelta

import services.web_session_service as web_session_service
from services.web_session_service import _utcnow_naive
from tests._fake_database import FakeDatabase


def setup_function():
    FakeDatabase.reset()
    web_session_service.Database = FakeDatabase


def test_create_session_returns_a_raw_token():
    token = web_session_service.create_session(user_id=1)

    assert isinstance(token, str)
    assert len(token) > 20


def test_create_session_never_stores_the_raw_token():
    token = web_session_service.create_session(user_id=1)

    stored = FakeDatabase.web_sessions[0]["TokenHash"]
    assert stored != token


def test_create_session_stores_user_ref_and_metadata():
    web_session_service.create_session(
        user_id=7, user_agent="pytest-agent", ip_address="127.0.0.1"
    )

    row = FakeDatabase.web_sessions[0]
    assert row["UserRef"] == 7
    assert row["UserAgent"] == "pytest-agent"
    assert row["IPAddress"] == "127.0.0.1"
    assert row["IsRevoked"] is False


def test_validate_session_with_valid_token_returns_user_id():
    token = web_session_service.create_session(user_id=42)

    user_id = web_session_service.validate_session(token)

    assert user_id == 42


def test_validate_session_updates_last_activity():
    token = web_session_service.create_session(user_id=42)
    FakeDatabase.web_sessions[0]["LastActivity"] = "OLD"

    web_session_service.validate_session(token)

    assert FakeDatabase.web_sessions[0]["LastActivity"] == "NOW"


def test_validate_session_with_unknown_token_returns_none():
    assert web_session_service.validate_session("not-a-real-token") is None


def test_validate_session_with_empty_token_returns_none():
    assert web_session_service.validate_session("") is None
    assert web_session_service.validate_session(None) is None


def test_validate_session_with_expired_token_returns_none():
    token = web_session_service.create_session(user_id=42)
    FakeDatabase.web_sessions[0]["ExpiresAt"] = _utcnow_naive() - timedelta(hours=1)

    assert web_session_service.validate_session(token) is None


def test_revoke_session_makes_token_invalid():
    token = web_session_service.create_session(user_id=42)
    assert web_session_service.validate_session(token) == 42

    web_session_service.revoke_session(token)

    assert web_session_service.validate_session(token) is None


def test_revoke_session_does_not_delete_the_row():
    token = web_session_service.create_session(user_id=42)

    web_session_service.revoke_session(token)

    assert len(FakeDatabase.web_sessions) == 1
    assert FakeDatabase.web_sessions[0]["IsRevoked"] is True


def test_revoke_session_with_empty_token_does_not_raise():
    web_session_service.revoke_session("")
    web_session_service.revoke_session(None)
