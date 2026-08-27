# -*- coding: utf-8 -*-
"""
Phase 15.1 — Accounting Core Foundation

این تست‌ها دو بخش دارند:
1. تست خالص Python برای _validate_journal_lines (بدون نیاز به دیتابیس) —
   قوانین اصلی موازنه سند حسابداری را پوشش می‌دهد.
2. تست post_journal_entry با یک Fake Connection/Cursor سبک که رفتار
   Cursor واقعی pyodbc را برای این چند Query خاص شبیه‌سازی می‌کند (چون
   accounting_service، مثل بقیه سرویس‌های مالی پروژه، از الگوی
   conn.cursor() + commit/rollback دستی استفاده می‌کند، نه db.execute()
   ساده).
"""

import pytest

import services.accounting_service as accounting_service
from services.accounting_service import AccountingError, _validate_journal_lines


# =========================================================
# بخش ۱ — اعتبارسنجی خالص (بدون دیتابیس)
# =========================================================

def test_validate_journal_lines_balanced_ok():
    lines = [
        {"account_code": "1000", "debit": 100},
        {"account_code": "4000", "credit": 100},
    ]
    total = _validate_journal_lines(lines)
    assert total == 100


def test_validate_journal_lines_requires_at_least_two_lines():
    with pytest.raises(AccountingError):
        _validate_journal_lines([{"account_code": "1000", "debit": 100}])


def test_validate_journal_lines_rejects_unbalanced():
    lines = [
        {"account_code": "1000", "debit": 100},
        {"account_code": "4000", "credit": 90},
    ]
    with pytest.raises(AccountingError):
        _validate_journal_lines(lines)


def test_validate_journal_lines_rejects_both_debit_and_credit_on_one_line():
    lines = [
        {"account_code": "1000", "debit": 100, "credit": 50},
        {"account_code": "4000", "credit": 50},
    ]
    with pytest.raises(AccountingError):
        _validate_journal_lines(lines)


def test_validate_journal_lines_rejects_zero_line():
    lines = [
        {"account_code": "1000", "debit": 0, "credit": 0},
        {"account_code": "4000", "credit": 100},
    ]
    with pytest.raises(AccountingError):
        _validate_journal_lines(lines)


def test_validate_journal_lines_rejects_negative_amounts():
    lines = [
        {"account_code": "1000", "debit": -10},
        {"account_code": "4000", "credit": 10},
    ]
    with pytest.raises(AccountingError):
        _validate_journal_lines(lines)


def test_validate_journal_lines_requires_account_reference():
    lines = [
        {"debit": 100},
        {"account_code": "4000", "credit": 100},
    ]
    with pytest.raises(AccountingError):
        _validate_journal_lines(lines)


def test_validate_journal_lines_allows_multi_line_balanced_entry():
    # یک فروش نقدی ساده با تخصیص به دو حساب بستانکار (مثلاً درآمد + مالیات)
    lines = [
        {"account_code": "1000", "debit": 220},
        {"account_code": "4000", "credit": 200},
        {"account_code": "2200", "credit": 20},
    ]
    total = _validate_journal_lines(lines)
    assert total == 220


def test_validate_journal_lines_tolerates_tiny_rounding_error():
    lines = [
        {"account_code": "1000", "debit": 100.001},
        {"account_code": "4000", "credit": 100.0},
    ]
    # نباید Exception بدهد چون اختلاف زیر BALANCE_TOLERANCE است
    _validate_journal_lines(lines)


# =========================================================
# بخش ۲ — post_journal_entry با Fake DB سبک (Cursor-Based)
# =========================================================

class _FakeCursor:
    def __init__(self, state):
        self.state = state
        self._last_result = None

    def execute(self, sql, params=()):
        normalized = " ".join(sql.split()).upper()
        state = self.state

        if normalized.startswith("SELECT ISNULL(MAX(ENTRYNUMBER)"):
            next_num = (max((e["EntryNumber"] for e in state["entries"]), default=0)) + 1
            self._last_result = (next_num,)
            return

        if normalized.startswith("INSERT INTO JOURNALENTRIES"):
            entry_number, shamsi_date, description, source_table, source_id, correlation_id, user_ref = params
            new_id = len(state["entries"]) + 1
            state["entries"].append({
                "ID": new_id, "EntryNumber": entry_number, "ShamsiDate": shamsi_date,
                "Description": description, "SourceTable": source_table, "SourceID": source_id,
                "CorrelationID": correlation_id, "UserRef": user_ref,
            })
            state["last_id"] = new_id
            self._last_result = None
            return

        if normalized == "SELECT @@IDENTITY AS ID":
            self._last_result = (state["last_id"],)
            return

        if normalized.startswith("SELECT ID, ISACTIVE FROM CHARTOFACCOUNTS WHERE CODE = ?"):
            code = params[0]
            acct = next((a for a in state["accounts"] if a["Code"] == code), None)
            self._last_result = (acct["ID"], acct["IsActive"]) if acct else None
            return

        if normalized.startswith("SELECT ID, ISACTIVE FROM CHARTOFACCOUNTS WHERE ID = ?"):
            account_id = params[0]
            acct = next((a for a in state["accounts"] if a["ID"] == account_id), None)
            self._last_result = (acct["ID"], acct["IsActive"]) if acct else None
            return

        if normalized.startswith("INSERT INTO JOURNALENTRYLINES"):
            journal_entry_ref, account_ref, debit, credit, description = params
            state["lines"].append({
                "JournalEntryRef": journal_entry_ref, "AccountRef": account_ref,
                "Debit": debit, "Credit": credit, "Description": description,
            })
            self._last_result = None
            return

        raise AssertionError(f"Unsupported SQL in fake cursor: {sql}")

    def fetchone(self):
        return self._last_result

    def close(self):
        pass


