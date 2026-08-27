# -*- coding: utf-8 -*-
"""
Auth Service — Phase 16C (Auth Extraction)

این ماژول منطق احراز هویت (تطبیق Username/Password با جدول Users) را به
شکل یک Service مستقل ارائه می‌دهد تا هم لایه وب و هم — در صورت نیاز فازهای
بعدی — UI دسکتاپ بتوانند از همان منطق استفاده کنند، بدون کپی کردن کد.

⚠️ محدودیت‌های عمدی این فاز:
- فقط جدول Users خوانده می‌شود (SELECT). هیچ ستون یا جدول جدیدی برای Users
  تعریف نمی‌شود.
- تنها نوشتنی که انجام می‌شود، به‌روزرسانی ستون از پیش موجود
  Users.LastLogin است (همان ستونی که در database/migrations/001_initial_safe.sql
  ساخته شده).
- ui/login_window.py (منطق ورود دسکتاپ) عمداً دست‌نخورده باقی مانده است؛
  این فایل آن منطق را بازنویسی یا حذف نمی‌کند، فقط نسخه‌ی قابل‌استفاده‌مجدد
  همان منطق را برای وب فراهم می‌کند.
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import Database
from utils.security import verify_password

#: کلیدهایی که هرگز نباید در خروجی این سرویس (برای لایه وب) قرار بگیرند.
_SENSITIVE_USER_FIELDS = ("PasswordHash", "PasswordSalt")


def authenticate_user(username: str, password: str):
    """
    نام‌کاربری و رمز عبور را در برابر جدول Users بررسی می‌کند.

    خروجی:
        دیکشنری اطلاعات کاربر (بدون PasswordHash/PasswordSalt) در صورت
        موفقیت، یا None در صورت هر نوع شکست — کاربر یافت نشد، غیرفعال
        است، یا رمز عبور نادرست است. عمداً بین این حالت‌ها تفاوتی در
        خروجی گذاشته نمی‌شود تا اطلاعات به مهاجم لو نرود (همان رفتار
        امن ui/login_window.py).
    """
    username = (username or "").strip()
    if not username or not password:
        return None

    db = Database()
    try:
        user = db.fetch_one(
            "SELECT * FROM Users WHERE Username = ? AND IsActive = 1",
            (username,),
        )
    finally:
        db.close()

    if not user:
        return None

    if not verify_password(password, user["PasswordHash"], user["PasswordSalt"]):
        return None

    _record_login(user["ID"])

    return {k: v for k, v in user.items() if k not in _SENSITIVE_USER_FIELDS}


def _record_login(user_id: int) -> None:
    """زمان آخرین ورود موفق را در ستون موجود Users.LastLogin ثبت می‌کند."""
    db = Database()
    try:
        db.execute(
            "UPDATE Users SET LastLogin = GETDATE() WHERE ID = ?",
            (user_id,),
        )
    finally:
        db.close()
