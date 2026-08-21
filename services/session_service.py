# -*- coding: utf-8 -*-
"""
Session Service — پایه تشخیص قطع برق / بسته‌شدن غیرعادی برنامه (Phase 12)

⚠️ وضعیت: این فقط زیرساخت پایه است (Foundation)، نه یک سیستم کامل و
تست‌شده. هنوز به رویداد بسته‌شدن برنامه (main.py) و به یک Timer برای
Heartbeat دوره‌ای وصل نشده است. این کار در فاز بعدی انجام می‌شود.

جدول موردنیاز: Sessions (ساخته‌شده در database/migrations/007_session_recovery.sql)
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import Database


def start_session(user_id: int) -> int:
    """
    یک Session جدید برای این اجرای برنامه می‌سازد و شناسه آن را برمی‌گرداند.
    باید بلافاصله بعد از ورود موفق کاربر (Login) فراخوانی شود.
    """
    db = Database()
    db.execute(
        "INSERT INTO Sessions (UserRef, LoginTime, LastHeartbeat, CloseStatus) "
        "VALUES (?, GETDATE(), GETDATE(), 'ACTIVE')",
        (user_id,)
    )
    row = db.fetch_one("SELECT SCOPE_IDENTITY() AS ID")
    db.close()
    return int(row["ID"]) if row else None


def heartbeat(session_id: int) -> None:
    """
    باید هر ۶۰ ثانیه (طبق بخش ۱۵ پرامپت) از یک Timer در برنامه فراخوانی شود
    تا مشخص شود برنامه هنوز باز و در حال اجراست.
    """
    db = Database()
    db.execute(
        "UPDATE Sessions SET LastHeartbeat = GETDATE() WHERE ID = ?",
        (session_id,)
    )
    db.close()


def mark_autosave(session_id: int) -> None:
    """زمان آخرین AutoSave موفق را ثبت می‌کند."""
    db = Database()
    db.execute(
        "UPDATE Sessions SET LastAutoSave = GETDATE() WHERE ID = ?",
        (session_id,)
    )
    db.close()


def close_session_cleanly(session_id: int) -> None:
    """
    باید هنگام بسته‌شدن عادی برنامه (کاربر روی X یا خروج کلیک می‌کند)
    فراخوانی شود.
    """
    db = Database()
    db.execute(
        "UPDATE Sessions SET CloseStatus = 'CLEAN' WHERE ID = ?",
        (session_id,)
    )
    db.close()


def find_crashed_sessions(user_id: int):
    """
    Sessionهایی از این کاربر که هنوز ACTIVE مانده‌اند (یعنی هیچ‌وقت
    CLEAN نشده‌اند) را برمی‌گرداند — نشانه‌ی قطع برق یا Crash در دفعه
    اجرای قبلی.
    """
    db = Database()
    rows = db.fetch_all(
        "SELECT * FROM Sessions WHERE UserRef = ? AND CloseStatus = 'ACTIVE' "
        "ORDER BY LoginTime DESC",
        (user_id,)
    )
    db.close()
    return rows


def mark_as_crashed(session_id: int) -> None:
    """بعد از تشخیص و اطلاع‌رسانی به کاربر، وضعیت Session قدیمی را نهایی می‌کند."""
    db = Database()
    db.execute(
        "UPDATE Sessions SET CloseStatus = 'CRASHED' WHERE ID = ?",
        (session_id,)
    )
    db.close()
