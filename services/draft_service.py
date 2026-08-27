# -*- coding: utf-8 -*-
"""
Draft Service — پایه ذخیره خودکار فرم‌های نیمه‌تمام (Phase 12)

⚠️ وضعیت: زیرساخت پایه (Foundation). هنوز به هیچ فرم UI واقعی (مثل
فرم خرید یا فروش) وصل نشده است — یعنی AutoSave به‌صورت خودکار برای
فرم‌ها فعال نیست. این کار (وصل‌کردن Draft Service به هر فرم به‌صورت
جداگانه) در فاز بعدی انجام می‌شود؛ اینجا فقط API لازم آماده شده.

قانون مهم (طبق بخش ۱۰ پرامپت): Draft هرگز نباید سند حسابداری نهایی
بسازد. Draft فقط داده خام فرم را نگه می‌دارد تا در صورت قطع برق قابل
بازیابی باشد؛ ثبت نهایی (Posted) کاملاً جدا و فقط با تأیید صریح کاربر
انجام می‌شود.

جدول موردنیاز: Drafts (ساخته‌شده در database/migrations/007_session_recovery.sql)
"""

import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import Database
from services.audit_service import create_audit_entry


def save_draft(user_id: int, form_type: str, data: dict,
               session_id: int = None, entity_type: str = None,
               entity_id: int = None, draft_id: int = None) -> int:
    """
    یک Draft جدید می‌سازد یا (اگر draft_id داده شده) همان Draft را
    به‌روزرسانی می‌کند. باید هر ۶۰ ثانیه یا بعد از تغییرات مهم فرم
    (طبق بخش ۸ پرامپت) فراخوانی شود.
    """
    data_json = json.dumps(data, ensure_ascii=False)
    db = Database()
    if draft_id:
        db.execute(
            "UPDATE Drafts SET DataJson = ?, UpdatedAt = GETDATE() "
            "WHERE ID = ? AND UserRef = ? AND Status = 'ACTIVE'",
            (data_json, draft_id, user_id)
        )
        db.close()
        return draft_id
    else:
        new_id = db.execute(
            "INSERT INTO Drafts (UserRef, SessionRef, FormType, EntityType, "
            "EntityID, DataJson, Status, CreatedAt, UpdatedAt) "
            "VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', GETDATE(), GETDATE())",
            (user_id, session_id, form_type, entity_type, entity_id, data_json)
        )
        db.close()
        return int(new_id) if new_id is not None else None


def get_active_drafts(user_id: int, form_type: str = None):
    """
    Draftهای فعال (بازیابی‌نشده) یک کاربر را برمی‌گرداند. اگر form_type
    داده شود، فقط برای همان نوع فرم فیلتر می‌کند.
    باید هنگام باز شدن هر فرم، قبل از نمایش فرم خالی، فراخوانی شود تا
    مشخص شود آیا کار نیمه‌تمامی برای بازیابی وجود دارد یا نه.
    """
    db = Database()
    if form_type:
        rows = db.fetch_all(
            "SELECT * FROM Drafts WHERE UserRef = ? AND FormType = ? "
            "AND Status = 'ACTIVE' ORDER BY UpdatedAt DESC",
            (user_id, form_type)
        )
    else:
        rows = db.fetch_all(
            "SELECT * FROM Drafts WHERE UserRef = ? AND Status = 'ACTIVE' "
            "ORDER BY UpdatedAt DESC",
            (user_id,)
        )
    db.close()
    result = []
    for r in rows:
        d = dict(r)
        try:
            d["Data"] = json.loads(d["DataJson"])
        except (ValueError, TypeError):
            d["Data"] = {}
        result.append(d)
    return result


def mark_recovered(draft_id: int, user_id: int = None) -> None:
    """وقتی کاربر انتخاب می‌کند Draft را بازیابی کند."""
    db = Database()
    db.execute("UPDATE Drafts SET Status = 'RECOVERED' WHERE ID = ?", (draft_id,))
    db.close()
    create_audit_entry(user_id, "Update", "Drafts", draft_id, "Draft recovered")


def discard_draft(draft_id: int, user_id: int = None) -> None:
    """وقتی کاربر انتخاب می‌کند Draft را دور بریزد."""
    db = Database()
    db.execute("UPDATE Drafts SET Status = 'DISCARDED' WHERE ID = ?", (draft_id,))
    db.close()
    create_audit_entry(user_id, "Update", "Drafts", draft_id, "Draft discarded")


def complete_draft(draft_id: int, user_id: int = None) -> None:
    """
    باید فقط بعد از ثبت نهایی موفق (Posted) عملیات اصلی فراخوانی شود
    — یعنی Draft دیگر لازم نیست چون سند نهایی حسابداری ساخته شده.
    این تابع هرگز نباید سند حسابداری بسازد، فقط وضعیت Draft را می‌بندد.
    """
    db = Database()
    db.execute("UPDATE Drafts SET Status = 'COMPLETED' WHERE ID = ?", (draft_id,))
    db.close()
    create_audit_entry(user_id, "Update", "Drafts", draft_id, "Draft completed")
