# -*- coding: utf-8 -*-
"""
Phase 15.4 — اتصال دریافت وجه (Receipt) به حسابداری دوطرفه

این ماژول قبل از این فاز **هیچ تست**ی نداشت. طبق همان قانون Brief که در
Phase 15.2/15.3 دنبال شد («قبل از تغییر سرویس، تست‌های Regression لازم را
اضافه کن»)، این فایل دو دسته تست دارد:

۱) Regression — رفتار **فعلی** create_receipt() (اعتبارسنجی، صندوق/بانک،
   چک InHand، تخصیص، بروزرسانی PaidAmount فاکتور، Rollback کامل در صورت
   خطا) که باید دقیقاً همان‌طور که قبل از این فاز کار می‌کرد، ادامه یابد.
   اتصال Ledger نباید هیچ‌کدام از این‌ها را بشکند.
۲) اتصال Ledger — سند حسابداری دوطرفه‌ای که حالا برای هر سند دریافت در
   همان Transaction اتمیک ساخته می‌شود، طبق تصمیم صریح Option F.2:
   دریافت‌های Partially Allocated رد نمی‌شوند و مانده تخصیص‌نیافته به
   حساب 2300 (پیش‌دریافت مشتری) بستانکار می‌شود، نه 1100.

از یک Fake Cursor/Connection سبک استفاده می‌شود، دقیقاً هم‌الگو با
`tests/test_sales_service.py` و `tests/test_inventory_service.py`: رفتار
Cursor واقعی pyodbc را برای دقیقاً همان Queryهایی که
`financial_service.create_receipt` و
`accounting_service._post_journal_entry_on_cursor` صادر می‌کنند شبیه‌سازی
می‌کند و از یک Snapshot برای Rollback واقعی استفاده می‌کند.
"""

import copy

import pytest

import services.financial_service as financial_service
from services.financial_service import FinancialError, _build_receipt_journal_lines
from services.accounting_service import AccountingError


# =========================================================
# Fake DB — Cursor-Based (هم‌الگو با test_sales_service.py)
# =========================================================

