# -*- coding: utf-8 -*-
"""
سرویس تنظیمات نرم‌افزار.
سه بخش:
۱. تنظیمات عمومی (نام/آدرس/تلفن فروشگاه، موجودی منفی، درصد سود پیش‌فرض) — جدول Settings
۲. مدیریت کاربران (افزودن/ویرایش/غیرفعال‌سازی/تغییر رمز) — جدول Users
۳. دسترسی کاربران به بخش‌های نرم‌افزار — جدول UserPermissions

نکته مهم سازگاری: اگر برای یک کاربر هیچ ردیفی در UserPermissions برای یک بخش
ثبت نشده باشد، پیش‌فرض «مجاز» در نظر گرفته می‌شود — یعنی کاربرانی که از قبل
(قبل از این مرحله) ساخته شده‌اند، بدون هیچ تنظیم دستی، دقیقاً مثل قبل به همه‌ی
بخش‌ها دسترسی دارند و چیزی برایشان قفل نمی‌شود.
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import Database
from utils.security import hash_password
from services.audit_service import create_audit_entry


# =========================================================
# فهرست بخش‌های قابل‌تنظیم دسترسی (کلید، عنوان فارسی)
# این فهرست دقیقاً با دکمه‌های صفحه اصلی (ui/main_window.py) هماهنگ است.
# =========================================================
MODULE_PERMISSIONS = [
    ("ModulePersons",       "👤 اشخاص"),
    ("ModuleProducts",      "📦 کالاها"),
    ("ModulePurchases",     "🛒 خرید"),
    ("ModuleSales",         "💰 فروش"),
    ("ModuleCashBoxBank",   "💵 صندوق و بانک"),
    ("ModuleReceipts",      "⬇️ دریافت"),
    ("ModulePayments",      "⬆️ پرداخت"),
    ("ModuleCheques",       "📑 چک‌ها"),
    ("ModuleInstallments",  "📅 اقساط"),
    ("ModuleReports",       "📊 گزارش‌ها"),
    ("ModuleCommunication", "📱 ارتباط با مشتری"),
    ("ModuleImport",        "📥 Import از ربات"),
    ("ModuleBackup",        "🗄️ پشتیبان‌گیری"),
    ("ModuleAssistant",     "🤖 دستیار هوش مصنوعی"),
]


# =========================================================
# ۱. تنظیمات عمومی (کلید-مقدار ساده روی جدول Settings)
# =========================================================
def get_setting(key: str, default: str = "") -> str:
    db = Database()
    row = db.fetch_one("SELECT SettingValue FROM Settings WHERE SettingKey = ?", (key,))
    db.close()
    return row["SettingValue"] if row and row["SettingValue"] is not None else default


def set_setting(key: str, value: str, description: str = None):
    db = Database()
    existing = db.fetch_one("SELECT ID FROM Settings WHERE SettingKey = ?", (key,))
    if existing:
        db.execute("UPDATE Settings SET SettingValue = ? WHERE SettingKey = ?", (value, key))
        create_audit_entry(None, "Update", "Settings", existing["ID"], f"Updated setting: {key}")
    else:
        new_id = db.execute(
            "INSERT INTO Settings (SettingKey, SettingValue, Description) VALUES (?, ?, ?)",
            (key, value, description)
        )
        create_audit_entry(None, "Create", "Settings", new_id, f"Created setting: {key}")
    db.close()


def get_general_settings() -> dict:
    keys = ["StoreName", "StoreAddress", "StorePhone", "AllowNegativeStock", "DefaultProfitPercent"]
    return {k: get_setting(k) for k in keys}


def save_general_settings(data: dict):
    for key, value in data.items():
        set_setting(key, value)


# =========================================================
# ۲. مدیریت کاربران
# =========================================================
def list_users() -> list:
    db = Database()
    rows = db.fetch_all(
        "SELECT ID, Username, FullName, IsAdmin, IsActive, CreatedAt, LastLogin "
        "FROM Users ORDER BY IsActive DESC, FullName"
    )
    db.close()
    return rows


def username_exists(username: str, exclude_user_id: int = None) -> bool:
    db = Database()
    if exclude_user_id:
        row = db.fetch_one(
            "SELECT ID FROM Users WHERE Username = ? AND ID <> ?", (username, exclude_user_id)
        )
    else:
        row = db.fetch_one("SELECT ID FROM Users WHERE Username = ?", (username,))
    db.close()
    return row is not None


def create_user(username: str, full_name: str, password: str, is_admin: bool, actor_user_id: int = None) -> int:
    if username_exists(username):
        raise ValueError("این نام کاربری قبلاً استفاده شده است.")
    hashed, salt = hash_password(password)
    db = Database()
    new_id = db.execute(
        """INSERT INTO Users (Username, PasswordHash, PasswordSalt, FullName, IsAdmin, IsActive)
           VALUES (?, ?, ?, ?, ?, 1)""",
        (username, hashed, salt, full_name, 1 if is_admin else 0)
    )
    db.close()

    create_audit_entry(
        actor_user_id,
        "Create",
        "Users",
        new_id,
        f"Created user: {username}"
    )

    return new_id


def update_user(user_id: int, full_name: str, is_admin: bool, is_active: bool, actor_user_id: int = None):
    db = Database()
    db.execute(
        "UPDATE Users SET FullName = ?, IsAdmin = ?, IsActive = ? WHERE ID = ?",
        (full_name, 1 if is_admin else 0, 1 if is_active else 0, user_id)
    )
    db.close()


    create_audit_entry(actor_user_id, "Update", "Users", user_id, f"Updated user: {full_name}")
def reset_user_password(user_id: int, new_password: str):
    hashed, salt = hash_password(new_password)
    db = Database()
    db.execute(
        "UPDATE Users SET PasswordHash = ?, PasswordSalt = ? WHERE ID = ?",
        (hashed, salt, user_id)
    )
    db.close()


# =========================================================
# ۳. دسترسی کاربران به بخش‌های نرم‌افزار
# =========================================================
def get_user_permissions(user_id: int) -> dict:
    """برمی‌گرداند: {PermissionKey: True/False} فقط برای کلیدهایی که صراحتاً ثبت شده‌اند."""
    db = Database()
    rows = db.fetch_all(
        "SELECT PermissionKey, IsAllowed FROM UserPermissions WHERE UserRef = ?", (user_id,)
    )
    db.close()
    return {r["PermissionKey"]: bool(r["IsAllowed"]) for r in rows}


def save_user_permissions(user_id: int, permissions: dict, actor_user_id: int = None):
    """permissions: {PermissionKey: True/False} — برای همه کلیدهای MODULE_PERMISSIONS ذخیره می‌شود."""
    db = Database()
    for key, allowed in permissions.items():
        existing = db.fetch_one(
            "SELECT ID FROM UserPermissions WHERE UserRef = ? AND PermissionKey = ?",
            (user_id, key)
        )
        if existing:
            db.execute(
                "UPDATE UserPermissions SET IsAllowed = ? WHERE ID = ?",
                (1 if allowed else 0, existing["ID"])
            )
        else:
            db.execute(
                "INSERT INTO UserPermissions (UserRef, PermissionKey, IsAllowed) VALUES (?, ?, ?)",
                (user_id, key, 1 if allowed else 0)
            )
    db.close()
    create_audit_entry(actor_user_id, "Update", "UserPermissions", user_id, f"Updated permissions for user {user_id}")


def is_module_allowed(user: dict, module_key: str) -> bool:
    """
    آیا کاربر داده‌شده به این بخش دسترسی دارد؟
    - مدیر (IsAdmin=1) همیشه به همه‌چیز دسترسی دارد.
    - اگر برای کاربر هیچ تنظیمی برای این کلید ثبت نشده باشد -> پیش‌فرض مجاز (سازگاری با نسخه‌های قبلی).
    - اگر صراحتاً IsAllowed=0 ثبت شده باشد -> غیرمجاز.
    """
    if user.get("IsAdmin"):
        return True
    db = Database()
    row = db.fetch_one(
        "SELECT IsAllowed FROM UserPermissions WHERE UserRef = ? AND PermissionKey = ?",
        (user["ID"], module_key)
    )
    db.close()
    if row is None:
        return True
    return bool(row["IsAllowed"])
