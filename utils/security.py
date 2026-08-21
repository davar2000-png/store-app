# -*- coding: utf-8 -*-
"""ابزار هش کردن امن رمز عبور کاربران"""

import hashlib
import os
import secrets


def hash_password(password: str, salt: str = None) -> tuple:
    """
    رمز عبور را با salt هش می‌کند.
    خروجی: (password_hash, salt)
    """
    if salt is None:
        salt = secrets.token_hex(16)
    combined = (password + salt).encode("utf-8")
    hashed = hashlib.sha256(combined).hexdigest()
    return hashed, salt


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """بررسی می‌کند رمز واردشده با هش ذخیره‌شده مطابقت دارد یا نه"""
    hashed, _ = hash_password(password, salt)
    return hashed == stored_hash