class _FakeCursor:
    def __init__(self, state):
        self.state = state
        self._last_result = None
        self._last_fetchall = None

    def execute(self, sql, params=()):
        normalized = " ".join(sql.split()).upper()
        state = self.state

        if normalized.startswith("SELECT ISNULL(MAX(RECEIPTNUMBER), 4000)"):
            next_num = max((r["ReceiptNumber"] for r in state["receipts"]), default=4000) + 1
            self._last_result = (next_num,)
            return

        if normalized.startswith("INSERT INTO RECEIPTS "):
            receipt_number, person_ref, shamsi_date, total_amount, description, user_ref = params
            new_id = state["_next_receipt_id"]
            state["_next_receipt_id"] += 1
            state["receipts"].append({
                "ID": new_id, "ReceiptNumber": receipt_number, "PersonRef": person_ref,
                "ShamsiDate": shamsi_date, "TotalAmount": total_amount,
                "Description": description, "UserRef": user_ref,
            })
            state["_last_identity"] = new_id
            self._last_result = None
            return

        if normalized == "SELECT @@IDENTITY AS ID":
            self._last_result = (state["_last_identity"],)
            return

        if normalized.startswith("SELECT CURRENTBALANCE FROM CASHBOXES WHERE ID = ?"):
            cash_box_id = params[0]
            self._last_result = (state["cash_boxes"][cash_box_id]["CurrentBalance"],)
            return

        if normalized.startswith("UPDATE CASHBOXES SET CURRENTBALANCE = ? WHERE ID = ?"):
            balance, cash_box_id = params
            state["cash_boxes"][cash_box_id]["CurrentBalance"] = balance
            return

        if normalized.startswith("INSERT INTO CASHBOXTRANSACTIONS"):
            (cash_box_ref, amount, balance_after, ref_id, shamsi_date,
             description, user_ref) = params
            state["cash_box_transactions"].append({
                "CashBoxRef": cash_box_ref, "Amount": amount, "BalanceAfter": balance_after,
                "RefID": ref_id, "ShamsiDate": shamsi_date, "Description": description,
                "UserRef": user_ref,
            })
            self._last_result = None
            return

        if normalized.startswith("SELECT CURRENTBALANCE FROM BANKACCOUNTS WHERE ID = ?"):
            bank_account_id = params[0]
            self._last_result = (state["bank_accounts"][bank_account_id]["CurrentBalance"],)
            return

        if normalized.startswith("UPDATE BANKACCOUNTS SET CURRENTBALANCE = ? WHERE ID = ?"):
            balance, bank_account_id = params
            state["bank_accounts"][bank_account_id]["CurrentBalance"] = balance
            return

        if normalized.startswith("INSERT INTO BANKTRANSACTIONS"):
            (bank_account_ref, amount, balance_after, ref_id, shamsi_date,
             description, user_ref) = params
            state["bank_transactions"].append({
                "BankAccountRef": bank_account_ref, "Amount": amount, "BalanceAfter": balance_after,
                "RefID": ref_id, "ShamsiDate": shamsi_date, "Description": description,
                "UserRef": user_ref,
            })
            self._last_result = None
            return

        if normalized.startswith("INSERT INTO CHEQUES"):
            (cheque_type, number, sayad, bank, person_ref, amount, shamsi_date,
             due_date, ref_table, description, user_ref) = params
            new_id = state["_next_cheque_id"]
            state["_next_cheque_id"] += 1
            state["cheques"].append({
                "ID": new_id, "ChequeType": cheque_type, "ChequeNumber": number,
                "SayadNumber": sayad, "BankName": bank, "PersonRef": person_ref,
                "Amount": amount, "ShamsiDate": shamsi_date, "DueShamsiDate": due_date,
                "Status": "InHand", "RefTable": ref_table, "RefID": None,
                "Description": description, "UserRef": user_ref,
            })
            state["_last_identity"] = new_id
            self._last_result = None
            return

        if normalized.startswith("UPDATE CHEQUES SET REFID = ? WHERE ID = ?"):
            ref_id, cheque_id = params
            for c in state["cheques"]:
                if c["ID"] == cheque_id:
                    c["RefID"] = ref_id
            return

        if normalized.startswith("INSERT INTO RECEIPTLINES"):
            receipt_ref, method_type, cash_box_ref, bank_account_ref, cheque_ref, amount = params
            state["receipt_lines"].append({
                "ReceiptRef": receipt_ref, "MethodType": method_type, "CashBoxRef": cash_box_ref,
                "BankAccountRef": bank_account_ref, "ChequeRef": cheque_ref, "Amount": amount,
            })
            self._last_result = None
            return

        if normalized.startswith("INSERT INTO RECEIPTALLOCATIONS"):
            receipt_ref, invoice_ref, amount = params
            state["receipt_allocations"].append({
                "ReceiptRef": receipt_ref, "SalesInvoiceRef": invoice_ref, "Amount": amount,
            })
            self._last_result = None
            return

        if normalized.startswith("UPDATE SALESINVOICES SET PAIDAMOUNT = PAIDAMOUNT + ? WHERE ID = ?"):
            amount, invoice_id = params
            state["sales_invoices"][invoice_id]["PaidAmount"] += amount
            return

        # --- هسته accounting_service._post_journal_entry_on_cursor ---
        if normalized.startswith("SELECT ISNULL(MAX(ENTRYNUMBER)"):
            next_num = max((e["EntryNumber"] for e in state["journal_entries"]), default=0) + 1
            self._last_result = (next_num,)
            return

        if normalized.startswith("INSERT INTO JOURNALENTRIES"):
            (entry_number, shamsi_date, description, source_table, source_id,
             correlation_id, user_ref) = params
            new_id = state["_next_journal_id"]
            state["_next_journal_id"] += 1
            state["journal_entries"].append({
                "ID": new_id, "EntryNumber": entry_number, "ShamsiDate": shamsi_date,
                "Description": description, "SourceTable": source_table, "SourceID": source_id,
                "CorrelationID": correlation_id, "UserRef": user_ref,
            })
            state["_last_identity"] = new_id
            self._last_result = None
            return

        if normalized.startswith("SELECT ID, ISACTIVE FROM CHARTOFACCOUNTS WHERE CODE = ?"):
            code = params[0]
            acct = next((a for a in state["accounts"] if a["Code"] == code), None)
            self._last_result = (acct["ID"], acct["IsActive"]) if acct else None
            return

        if normalized.startswith("INSERT INTO JOURNALENTRYLINES"):
            journal_entry_ref, account_ref, debit, credit, description = params
            state["journal_lines"].append({
                "JournalEntryRef": journal_entry_ref, "AccountRef": account_ref,
                "Debit": debit, "Credit": credit, "Description": description,
            })
            self._last_result = None
            return

        raise AssertionError(f"Unsupported SQL in fake cursor: {sql}")

    def fetchone(self):
        return self._last_result

    def fetchall(self):
        return self._last_fetchall if self._last_fetchall is not None else []

    def close(self):
        pass


