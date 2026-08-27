# -*- coding: utf-8 -*-

import services.auth_service as auth_service
from tests._fake_database import FakeDatabase
from utils.security import hash_password


def setup_function():
    FakeDatabase.reset()
    auth_service.Database = FakeDatabase

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
        },
        {
            "ID": 2,
            "Username": "disabled-user",
            "PasswordHash": password_hash,
            "PasswordSalt": salt,
            "FullName": "Disabled User",
            "IsAdmin": False,
            "IsActive": False,
            "LastLogin": None,
        },
    ]


def test_authenticate_user_with_correct_credentials_succeeds():
    user = auth_service.authenticate_user("davar", "correct-horse")

    assert user is not None
    assert user["Username"] == "davar"
    assert user["ID"] == 1


def test_authenticate_user_never_leaks_password_fields():
    user = auth_service.authenticate_user("davar", "correct-horse")

    assert "PasswordHash" not in user
    assert "PasswordSalt" not in user


def test_authenticate_user_records_last_login():
    auth_service.authenticate_user("davar", "correct-horse")

    assert FakeDatabase.users[0]["LastLogin"] == "NOW"


def test_authenticate_user_with_wrong_password_fails():
    user = auth_service.authenticate_user("davar", "wrong-password")

    assert user is None


def test_authenticate_user_with_unknown_username_fails():
    user = auth_service.authenticate_user("nobody", "correct-horse")

    assert user is None


def test_authenticate_inactive_user_fails():
    user = auth_service.authenticate_user("disabled-user", "correct-horse")

    assert user is None


def test_authenticate_user_with_empty_credentials_fails():
    assert auth_service.authenticate_user("", "") is None
    assert auth_service.authenticate_user("davar", "") is None
    assert auth_service.authenticate_user("", "correct-horse") is None
