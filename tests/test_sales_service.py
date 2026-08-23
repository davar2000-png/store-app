# -*- coding: utf-8 -*-
"""
Phase 15.2 — اتصال فروش به حسابداری دوطرفه

این ماژول قبل از این فاز **هیچ تست**ی نداشت (طبق `AI_HANDOFF.md`، آگاهانه
به‌عنوان بدهی فنی برای این فاز باقی مانده بود). طبق قانون Brief («قبل از
تغییر sales_service.py، تست‌های Regression لازم را اضافه کن»)، این فایل دو
دسته تست دارد:

۱) Regression — رفتار **فعلی** فروش (FIFO، موجودی، کاردکس، سریال/IMEI،
   خطاهای اعتبارسنجی) که باید دقیقاً همان‌طور که قبل از این فاز کار
   می‌کرد، ادامه یابد. اتصال Ledger نباید هیچ‌کدام از این‌ها را بشکند.
۲) اتصال Ledger — سند حسابداری دوطرفه‌ای که حالا برای هر فاکتور فروش در
   همان Transaction اتمیک ساخته می‌شود: موازنه، حساب‌های درست، مرجع سند
   مبدأ (SourceTable/SourceID)، و رفتار Rollback کامل در صورت خطای Ledger.

از یک Fake Cursor/Connection سبک استفاده می‌شود (مثل الگوی
`tests/test_accounting_service.py`) که رفتار Cursor واقعی pyodbc را برای
دقیقاً همان Queryهایی که `sales_service.create_sales_invoice` و
`accounting_service._post_journal_entry_on_cursor` صادر می‌کنند شبیه‌سازی
می‌کند و از یک Snapshot برای Rollback واقعی استفاده می‌کند.
"""

import copy

import pytest

import services.sales_service as sales_service
from services.sales_service import SalesError, _build_sales_journal_lines
from services.accounting_service import AccountingError


# =========================================================
# Fake DB — Cursor-Based (مثل الگوی test_accounting_service.py)
# =========================================================