class _FakeConnection:
    """Snapshot در connect() و بازگردانی کامل آن در rollback() — دقیقاً مثل
    رفتار واقعی pyodbc که تغییرات نیمه‌کاره یک Transaction را پاک می‌کند."""

    def __init__(self, state):
        self.state = state
        self._snapshot = copy.deepcopy(state)
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        return _FakeCursor(self.state)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True
        snap = copy.deepcopy(self._snapshot)
        for key, value in snap.items():
            if isinstance(value, list):
                self.state[key][:] = value
            elif isinstance(value, dict):
                self.state[key].clear()
                self.state[key].update(value)
            else:
                self.state[key] = value


class _FakeDatabase:
    """جایگزین سبک services.financial_service.Database (و
    services.accounting_service.Database و services.audit_service.Database)
    برای این تست‌ها."""

    _shared_state = None

    def __init__(self):
        self._conn = None

    def connect(self):
        self._conn = _FakeConnection(self.__class__._shared_state)
        return self._conn

    def close(self):
        pass

    def execute(self, query, params=()):
        # استفاده‌شده توسط create_audit_entry (بعد از commit، خارج از
        # Transaction اصلی فراخوانی می‌شود) — فقط باید بدون Exception عبور کند.
        return None

    def fetch_all(self, query, params=()):
        return []

    def fetch_one(self, query, params=()):
        return None

    @classmethod
    def reset(cls):
        cls._shared_state = {
            "cash_boxes": {},
            "bank_accounts": {},
            "cheques": [],
            "receipts": [],
            "receipt_lines": [],
            "receipt_allocations": [],
            "sales_invoices": {},
            "cash_box_transactions": [],
            "bank_transactions": [],
            "accounts": [
                {"ID": 1, "Code": "1000", "Name": "صندوق و بانک", "IsActive": True},
                {"ID": 2, "Code": "1100", "Name": "دریافتنی", "IsActive": True},
                {"ID": 3, "Code": "1300", "Name": "اسناد دریافتنی", "IsActive": True},
                {"ID": 4, "Code": "2300", "Name": "پیش‌دریافت مشتری", "IsActive": True},
            ],
            "journal_entries": [],
            "journal_lines": [],
            "_next_receipt_id": 1,
            "_next_cheque_id": 1,
            "_next_journal_id": 1,
            "_last_identity": None,
        }


def setup_function():
    _FakeDatabase.reset()
    financial_service.Database = _FakeDatabase

    import services.accounting_service as accounting_service
    accounting_service.Database = _FakeDatabase

    import services.audit_service as audit_service
    audit_service.Database = _FakeDatabase

    state = _FakeDatabase._shared_state
    state["cash_boxes"][1] = {"ID": 1, "CurrentBalance": 1000.0}
    state["bank_accounts"][1] = {"ID": 1, "CurrentBalance": 5000.0}
    state["sales_invoices"][1] = {"ID": 1, "PaidAmount": 0.0}


