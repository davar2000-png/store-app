import logging
from datetime import datetime
import uuid

from database.db import Database

logger = logging.getLogger(__name__)


def create_audit_entry(user_id, action_type, table_name, record_id=None, details=None):
    """
    یک رکورد Audit ثبت می‌کند و دیکشنری همان رکورد را برمی‌گرداند.

    طراحی عمدی: خطای نوشتن Audit هرگز عملیات اصلی تجاری (فروش/خرید/تسویه) را
    متوقف یا Rollback نمی‌کند (چون این تابع فقط Best-Effort Logging است، نه
    بخشی از Transaction حسابداری). اما برخلاف نسخه قبلی، خطا دیگر کاملاً
    بی‌صدا بلعیده نمی‌شود — با logger.error ثبت می‌شود تا یک شکست خاموش در
    زنجیره Audit (که مستقیماً روی صحت گزارش‌های امنیتی/حسابداری اثر می‌گذارد)
    قابل ردیابی باشد. فراخوان می‌تواند با بررسی audit_write_failed در مقدار
    بازگشتی متوجه شکست شود.
    """
    correlation_id = str(uuid.uuid4())
    action_date = datetime.now()
    audit_write_failed = False

    try:
        db = Database()
        try:
            db.execute(
                """
                INSERT INTO AuditLogs
                (UserRef, ActionType, TableName, RecordID, Details, ActionDate, CorrelationID)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    action_type,
                    table_name,
                    record_id,
                    details,
                    action_date,
                    correlation_id
                )
            )
        finally:
            db.close()
    except Exception:
        audit_write_failed = True
        logger.error(
            "Audit write failed: user=%s action=%s table=%s record=%s correlation=%s",
            user_id, action_type, table_name, record_id, correlation_id,
            exc_info=True,
        )

    return {
        "UserRef": user_id,
        "ActionType": action_type,
        "TableName": table_name,
        "RecordID": record_id,
        "Details": details,
        "ActionDate": action_date,
        "CorrelationID": correlation_id,
        "audit_write_failed": audit_write_failed,
    }


def log_action(user_id, action_type, table_name, record_id=None, details=None):
    return create_audit_entry(
        user_id,
        action_type,
        table_name,
        record_id,
        details
    )


def get_recent_logs(user_id=None, action_type=None, table_name=None,
                     date_from=None, date_to=None, limit=200):
    """
    گزارش رویدادها را با فیلترهای اختیاری برمی‌گرداند.
    فیلترها فقط در صورتی اعمال می‌شوند که مقدار داده شده باشند (AND ترکیب می‌شوند).
    نتایج بر اساس ActionDate نزولی مرتب می‌شوند (جدیدترین اول).
    """
    conditions = []
    params = []

    if user_id is not None:
        conditions.append("UserRef = ?")
        params.append(user_id)
    if action_type:
        conditions.append("ActionType = ?")
        params.append(action_type)
    if table_name:
        conditions.append("TableName = ?")
        params.append(table_name)
    if date_from is not None:
        conditions.append("ActionDate >= ?")
        params.append(date_from)
    if date_to is not None:
        conditions.append("ActionDate <= ?")
        params.append(date_to)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"""
        SELECT TOP {int(limit)} UserRef, ActionType, TableName, RecordID,
               Details, ActionDate, CorrelationID
        FROM AuditLogs
        {where_clause}
        ORDER BY ActionDate DESC
    """

    db = Database()
    rows = db.fetch_all(query, tuple(params))
    db.close()
    return rows
