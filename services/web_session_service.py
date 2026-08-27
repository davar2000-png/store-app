# -*- coding: utf-8 -*-
"""
Web Session Service — Phase 16C (Session Login)

مدیریت Session های وب (Login/Logout در مرورگر) — کاملاً مستقل از
services/session_service.py که برای بازیابی بعد از قطع برق در برنامه
دسکتاپی است و به جدول Sessions موجود (database/migrations/007_session_recovery.sql)
وصل است. آن جدول و آن سرویس در این فاز دست‌نخورده باقی می‌مانند.

جدول موردنیاز این سرویس: WebSessions
(database/migrations/015_web_sessions.sql)

⚠️ نکته امنیتی: توکن خام Session هرگز در دیتابیس ذخیره نمی‌شود — فقط هش
SHA-256 آن ذخیره می‌شود (همان اصل هش‌کردن رمز عبور در utils/security.py).
اگر دیتابیس افشا شود، توکن‌های فعال کاربران قابل استفاده مجدد نخواهند بود.
"""

import hashlib
import secrets
import sys
import os
from datetime import datetime, timedelta, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import Database

#: مدت اعتبار پیش‌فرض هر Session وب، بر حسب ساعت.
SESSION_LIFETIME_HOURS = 12


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _utcnow_naive() -> datetime:
    """
    زمان فعلی UTC به‌صورت naive (بدون tzinfo).

    این برنامه در همه‌جا (از جمله ستون‌های DATETIME2 در SQL Server از طریق
    pyodbc) از datetime بدون tzinfo استفاده می‌کند؛ برای جلوگیری از خطای
    مقایسه aware/naive، همان الگو اینجا هم حفظ می‌شود.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def create_session(user_id: int, user_agent: str = None, ip_address: str = None) -> str:
    """
    یک Session وب جدید برای این کاربر می‌سازد.

    خروجی: توکن خام Session که باید در Cookie مرورگر قرار بگیرد. این توکن
    خام هرگز در دیتابیس ذخیره نمی‌شود — فقط هش آن.
    """
    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)
    expires_at = _utcnow_naive() + timedelta(hours=SESSION_LIFETIME_HOURS)

    db = Database()
    try:
        db.execute(
            "INSERT INTO WebSessions "
            "(TokenHash, UserRef, ExpiresAt, UserAgent, IPAddress) "
            "VALUES (?, ?, ?, ?, ?)",
            (token_hash, user_id, expires_at, user_agent, ip_address),
        )
    finally:
        db.close()

    return raw_token


def validate_session(raw_token: str):
    """
    توکن خام (از Cookie درخواست) را بررسی می‌کند.

    خروجی: UserRef (int) در صورت معتبر و فعال بودن Session، یا None اگر
    Session وجود نداشته باشد، باطل (IsRevoked) شده باشد، یا منقضی شده باشد.
    """
    if not raw_token:
        return None

    token_hash = _hash_token(raw_token)

    db = Database()
    try:
        row = db.fetch_one(
            "SELECT * FROM WebSessions WHERE TokenHash = ?",
            (token_hash,),
        )
        if not row:
            return None
        if row["IsRevoked"]:
            return None
        if row["ExpiresAt"] < _utcnow_naive():
            return None

        db.execute(
            "UPDATE WebSessions SET LastActivity = GETDATE() WHERE ID = ?",
            (row["ID"],),
        )
    finally:
        db.close()

    return row["UserRef"]


def revoke_session(raw_token: str) -> None:
    """
    Session را باطل می‌کند (Logout).

    رکورد از دیتابیس حذف نمی‌شود (برای حفظ قابلیت بازبینی/Audit)، فقط
    IsRevoked=1 می‌شود؛ validate_session از این پس آن را رد خواهد کرد.
    """
    if not raw_token:
        return

    token_hash = _hash_token(raw_token)

    db = Database()
    try:
        db.execute(
            "UPDATE WebSessions SET IsRevoked = 1 WHERE TokenHash = ?",
            (token_hash,),
        )
    finally:
        db.close()