def _cheque_line(amount=100.0, **extra):
    line = {
        "method": "Cheque", "amount": amount,
        "cheque": {"number": "123", "sayad": "", "bank": "Melli",
                   "issue_date": "1404-06-01", "due_date": "1404-07-01", "description": ""},
    }
    line.update(extra)
    return line


# =========================================================
# بخش ۱ — Regression: رفتار فعلی create_receipt() (نباید با اتصال Ledger بشکند)
# =========================================================

def test_create_receipt_rejects_empty_lines():
    with pytest.raises(FinancialError):
        financial_service.create_receipt(1, "1404-06-01", "", 1, [], [])


def test_create_receipt_rejects_zero_total():
    with pytest.raises(FinancialError):
        financial_service.create_receipt(
            1, "1404-06-01", "", 1,
            [{"method": "Cash", "amount": 0, "cash_box_id": 1}], []
        )


def test_create_receipt_rejects_over_allocation():
    with pytest.raises(FinancialError):
        financial_service.create_receipt(
            1, "1404-06-01", "", 1,
            [{"method": "Cash", "amount": 100, "cash_box_id": 1}],
            [{"invoice_id": 1, "amount": 1000}],
        )
    state = _FakeDatabase._shared_state
    assert state["receipts"] == []


def test_create_receipt_rejects_invalid_payment_method():
    with pytest.raises(FinancialError):
        financial_service.create_receipt(
            1, "1404-06-01", "", 1,
            [{"method": "Crypto", "amount": 100}], []
        )


def test_create_receipt_rejects_zero_or_negative_line_amount():
    with pytest.raises(FinancialError):
        financial_service.create_receipt(
            1, "1404-06-01", "", 1,
            [{"method": "Cash", "amount": 100, "cash_box_id": 1},
             {"method": "Bank", "amount": -1, "bank_account_id": 1}],
            [],
        )


def test_create_receipt_cash_updates_cash_box_balance():
    financial_service.create_receipt(
        1, "1404-06-01", "", 1,
        [{"method": "Cash", "amount": 300.0, "cash_box_id": 1}], []
    )
    state = _FakeDatabase._shared_state
    assert state["cash_boxes"][1]["CurrentBalance"] == 1300.0


def test_create_receipt_cash_inserts_cash_box_transaction():
    financial_service.create_receipt(
        1, "1404-06-01", "", 1,
        [{"method": "Cash", "amount": 300.0, "cash_box_id": 1}], []
    )
    state = _FakeDatabase._shared_state
    assert len(state["cash_box_transactions"]) == 1
    assert state["cash_box_transactions"][0]["Amount"] == 300.0


def test_create_receipt_bank_updates_bank_account_balance():
    financial_service.create_receipt(
        1, "1404-06-01", "", 1,
        [{"method": "Bank", "amount": 700.0, "bank_account_id": 1}], []
    )
    state = _FakeDatabase._shared_state
    assert state["bank_accounts"][1]["CurrentBalance"] == 5700.0


def test_create_receipt_bank_inserts_bank_transaction():
    financial_service.create_receipt(
        1, "1404-06-01", "", 1,
        [{"method": "Bank", "amount": 700.0, "bank_account_id": 1}], []
    )
    state = _FakeDatabase._shared_state
    assert len(state["bank_transactions"]) == 1
    assert state["bank_transactions"][0]["Amount"] == 700.0


def test_create_receipt_cheque_creates_cheques_row():
    financial_service.create_receipt(1, "1404-06-01", "", 1, [_cheque_line(250.0)], [])
    state = _FakeDatabase._shared_state
    assert len(state["cheques"]) == 1
    assert state["cheques"][0]["Amount"] == 250.0


