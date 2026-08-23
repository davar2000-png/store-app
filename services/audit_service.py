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
