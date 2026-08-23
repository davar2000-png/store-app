from datetime import datetime
import uuid


def create_correlation_id():
    return str(uuid.uuid4())


def create_audit_entry(user_id, action_type, table_name, record_id=None, details=None):
    return {
        "UserRef": user_id,
        "ActionType": action_type,
        "TableName": table_name,
        "RecordID": record_id,
        "Details": details,
        "ActionDate": datetime.now(),
        "CorrelationID": create_correlation_id()
    }
