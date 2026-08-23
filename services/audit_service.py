from datetime import datetime
import uuid

from database.db import Database


def create_audit_entry(user_id, action_type, table_name, record_id=None, details=None):
    correlation_id = str(uuid.uuid4())

    try:
        db = Database()
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
                datetime.now(),
                correlation_id
            )
        )
        db.close()
    except Exception:
        pass

    return {
        "UserRef": user_id,
        "ActionType": action_type,
        "TableName": table_name,
        "RecordID": record_id,
        "Details": details,
        "ActionDate": datetime.now(),
        "CorrelationID": correlation_id
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