def test_create_receipt_cheque_remains_in_hand():
    financial_service.create_receipt(1, "1404-06-01", "", 1, [_cheque_line(250.0)], [])
    state = _FakeDatabase._shared_state
    assert state["cheques"][0]["Status"] == "InHand"


def test_create_receipt_cheque_does_not_touch_cash_or_bank():
    financial_service.create_receipt(1, "1404-06-01", "", 1, [_cheque_line(250.0)], [])
    state = _FakeDatabase._shared_state
    assert state["cash_boxes"][1]["CurrentBalance"] == 1000.0
    assert state["bank_accounts"][1]["CurrentBalance"] == 5000.0
    assert state["cash_box_transactions"] == []
    assert state["bank_transactions"] == []


def test_create_receipt_mixed_cash_bank_cheque():
    receipt_id, _ = financial_service.create_receipt(
        1, "1404-06-01", "", 1,
        [
            {"method": "Cash", "amount": 100.0, "cash_box_id": 1},
            {"method": "Bank", "amount": 200.0, "bank_account_id": 1},
            _cheque_line(300.0),
        ],
        [],
    )
    state = _FakeDatabase._shared_state
    assert len(state["receipt_lines"]) == 3
    assert state["cash_boxes"][1]["CurrentBalance"] == 1100.0
    assert state["bank_accounts"][1]["CurrentBalance"] == 5200.0
    assert len(state["cheques"]) == 1


def test_create_receipt_inserts_allocations_and_updates_paid_amount():
    financial_service.create_receipt(
        1, "1404-06-01", "", 1,
        [{"method": "Cash", "amount": 500.0, "cash_box_id": 1}],
        [{"invoice_id": 1, "amount": 500.0}],
    )
    state = _FakeDatabase._shared_state
    assert len(state["receipt_allocations"]) == 1
    assert state["sales_invoices"][1]["PaidAmount"] == 500.0


def test_create_receipt_partial_allocation_remains_allowed():
    receipt_id, _ = financial_service.create_receipt(
        1, "1404-06-01", "", 1,
        [{"method": "Cash", "amount": 1000.0, "cash_box_id": 1}],
        [{"invoice_id": 1, "amount": 400.0}],
    )
    state = _FakeDatabase._shared_state
    assert receipt_id is not None
    assert state["sales_invoices"][1]["PaidAmount"] == 400.0
    assert state["receipts"][0]["TotalAmount"] == 1000.0


def test_create_receipt_rolls_back_everything_on_failure():
    state = _FakeDatabase._shared_state
    with pytest.raises(FinancialError):
        financial_service.create_receipt(
            1, "1404-06-01", "", 1,
            [{"method": "Cash", "amount": 100.0, "cash_box_id": 1},
             {"method": "Bank", "amount": 0, "bank_account_id": 1}],
            [],
        )
    assert state["receipts"] == []
    assert state["cash_boxes"][1]["CurrentBalance"] == 1000.0
    assert state["cash_box_transactions"] == []


# =========================================================
# بخش ۲ — اتصال Ledger: سند حسابداری دوطرفه
# =========================================================

def test_create_receipt_fully_allocated_cash_journal():
    receipt_id, _ = financial_service.create_receipt(
        1, "1404-06-01", "", 1,
        [{"method": "Cash", "amount": 500.0, "cash_box_id": 1}],
        [{"invoice_id": 1, "amount": 500.0}],
    )
    state = _FakeDatabase._shared_state
    accounts_by_id = {a["ID"]: a["Code"] for a in state["accounts"]}
    lines = state["journal_lines"]

    debit_cash = next(l["Debit"] for l in lines if accounts_by_id[l["AccountRef"]] == "1000")
    credit_ar = next(l["Credit"] for l in lines if accounts_by_id[l["AccountRef"]] == "1100")

    assert debit_cash == 500.0
    assert credit_ar == 500.0
    assert all(accounts_by_id[l["AccountRef"]] != "2300" for l in lines)