class _FakeCursor:
    def __init__(self, state):
        self.state = state
        self._last_result = None
        self._last_fetchall = None

    def execute(self, sql, params=()):
        normalized = " ".join(sql.split()).upper()
        state = self.state

        if normalized.startswith("SELECT SETTINGVALUE FROM SETTINGS WHERE SETTINGKEY = ?"):
            key = params[0]
            val = state["settings"].get(key)
            self._last_result = (val,) if val is not None else None
            return

        if normalized.startswith("SELECT ISNULL(MAX(INVOICENUMBER), 2000)"):
            next_num = max((i["InvoiceNumber"] for i in state["invoices"]), default=2000) + 1
            self._last_result = (next_num,)
            return

        if normalized.startswith("INSERT INTO SALESINVOICES"):
            (invoice_number, person_ref, shamsi_date, total_amount, discount_amount,
             tax_amount, payable_amount, description, user_ref) = params
            new_id = state["_next_invoice_id"]
            state["_next_invoice_id"] += 1
            state["invoices"].append({
                "ID": new_id, "InvoiceNumber": invoice_number, "PersonRef": person_ref,
                "ShamsiDate": shamsi_date, "TotalAmount": total_amount,
                "DiscountAmount": discount_amount, "TaxAmount": tax_amount,
                "PayableAmount": payable_amount, "Description": description, "UserRef": user_ref,
            })
            state["_last_identity"] = new_id
            self._last_result = None
            return

        if normalized == "SELECT @@IDENTITY AS ID":
            self._last_result = (state["_last_identity"],)
            return

        if normalized.startswith("SELECT ID, REMAININGQUANTITY, UNITPRICE FROM PRODUCTPURCHASELAYERS"):
            product_id = params[0]
            layers = [l for l in state["layers"]
                      if l["ProductRef"] == product_id and l["RemainingQuantity"] > 0]
            layers.sort(key=lambda l: l["ID"])
            self._last_fetchall = [(l["ID"], l["RemainingQuantity"], l["UnitPrice"]) for l in layers]
            return

        if normalized.startswith("SELECT PURCHASEPRICE FROM PRODUCTS WHERE ID = ?"):
            product_id = params[0]
            self._last_result = (state["products"][product_id]["PurchasePrice"],)
            return

        if normalized.startswith("INSERT INTO SALESINVOICEITEMS"):
            (invoice_ref, product_ref, qty, unit_price, discount_amount, total_price,
             cost_amount, description) = params
            new_id = state["_next_item_id"]
            state["_next_item_id"] += 1
            state["items"].append({
                "ID": new_id, "InvoiceRef": invoice_ref, "ProductRef": product_ref,
                "Quantity": qty, "UnitPrice": unit_price, "DiscountAmount": discount_amount,
                "TotalPrice": total_price, "CostAmount": cost_amount, "Description": description,
            })
            state["_last_identity"] = new_id
            self._last_result = None
            return

        if normalized.startswith("UPDATE PRODUCTPURCHASELAYERS SET REMAININGQUANTITY"):
            take, layer_id = params
            for l in state["layers"]:
                if l["ID"] == layer_id:
                    l["RemainingQuantity"] -= take
            return

        if normalized.startswith("INSERT INTO SALESINVOICEITEMLAYERS"):
            item_ref, layer_ref, qty, unit_price = params
            state["item_layers"].append({
                "SalesInvoiceItemRef": item_ref, "PurchaseLayerRef": layer_ref,
                "Quantity": qty, "UnitPrice": unit_price,
            })
            self._last_result = None
            return

        if normalized.startswith("SELECT STATUS FROM PRODUCTSERIALS WHERE ID = ? AND PRODUCTREF = ?"):
            serial_id, product_id = params
            s = state["serials"].get(serial_id)
            self._last_result = (s["Status"],) if (s and s["ProductRef"] == product_id) else None
            return

        if normalized.startswith("UPDATE PRODUCTSERIALS SET STATUS = N'SOLD'"):
            item_ref, serial_id = params
            s = state["serials"].get(serial_id)
            if s:
                s["Status"] = "Sold"
                s["SoldInInvoiceItemRef"] = item_ref
            return

        if normalized.startswith("UPDATE PRODUCTS SET CURRENTSTOCK = CURRENTSTOCK - ?"):
            qty, product_id = params
            state["products"][product_id]["CurrentStock"] -= qty
            return

        if normalized.startswith("SELECT CURRENTSTOCK FROM PRODUCTS WHERE ID = ?"):
            product_id = params[0]
            self._last_result = (state["products"][product_id]["CurrentStock"],)
            return

        if normalized.startswith("INSERT INTO PRODUCTCARDEX"):
            (product_ref, shamsi_date, invoice_ref, out_qty, unit_price,
             balance, description, user_ref) = params
            state["cardex"].append({
                "ProductRef": product_ref, "ShamsiDate": shamsi_date, "RefID": invoice_ref,
                "OutQuantity": out_qty, "UnitPrice": unit_price, "BalanceQuantity": balance,
                "Description": description, "UserRef": user_ref,
            })
            self._last_result = None
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
    """جایگزین سبک services.sales_service.Database (و services.accounting_service.Database
    و services.audit_service.Database) برای این تست‌ها."""

    _shared_state = None

    def __init__(self):
        self._conn = None

    def connect(self):
        self._conn = _FakeConnection(self.__class__._shared_state)
        return self._conn

    def close(self):
        pass

    def execute(self, query, params=()):
        # استفاده‌شده توسط create_audit_entry (بعد از commit، خارج از Transaction
        # اصلی فراخوانی می‌شود) — فقط باید بدون Exception عبور کند.
        return None

    def fetch_all(self, query, params=()):
        return []

    def fetch_one(self, query, params=()):
        return None

    @classmethod
    def reset(cls):
        cls._shared_state = {
            "products": {},
            "layers": [],
            "serials": {},
            "settings": {},
            "invoices": [],
            "items": [],
            "item_layers": [],
            "cardex": [],
            "accounts": [
                {"ID": 1, "Code": "1100", "Name": "دریافتنی", "IsActive": True},
                {"ID": 2, "Code": "1200", "Name": "موجودی کالا", "IsActive": True},
                {"ID": 3, "Code": "2200", "Name": "مالیات", "IsActive": True},
                {"ID": 4, "Code": "4000", "Name": "درآمد فروش", "IsActive": True},
                {"ID": 5, "Code": "5000", "Name": "بهای تمام‌شده", "IsActive": True},
            ],
            "journal_entries": [],
            "journal_lines": [],
            "_next_invoice_id": 1,
            "_next_item_id": 1,
            "_next_journal_id": 1,
            "_last_identity": None,
        }


