# -*- coding: utf-8 -*-

import copy


class FakeDatabase:
    sessions = []
    drafts = []
    _next_session_id = 1
    _next_draft_id = 1

    def __init__(self):
        self._last_insert_id = None

    @classmethod
    def reset(cls):
        cls.sessions = []
        cls.drafts = []
        cls._next_session_id = 1
        cls._next_draft_id = 1

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

        raise AssertionError(f"Unsupported SQL: {sql}")

    def fetch_one(self, sql, params=()):
        normalized = " ".join(sql.split()).upper()

        if "SCOPE_IDENTITY()" in normalized:
            return {"ID": self._last_insert_id}

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

        raise AssertionError(f"Unsupported fetch_all SQL: {sql}")

    def close(self):
        pass

    @classmethod
    def _set_draft_status(cls, draft_id, status):
        for row in cls.drafts:
            if row["ID"] == draft_id:
                row["Status"] = status
