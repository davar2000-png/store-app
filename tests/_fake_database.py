# -*- coding: utf-8 -*-

import copy


class FakeDatabase:
    sessions = []
    drafts = []
    audit_logs = []
    _next_session_id = 1
    _next_draft_id = 1
    _next_audit_id = 1

    #: وقتی True باشد، execute برای INSERT INTO AuditLogs یک خطا شبیه‌سازی
    #: می‌کند تا رفتار create_audit_entry در برابر شکست DB تست شود.
    fail_audit_insert = False

    #: (Phase 16C) داده‌های ساختگی Users — تست‌ها این لیست را مستقیماً پر
    #: می‌کنند؛ این FakeDatabase هیچ کاربری را از پیش Seed نمی‌کند.
    users = []

    #: (Phase 16C) Session های وب — کاملاً مستقل از self.sessions (که
    #: مربوط به بازیابی بعد از قطع برق در دسکتاپ است).
    web_sessions = []
    _next_web_session_id = 1

    def __init__(self):
        self._last_insert_id = None

    @classmethod
    def reset(cls):
        cls.sessions = []
        cls.drafts = []
        cls.audit_logs = []
        cls._next_session_id = 1
        cls._next_draft_id = 1
        cls._next_audit_id = 1
        cls.fail_audit_insert = False
        cls.users = []
        cls.web_sessions = []
        cls._next_web_session_id = 1

    def execute(self, sql, params=()):
        normalized = " ".join(sql.split()).upper()

        if normalized.startswith("INSERT INTO SESSIONS"):
            user_id = params[0]
            row = {
                "ID": self.__class__._next_session_id,
                "UserRef": user_id,
                "LoginTime": "NOW",
                "LastHeartbeat": "NOW",
                "LastAutoSave": None,
                "CloseStatus": "ACTIVE",
            }
            self.__class__.sessions.append(row)
            self.__class__._next_session_id += 1
            self._last_insert_id = row["ID"]
            return self._last_insert_id

        if normalized.startswith("UPDATE SESSIONS SET LASTHEARTBEAT"):
            session_id = params[0]
            for row in self.__class__.sessions:
                if row["ID"] == session_id:
                    row["LastHeartbeat"] = "NOW"
            return

        if normalized.startswith("UPDATE SESSIONS SET LASTAUTOSAVE"):
            session_id = params[0]
            for row in self.__class__.sessions:
                if row["ID"] == session_id:
                    row["LastAutoSave"] = "NOW"
            return

        if normalized.startswith("UPDATE SESSIONS SET CLOSESTATUS = 'CLEAN'"):
            session_id = params[0]
            for row in self.__class__.sessions:
                if row["ID"] == session_id:
                    row["CloseStatus"] = "CLEAN"
            return

        if normalized.startswith("UPDATE SESSIONS SET CLOSESTATUS = 'CRASHED'"):
            session_id = params[0]
            for row in self.__class__.sessions:
                if row["ID"] == session_id:
                    row["CloseStatus"] = "CRASHED"
            return

        if normalized.startswith("INSERT INTO DRAFTS"):
            (
                user_id,
                session_id,
                form_type,
                entity_type,
                entity_id,
                data_json,
            ) = params

            row = {
                "ID": self.__class__._next_draft_id,
                "UserRef": user_id,
                "SessionRef": session_id,
                "FormType": form_type,
                "EntityType": entity_type,
                "EntityID": entity_id,
                "DataJson": data_json,
                "Status": "ACTIVE",
                "CreatedAt": "NOW",
                "UpdatedAt": "NOW",
            }
            self.__class__.drafts.append(row)
            self.__class__._next_draft_id += 1
            self._last_insert_id = row["ID"]
            return self._last_insert_id

        if normalized.startswith("UPDATE DRAFTS SET DATAJSON"):
            data_json, draft_id, user_id = params
            for row in self.__class__.drafts:
                if (
                    row["ID"] == draft_id
                    and row["UserRef"] == user_id
                    and row["Status"] == "ACTIVE"
                ):
                    row["DataJson"] = data_json
                    row["UpdatedAt"] = "NOW"
            return

        if normalized.startswith("UPDATE DRAFTS SET STATUS = 'RECOVERED'"):
            self._set_draft_status(params[0], "RECOVERED")
            return

        if normalized.startswith("UPDATE DRAFTS SET STATUS = 'DISCARDED'"):
            self._set_draft_status(params[0], "DISCARDED")
            return

        if normalized.startswith("UPDATE DRAFTS SET STATUS = 'COMPLETED'"):
            self._set_draft_status(params[0], "COMPLETED")
            return

        if normalized.startswith("INSERT INTO AUDITLOGS"):
            if self.__class__.fail_audit_insert:
                raise RuntimeError("simulated AuditLogs insert failure")

            (
                user_ref, action_type, table_name, record_id,
                details, action_date, correlation_id,
            ) = params
            row = {
                "ID": self.__class__._next_audit_id,
                "UserRef": user_ref,
                "ActionType": action_type,
                "TableName": table_name,
                "RecordID": record_id,
                "Details": details,
                "ActionDate": action_date,
                "CorrelationID": correlation_id,
            }
            self.__class__.audit_logs.append(row)
            self.__class__._next_audit_id += 1
            self._last_insert_id = row["ID"]
            return self._last_insert_id

        if normalized.startswith("UPDATE USERS SET LASTLOGIN"):
            user_id = params[0]
            for row in self.__class__.users:
                if row["ID"] == user_id:
                    row["LastLogin"] = "NOW"
            return

        if normalized.startswith("INSERT INTO WEBSESSIONS"):
            token_hash, user_id, expires_at, user_agent, ip_address = params
            row = {
                "ID": self.__class__._next_web_session_id,
                "TokenHash": token_hash,
                "UserRef": user_id,
                "CreatedAt": "NOW",
                "ExpiresAt": expires_at,
                "LastActivity": "NOW",
                "IsRevoked": False,
                "UserAgent": user_agent,
                "IPAddress": ip_address,
            }
            self.__class__.web_sessions.append(row)
            self.__class__._next_web_session_id += 1
            self._last_insert_id = row["ID"]
            return self._last_insert_id

        if normalized.startswith("UPDATE WEBSESSIONS SET LASTACTIVITY"):
            session_id = params[0]
            for row in self.__class__.web_sessions:
                if row["ID"] == session_id:
                    row["LastActivity"] = "NOW"
            return

        if normalized.startswith("UPDATE WEBSESSIONS SET ISREVOKED"):
            token_hash = params[0]
            for row in self.__class__.web_sessions:
                if row["TokenHash"] == token_hash:
                    row["IsRevoked"] = True
            return

        raise AssertionError(f"Unsupported SQL: {sql}")

    def fetch_one(self, sql, params=()):
        normalized = " ".join(sql.split()).upper()

        if "SCOPE_IDENTITY()" in normalized:
            return {"ID": self._last_insert_id}

        if "FROM USERS WHERE USERNAME" in normalized:
            username = params[0]
            for row in self.__class__.users:
                if row["Username"] == username and row.get("IsActive", True):
                    return copy.deepcopy(row)
            return None

        if "FROM WEBSESSIONS WHERE TOKENHASH" in normalized:
            token_hash = params[0]
            for row in self.__class__.web_sessions:
                if row["TokenHash"] == token_hash:
                    return copy.deepcopy(row)
            return None

        raise AssertionError(f"Unsupported fetch_one SQL: {sql}")

    def fetch_all(self, sql, params=()):
        normalized = " ".join(sql.split()).upper()

        if "FROM SESSIONS" in normalized:
            user_id = params[0]
            rows = [
                copy.deepcopy(row)
                for row in self.__class__.sessions
                if row["UserRef"] == user_id
                and row["CloseStatus"] == "ACTIVE"
            ]
            rows.sort(key=lambda row: row["ID"], reverse=True)
            return rows

        if "FROM DRAFTS" in normalized:
            if "FORMTYPE = ?" in normalized:
                user_id, form_type = params
                rows = [
                    copy.deepcopy(row)
                    for row in self.__class__.drafts
                    if row["UserRef"] == user_id
                    and row["FormType"] == form_type
                    and row["Status"] == "ACTIVE"
                ]
            else:
                user_id = params[0]
                rows = [
                    copy.deepcopy(row)
                    for row in self.__class__.drafts
                    if row["UserRef"] == user_id
                    and row["Status"] == "ACTIVE"
                ]

            rows.sort(key=lambda row: row["ID"], reverse=True)
            return rows

        if "FROM AUDITLOGS" in normalized:
            rows = [copy.deepcopy(row) for row in self.__class__.audit_logs]
            rows.sort(key=lambda row: row["ID"], reverse=True)
            return rows

        raise AssertionError(f"Unsupported fetch_all SQL: {sql}")

    def close(self):
        pass

    @classmethod
    def _set_draft_status(cls, draft_id, status):
        for row in cls.drafts:
            if row["ID"] == draft_id:
                row["Status"] = status