def setup_function():
    _FakeDatabase.reset()
    sales_service.Database = _FakeDatabase

    import services.accounting_service as accounting_service
    accounting_service.Database = _FakeDatabase

    import services.audit_service as audit_service
    audit_service.Database = _FakeDatabase

    state = _FakeDatabase._shared_state
    # یک کالای پایه با دو لایه خرید FIFO (برای تست‌های چندلایه)
    state["products"][1] = {"ID": 1, "CurrentStock": 30, "PurchasePrice": 100.0}
    state["layers"].extend([
        {"ID": 1, "ProductRef": 1, "RemainingQuantity": 10, "UnitPrice": 100.0},
        {"ID": 2, "ProductRef": 1, "RemainingQuantity": 20, "UnitPrice": 120.0},
    ])


def _basic_item(qty=5, price=200.0, discount=0.0, **extra):
    item = {"product_id": 1, "quantity": qty, "unit_price": price, "discount": discount}
    item.update(extra)
    return item


# =========================================================
# بخش ۱ — Regression: رفتار فعلی فروش (نباید با اتصال Ledger بشکند)
# =========================================================

def test_create_sales_invoice_requires_items():
    with pytest.raises(SalesError):
        sales_service.create_sales_invoice(1, "1404-06-01", 0, 0, "", 1, [])
    state = _FakeDatabase._shared_state
    assert state["invoices"] == []


def test_create_sales_invoice_rejects_zero_quantity():
    with pytest.raises(SalesError):
        sales_service.create_sales_invoice(1, "1404-06-01", 0, 0, "", 1, [_basic_item(qty=0)])


def test_create_sales_invoice_rejects_negative_price():
    with pytest.raises(SalesError):
        sales_service.create_sales_invoice(1, "1404-06-01", 0, 0, "", 1, [_basic_item(price=-1)])


def test_create_sales_invoice_requires_matching_serial_count():
    item = _basic_item(qty=2, has_serial=True, serial_ids=[101])
    with pytest.raises(SalesError):
        sales_service.create_sales_invoice(1, "1404-06-01", 0, 0, "", 1, [item])


def test_create_sales_invoice_single_layer_fifo_cost():
    # ۵ عدد از لایه اول (قیمت ۱۰۰) کم می‌شود -> بهای تمام‌شده = ۵۰۰
    invoice_id, invoice_number = sales_service.create_sales_invoice(
        1, "1404-06-01", 0, 0, "", 1, [_basic_item(qty=5, price=200.0)]
    )
    state = _FakeDatabase._shared_state
    assert invoice_number == 2001
    item = state["items"][0]
    assert item["CostAmount"] == 500.0
    assert item["TotalPrice"] == 1000.0

    layer1 = next(l for l in state["layers"] if l["ID"] == 1)
    assert layer1["RemainingQuantity"] == 5


def test_create_sales_invoice_multi_layer_fifo_cost():
    # ۱۵ عدد: ۱۰ از لایه اول (۱۰۰) + ۵ از لایه دوم (۱۲۰) => بهای = ۱۰۰۰ + ۶۰۰ = ۱۶۰۰
    sales_service.create_sales_invoice(
        1, "1404-06-01", 0, 0, "", 1, [_basic_item(qty=15, price=200.0)]
    )
    state = _FakeDatabase._shared_state
    item = state["items"][0]
    assert item["CostAmount"] == 1600.0

    layer1 = next(l for l in state["layers"] if l["ID"] == 1)
    layer2 = next(l for l in state["layers"] if l["ID"] == 2)
    assert layer1["RemainingQuantity"] == 0
    assert layer2["RemainingQuantity"] == 15


def test_create_sales_invoice_insufficient_stock_raises_and_rolls_back_everything():
    state = _FakeDatabase._shared_state
    state["settings"]["AllowNegativeStock"] = "0"

    with pytest.raises(SalesError):
        sales_service.create_sales_invoice(
            1, "1404-06-01", 0, 0, "", 1, [_basic_item(qty=999, price=200.0)]
        )

    # هیچ‌چیزی نباید ذخیره مانده باشد (Rollback کامل)
    assert state["invoices"] == []
    assert state["items"] == []
    layer1 = next(l for l in state["layers"] if l["ID"] == 1)
    assert layer1["RemainingQuantity"] == 10  # دست‌نخورده