def test_create_receipt_fully_allocated_bank_journal():
    financial_service.create_receipt(
        1, "1404-06-01", "", 1,
        [{"method": "Bank", "amount": 700.0, "bank_account_id": 1}],
        [{"invoice_id": 1, "amount": 700.0}],
    )
    state = _FakeDatabase._shared_state
    accounts_by_id = {a["ID"]: a["Code"] for a in state["accounts"]}
    lines = state["journal_lines"]

    debit_cash = next(l["Debit"] for l in lines if accounts_by_id[l["AccountRef"]] == "1000")
    credit_ar = next(l["Credit"] for l in lines if accounts_by_id[l["AccountRef"]] == "1100")

    assert debit_cash == 700.0
    assert credit_ar == 700.0


def test_create_receipt_fully_allocated_cheque_journal():
    financial_service.create_receipt(
        1, "1404-06-01", "", 1,
        [_cheque_line(250.0)],
        [{"invoice_id": 1, "amount": 250.0}],
    )
    state = _FakeDatabase._shared_state
    accounts_by_id = {a["ID"]: a["Code"] for a in state["accounts"]}
    lines = state["journal_lines"]

    debit_notes = next(l["Debit"] for l in lines if accounts_by_id[l["AccountRef"]] == "1300")
    credit_ar = next(l["Credit"] for l in lines if accounts_by_id[l["AccountRef"]] == "1100")

    assert debit_notes == 250.0
    assert credit_ar == 250.0
    assert all(accounts_by_id[l["AccountRef"]] != "1000" for l in lines)


def test_create_receipt_mixed_journal_debits_1000_and_1300():
    receipt_id, _ = financial_service.create_receipt(
        1, "1404-06-01", "", 1,
        [
            {"method": "Cash", "amount": 100.0, "cash_box_id": 1},
            {"method": "Bank", "amount": 200.0, "bank_account_id": 1},
            _cheque_line(300.0),
        ],
        [{"invoice_id": 1, "amount": 600.0}],
    )
    state = _FakeDatabase._shared_state
    accounts_by_id = {a["ID"]: a["Code"] for a in state["accounts"]}
    lines = state["journal_lines"]

    debit_cash_bank = next(l["Debit"] for l in lines if accounts_by_id[l["AccountRef"]] == "1000")
    debit_notes = next(l["Debit"] for l in lines if accounts_by_id[l["AccountRef"]] == "1300")
    credit_ar = next(l["Credit"] for l in lines if accounts_by_id[l["AccountRef"]] == "1100")

    assert debit_cash_bank == 300.0  # 100 + 200
    assert debit_notes == 300.0
    assert credit_ar == 600.0
    assert sum(l["Debit"] for l in lines) == sum(l["Credit"] for l in lines)


def test_create_receipt_partially_allocated_credits_2300_for_remainder():
    receipt_id, _ = financial_service.create_receipt(
        1, "1404-06-01", "", 1,
        [{"method": "Cash", "amount": 1000.0, "cash_box_id": 1}],
        [{"invoice_id": 1, "amount": 400.0}],
    )
    state = _FakeDatabase._shared_state
    accounts_by_id = {a["ID"]: a["Code"] for a in state["accounts"]}
    lines = state["journal_lines"]

    debit_cash = next(l["Debit"] for l in lines if accounts_by_id[l["AccountRef"]] == "1000")
    credit_ar = next(l["Credit"] for l in lines if accounts_by_id[l["AccountRef"]] == "1100")
    credit_advance = next(l["Credit"] for l in lines if accounts_by_id[l["AccountRef"]] == "2300")

    assert debit_cash == 1000.0
    assert credit_ar == 400.0
    assert credit_advance == 600.0
    assert sum(l["Debit"] for l in lines) == sum(l["Credit"] for l in lines)


