from datetime import datetime
import uuid


def create_audit_entry(user_id, action_type, table_name, record_id=None, details=None):
    return {
        "UserRef": user_id,
        "ActionType": action_type,
        "TableName": table_name,
        "RecordID": record_id,
        "Details": details,
        "ActionDate": datetime.now(),
        "CorrelationID": str(uuid.uuid4())
    }


def log_action(user_id, action_type, table_name, record_id=None, details=None):
    return create_audit_entry(
        user_id,
        action_type,
        table_name,
        record_id,
        details
    )