def test_create_sales_invoice_allows_negative_stock_when_setting_enabled():
    state = _FakeDatabase._shared_state
    state["settings"]["AllowNegativeStock"] = "1"

    invoice_id, _ = sales_service.create_sales_invoice(
        1, "1404-06-01", 0, 0, "", 1, [_basic_item(qty=40, price=200.0)]
    )
    # موجودی کل لایه‌ها ۳۰ است؛ ۱۰ عدد کمبود با PurchasePrice=100 پوشش داده می‌شود
    item = state["items"][0]
    # ۱۰*۱۰۰ + ۲۰*۱۲۰ + ۱۰*۱۰۰(کمبود) = ۱۰۰۰+۲۴۰۰+۱۰۰۰ = ۴۴۰۰
    assert item["CostAmount"] == 4400.0


def test_create_sales_invoice_updates_stock_and_cardex():
    sales_service.create_sales_invoice(
        1, "1404-06-01", 0, 0, "", 1, [_basic_item(qty=5, price=200.0)]
    )
    state = _FakeDatabase._shared_state
    assert state["products"][1]["CurrentStock"] == 25
    assert len(state["cardex"]) == 1
    assert state["cardex"][0]["OutQuantity"] == 5
    assert state["cardex"][0]["BalanceQuantity"] == 25


def test_create_sales_invoice_marks_serials_sold():
    state = _FakeDatabase._shared_state
    state["serials"][501] = {"ID": 501, "ProductRef": 1, "Status": "InStock"}

    invoice_id, _ = sales_service.create_sales_invoice(
        1, "1404-06-01", 0, 0, "", 1,
        [_basic_item(qty=1, price=200.0, has_serial=True, serial_ids=[501])]
    )
    assert state["serials"][501]["Status"] == "Sold"


def test_create_sales_invoice_rejects_serial_not_in_stock():
    state = _FakeDatabase._shared_state
    state["serials"][501] = {"ID": 501, "ProductRef": 1, "Status": "Sold"}

    with pytest.raises(SalesError):
        sales_service.create_sales_invoice(
            1, "1404-06-01", 0, 0, "", 1,
            [_basic_item(qty=1, price=200.0, has_serial=True, serial_ids=[501])]
        )
    assert state["invoices"] == []


# =========================================================
# بخش ۲ — اتصال Ledger: سند حسابداری دوطرفه
# =========================================================

def test_create_sales_invoice_posts_balanced_journal_entry():
    invoice_id, invoice_number = sales_service.create_sales_invoice(
        1, "1404-06-01", 0, 0, "", 1, [_basic_item(qty=5, price=200.0)]
    )
    state = _FakeDatabase._shared_state

    assert len(state["journal_entries"]) == 1
    entry = state["journal_entries"][0]
    assert entry["SourceTable"] == "SalesInvoices"
    assert entry["SourceID"] == invoice_id

    lines = state["journal_lines"]
    total_debit = sum(l["Debit"] for l in lines)
    total_credit = sum(l["Credit"] for l in lines)
    assert total_debit == total_credit  # موازنه واقعی

    # 1000 = 5*200 (فروش) ; بهای = 500 (۵ عدد از لایه ۱۰۰)
    accounts_by_id = {a["ID"]: a["Code"] for a in state["accounts"]}
    debit_ar = next(l["Debit"] for l in lines if accounts_by_id[l["AccountRef"]] == "1100")
    credit_rev = next(l["Credit"] for l in lines if accounts_by_id[l["AccountRef"]] == "4000")
    debit_cogs = next(l["Debit"] for l in lines if accounts_by_id[l["AccountRef"]] == "5000")
    credit_inv = next(l["Credit"] for l in lines if accounts_by_id[l["AccountRef"]] == "1200")

    assert debit_ar == 1000.0
    assert credit_rev == 1000.0
    assert debit_cogs == 500.0
    assert credit_inv == 500.0
    # بدون مالیات، نباید هیچ ردیفی برای حساب مالیات ساخته شود
    assert all(accounts_by_id[l["AccountRef"]] != "2200" for l in lines)


def test_create_sales_invoice_journal_includes_tax_payable_line_when_tax_present():
    sales_service.create_sales_invoice(
        1, "1404-06-01", discount_amount=0, tax_amount=90, description="", user_id=1,
        items=[_basic_item(qty=5, price=200.0)]
    )
    state = _FakeDatabase._shared_state
    accounts_by_id = {a["ID"]: a["Code"] for a in state["accounts"]}
    lines = state["journal_lines"]

    credit_tax = next(l["Credit"] for l in lines if accounts_by_id[l["AccountRef"]] == "2200")
    debit_ar = next(l["Debit"] for l in lines if accounts_by_id[l["AccountRef"]] == "1100")

    assert credit_tax == 90.0
    assert debit_ar == 1090.0  # PayableAmount = 1000 - 0 + 90
    assert sum(l["Debit"] for l in lines) == sum(l["Credit"] for l in lines)