def test_create_receipt_fully_unallocated_credits_only_2300():
    financial_service.create_receipt(
        1, "1404-06-01", "", 1,
        [{"method": "Cash", "amount": 500.0, "cash_box_id": 1}],
        [],
    )
    state = _FakeDatabase._shared_state
    accounts_by_id = {a["ID"]: a["Code"] for a in state["accounts"]}
    lines = state["journal_lines"]

    assert all(accounts_by_id[l["AccountRef"]] != "1100" for l in lines)
    credit_advance = next(l["Credit"] for l in lines if accounts_by_id[l["AccountRef"]] == "2300")
    assert credit_advance == 500.0


def test_create_receipt_journal_always_balanced():
    financial_service.create_receipt(
        1, "1404-06-01", "", 1,
        [
            {"method": "Cash", "amount": 150.0, "cash_box_id": 1},
            {"method": "Bank", "amount": 350.0, "bank_account_id": 1},
            _cheque_line(500.0),
        ],
        [{"invoice_id": 1, "amount": 600.0}],
    )
    state = _FakeDatabase._shared_state
    lines = state["journal_lines"]
    assert sum(l["Debit"] for l in lines) == sum(l["Credit"] for l in lines)


def test_create_receipt_journal_source_table_and_id():
    receipt_id, _ = financial_service.create_receipt(
        1, "1404-06-01", "", 1,
        [{"method": "Cash", "amount": 500.0, "cash_box_id": 1}],
        [{"invoice_id": 1, "amount": 500.0}],
    )
    state = _FakeDatabase._shared_state
    entry = state["journal_entries"][0]
    assert entry["SourceTable"] == "Receipts"
    assert entry["SourceID"] == receipt_id


def test_create_receipt_journal_entry_number_increments():
    financial_service.create_receipt(
        1, "1404-06-01", "", 1,
        [{"method": "Cash", "amount": 100.0, "cash_box_id": 1}], []
    )
    financial_service.create_receipt(
        1, "1404-06-02", "", 1,
        [{"method": "Cash", "amount": 200.0, "cash_box_id": 1}], []
    )
    state = _FakeDatabase._shared_state
    numbers = sorted(e["EntryNumber"] for e in state["journal_entries"])
    assert numbers == [1, 2]


def test_create_receipt_missing_account_1000_rolls_back_everything():
    state = _FakeDatabase._shared_state
    state["accounts"] = [a for a in state["accounts"] if a["Code"] != "1000"]

    with pytest.raises(AccountingError):
        financial_service.create_receipt(
            1, "1404-06-01", "", 1,
            [{"method": "Cash", "amount": 500.0, "cash_box_id": 1}],
            [{"invoice_id": 1, "amount": 500.0}],
        )

    assert state["receipts"] == []
    assert state["journal_entries"] == []
    assert state["journal_lines"] == []
    assert state["cash_boxes"][1]["CurrentBalance"] == 1000.0  # Rollback شده


def test_create_receipt_missing_account_1100_rolls_back_everything():
    state = _FakeDatabase._shared_state
    state["accounts"] = [a for a in state["accounts"] if a["Code"] != "1100"]

    with pytest.raises(AccountingError):
        financial_service.create_receipt(
            1, "1404-06-01", "", 1,
            [{"method": "Cash", "amount": 500.0, "cash_box_id": 1}],
            [{"invoice_id": 1, "amount": 500.0}],
        )

    assert state["receipts"] == []
    assert state["sales_invoices"][1]["PaidAmount"] == 0.0  # Rollback شده


def test_create_receipt_missing_account_1300_rolls_back_everything():
    state = _FakeDatabase._shared_state
    state["accounts"] = [a for a in state["accounts"] if a["Code"] != "1300"]

    with pytest.raises(AccountingError):
        financial_service.create_receipt(
            1, "1404-06-01", "", 1,
            [_cheque_line(250.0)],
            [{"invoice_id": 1, "amount": 250.0}],
        )

    assert state["receipts"] == []
    assert state["cheques"] == []  # Rollback شده