class _FakeConnection:
    """
    برای شبیه‌سازی رفتار Rollback واقعی pyodbc (که تغییرات نیمه‌کاره را
    واقعاً پاک می‌کند)، از یک Snapshot ساده در لحظه connect() استفاده
    می‌شود و rollback() آن را برمی‌گرداند.
    """

    def __init__(self, state):
        self.state = state
        self._snapshot = {
            "entries": list(state["entries"]),
            "lines": list(state["lines"]),
            "last_id": state["last_id"],
        }
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        return _FakeCursor(self.state)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True
        self.state["entries"][:] = self._snapshot["entries"]
        self.state["lines"][:] = self._snapshot["lines"]
        self.state["last_id"] = self._snapshot["last_id"]


class _FakeDatabase:
    """جایگزین سبک services.accounting_service.Database برای این تست‌ها."""

    _shared_state = None

    def __init__(self):
        self._conn = None

    def connect(self):
        self._conn = _FakeConnection(self.__class__._shared_state)
        return self._conn

    def close(self):
        pass

    def execute(self, query, params=()):
        # استفاده‌شده توسط create_audit_entry (خارج از این تست‌ها Mock نشده،
        # پس فقط باید بدون Exception عبور کند)
        return None

    def fetch_all(self, query, params=()):
        return []

    def fetch_one(self, query, params=()):
        return None

    @classmethod
    def reset(cls, accounts):
        cls._shared_state = {"accounts": accounts, "entries": [], "lines": [], "last_id": None}


def setup_function():
    accounts = [
        {"ID": 1, "Code": "1000", "Name": "صندوق و بانک", "IsActive": True},
        {"ID": 2, "Code": "4000", "Name": "درآمد فروش", "IsActive": True},
        {"ID": 3, "Code": "9999", "Name": "غیرفعال", "IsActive": False},
    ]
    _FakeDatabase.reset(accounts)
    accounting_service.Database = _FakeDatabase
    # audit_service هم از همان Database الگو می‌گیرد؛ create_audit_entry با
    # execute() ساده کار می‌کند که در _FakeDatabase بی‌خطر است.
    import services.audit_service as audit_service
    audit_service.Database = _FakeDatabase


def test_post_journal_entry_happy_path():
    entry_id, entry_number = accounting_service.post_journal_entry(
        shamsi_date="1404-06-01",
        description="فروش نقدی تستی",
        lines=[
            {"account_code": "1000", "debit": 500},
            {"account_code": "4000", "credit": 500},
        ],
        user_id=1,
    )

    state = _FakeDatabase._shared_state
    assert entry_id == 1
    assert entry_number == 1
    assert len(state["entries"]) == 1
    assert len(state["lines"]) == 2
    assert state["lines"][0]["Debit"] == 500
    assert state["lines"][1]["Credit"] == 500


def test_post_journal_entry_rejects_unknown_account_code():
    with pytest.raises(AccountingError):
        accounting_service.post_journal_entry(
            shamsi_date="1404-06-01",
            description="حساب نامعتبر",
            lines=[
                {"account_code": "1000", "debit": 100},
                {"account_code": "7777", "credit": 100},
            ],
            user_id=1,
        )
    # هیچ سند/ردیفی نباید ذخیره مانده باشد چون Rollback شده
    state = _FakeDatabase._shared_state
    assert len(state["entries"]) == 0
    assert len(state["lines"]) == 0


def test_post_journal_entry_rejects_inactive_account():
    with pytest.raises(AccountingError):
        accounting_service.post_journal_entry(
            shamsi_date="1404-06-01",
            description="حساب غیرفعال",
            lines=[
                {"account_code": "1000", "debit": 100},
                {"account_code": "9999", "credit": 100},
            ],
            user_id=1,
        )
    state = _FakeDatabase._shared_state
    assert len(state["entries"]) == 0


def test_post_journal_entry_rejects_unbalanced_before_touching_db():
    with pytest.raises(AccountingError):
        accounting_service.post_journal_entry(
            shamsi_date="1404-06-01",
            description="موازنه ندارد",
            lines=[
                {"account_code": "1000", "debit": 100},
                {"account_code": "4000", "credit": 90},
            ],
            user_id=1,
        )
    # اعتبارسنجی باید قبل از هر Query به دیتابیس رد شود
    state = _FakeDatabase._shared_state
    assert len(state["entries"]) == 0


def test_post_journal_entry_increments_entry_number():
    accounting_service.post_journal_entry(
        "1404-06-01", "سند اول",
        [{"account_code": "1000", "debit": 100}, {"account_code": "4000", "credit": 100}],
        user_id=1,
    )
    _, second_number = accounting_service.post_journal_entry(
        "1404-06-02", "سند دوم",
        [{"account_code": "1000", "debit": 50}, {"account_code": "4000", "credit": 50}],
        user_id=1,
    )
    assert second_number == 2