def test_create_sales_invoice_journal_entry_number_increments_across_invoices():
    sales_service.create_sales_invoice(1, "1404-06-01", 0, 0, "", 1, [_basic_item(qty=2, price=200.0)])
    sales_service.create_sales_invoice(1, "1404-06-02", 0, 0, "", 1, [_basic_item(qty=2, price=200.0)])
    state = _FakeDatabase._shared_state
    numbers = sorted(e["EntryNumber"] for e in state["journal_entries"])
    assert numbers == [1, 2]


def test_create_sales_invoice_rolls_back_everything_when_ledger_account_missing():
    """اگر Chart of Accounts حساب لازم را نداشته باشد (ناسازگاری Ledger)،
    کل فاکتور فروش (سربرگ، اقلام، کسر FIFO، موجودی، کاردکس) باید Rollback
    شود — نه اینکه فاکتور بدون سند حسابداری باقی بماند."""
    state = _FakeDatabase._shared_state
    # حذف حساب درآمد فروش برای شبیه‌سازی یک Chart of Accounts ناقص
    state["accounts"] = [a for a in state["accounts"] if a["Code"] != "4000"]

    with pytest.raises(AccountingError):
        sales_service.create_sales_invoice(1, "1404-06-01", 0, 0, "", 1, [_basic_item(qty=5, price=200.0)])

    assert state["invoices"] == []
    assert state["items"] == []
    assert state["journal_entries"] == []
    assert state["journal_lines"] == []
    layer1 = next(l for l in state["layers"] if l["ID"] == 1)
    assert layer1["RemainingQuantity"] == 10  # کسر FIFO هم Rollback شده
    assert state["products"][1]["CurrentStock"] == 30  # موجودی هم دست‌نخورده


def test_create_sales_invoice_pure_validation_failure_never_touches_ledger():
    state = _FakeDatabase._shared_state
    with pytest.raises(SalesError):
        sales_service.create_sales_invoice(1, "1404-06-01", 0, 0, "", 1, [])
    assert state["journal_entries"] == []
    assert state["journal_lines"] == []


# =========================================================
# بخش ۳ — _build_sales_journal_lines: تست خالص (بدون دیتابیس)
# =========================================================

def test_build_sales_journal_lines_balanced_pure():
    lines = _build_sales_journal_lines(
        total_amount=1000, discount_amount=0, tax_amount=0, payable=1000, total_cost_amount=500
    )
    assert sum(l.get("debit", 0) for l in lines) == sum(l.get("credit", 0) for l in lines)
    codes = {l["account_code"] for l in lines}
    assert codes == {"1100", "4000", "5000", "1200"}


def test_build_sales_journal_lines_skips_zero_tax_line():
    lines = _build_sales_journal_lines(
        total_amount=1000, discount_amount=0, tax_amount=0, payable=1000, total_cost_amount=500
    )
    assert all(l["account_code"] != "2200" for l in lines)


def test_build_sales_journal_lines_includes_tax_line_when_present():
    lines = _build_sales_journal_lines(
        total_amount=1000, discount_amount=0, tax_amount=90, payable=1090, total_cost_amount=500
    )
    tax_line = next(l for l in lines if l["account_code"] == "2200")
    assert tax_line["credit"] == 90


def test_build_sales_journal_lines_omits_cogs_lines_when_cost_zero():
    lines = _build_sales_journal_lines(
        total_amount=1000, discount_amount=0, tax_amount=0, payable=1000, total_cost_amount=0
    )
    codes = {l["account_code"] for l in lines}
    assert "5000" not in codes and "1200" not in codes


def test_build_sales_journal_lines_applies_discount_to_revenue_not_ar():
    lines = _build_sales_journal_lines(
        total_amount=1000, discount_amount=100, tax_amount=0, payable=900, total_cost_amount=500
    )
    ar_line = next(l for l in lines if l["account_code"] == "1100")
    rev_line = next(l for l in lines if l["account_code"] == "4000")
    assert ar_line["debit"] == 900
    assert rev_line["credit"] == 900