def test_create_receipt_missing_account_2300_rolls_back_everything():
    state = _FakeDatabase._shared_state
    state["accounts"] = [a for a in state["accounts"] if a["Code"] != "2300"]

    with pytest.raises(AccountingError):
        financial_service.create_receipt(
            1, "1404-06-01", "", 1,
            [{"method": "Cash", "amount": 1000.0, "cash_box_id": 1}],
            [{"invoice_id": 1, "amount": 400.0}],  # partial -> نیاز به 2300
        )

    assert state["receipts"] == []
    assert state["cash_boxes"][1]["CurrentBalance"] == 1000.0  # Rollback شده


def test_create_receipt_pure_validation_failure_never_touches_ledger():
    state = _FakeDatabase._shared_state
    with pytest.raises(FinancialError):
        financial_service.create_receipt(1, "1404-06-01", "", 1, [], [])
    assert state["journal_entries"] == []
    assert state["journal_lines"] == []


# =========================================================
# بخش ۳ — _build_receipt_journal_lines: تست خالص (بدون دیتابیس)
# =========================================================

def test_build_receipt_journal_lines_fully_allocated_balanced_pure():
    lines = _build_receipt_journal_lines(
        cash_amount=500.0, bank_amount=0, cheque_amount=0, alloc_sum=500.0, total_amount=500.0
    )
    assert sum(l.get("debit", 0) for l in lines) == sum(l.get("credit", 0) for l in lines)
    codes = {l["account_code"] for l in lines}
    assert codes == {"1000", "1100"}


def test_build_receipt_journal_lines_omits_2300_when_fully_allocated():
    lines = _build_receipt_journal_lines(
        cash_amount=500.0, bank_amount=0, cheque_amount=0, alloc_sum=500.0, total_amount=500.0
    )
    assert all(l["account_code"] != "2300" for l in lines)


def test_build_receipt_journal_lines_includes_2300_when_partially_allocated():
    lines = _build_receipt_journal_lines(
        cash_amount=1000.0, bank_amount=0, cheque_amount=0, alloc_sum=400.0, total_amount=1000.0
    )
    advance_line = next(l for l in lines if l["account_code"] == "2300")
    ar_line = next(l for l in lines if l["account_code"] == "1100")
    assert advance_line["credit"] == 600.0
    assert ar_line["credit"] == 400.0
    assert sum(l.get("debit", 0) for l in lines) == sum(l.get("credit", 0) for l in lines)


def test_build_receipt_journal_lines_omits_1100_when_fully_unallocated():
    lines = _build_receipt_journal_lines(
        cash_amount=500.0, bank_amount=0, cheque_amount=0, alloc_sum=0, total_amount=500.0
    )
    codes = {l["account_code"] for l in lines}
    assert "1100" not in codes
    assert codes == {"1000", "2300"}


def test_build_receipt_journal_lines_aggregates_cash_and_bank_into_1000():
    lines = _build_receipt_journal_lines(
        cash_amount=100.0, bank_amount=200.0, cheque_amount=0, alloc_sum=300.0, total_amount=300.0
    )
    cash_bank_line = next(l for l in lines if l["account_code"] == "1000")
    assert cash_bank_line["debit"] == 300.0


def test_build_receipt_journal_lines_cheque_goes_to_1300_not_1000():
    lines = _build_receipt_journal_lines(
        cash_amount=0, bank_amount=0, cheque_amount=250.0, alloc_sum=250.0, total_amount=250.0
    )
    codes = {l["account_code"] for l in lines}
    assert "1300" in codes and "1000" not in codes


def test_build_receipt_journal_lines_never_credits_full_amount_to_1100_when_partial():
    lines = _build_receipt_journal_lines(
        cash_amount=1000.0, bank_amount=0, cheque_amount=0, alloc_sum=400.0, total_amount=1000.0
    )
    ar_line = next(l for l in lines if l["account_code"] == "1100")
    assert ar_line["credit"] != 1000.0
    assert ar_line["credit"] == 400.0
