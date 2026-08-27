# -*- coding: utf-8 -*-
"""
Phase 15.3 — اتصال خرید به حسابداری دوطرفه (Option C)

این ماژول قبل از این فاز هیچ تستی نداشت. طبق همان قانونی که در Phase 15.2
برای sales_service.py رعایت شد، این فایل دو دسته تست دارد:

۱) Regression — رفتار **فعلی** create_purchase_invoice (اقلام، لایه FIFO با
   قیمت خام، سریال/IMEI، موجودی، کاردکس، خطاهای اعتبارسنجی) که باید دقیقاً
   همان‌طور که قبل از این فاز کار می‌کرد ادامه یابد. اتصال Ledger نباید
   هیچ‌کدام از این‌ها را بشکند و به‌خصوص نباید ProductPurchaseLayers.UnitPrice
   را تغییر دهد (طبق تصمیم صریح Option C).
۲) اتصال Ledger — سند حسابداری دوطرفه‌ای که حالا برای هر فاکتور خرید در
   همان Transaction اتمیک ساخته می‌شود:
       بدهکار 1200 موجودی کالا       = SUM(quantity × raw_unit_price)
       بدهکار 1400 مالیات خرید       = TaxAmount
       بستانکار 5100 تخفیف خرید      = تخفیف قلمی + تخفیف سربرگ
       بستانکار 2000 حساب‌های پرداختنی = PayableAmount
   موازنه، حساب‌های درست، مرجع سند مبدأ (SourceTable/SourceID)، و رفتار
   Rollback کامل در صورت خطای Ledger.

از یک Fake Cursor/Connection سبک استفاده می‌شود (دقیقاً مثل الگوی
tests/test_sales_service.py) که رفتار Cursor واقعی pyodbc را برای همان
Queryهایی که inventory_service.create_purchase_invoice و
accounting_service._post_journal_entry_on_cursor صادر می‌کنند شبیه‌سازی
می‌کند و از یک Snapshot برای Rollback واقعی استفاده می‌کند.
"""

import copy

import pytest

import services.inventory_service as inventory_service
from services.inventory_service import (
    InventoryError,
    _build_purchase_journal_lines,
    _build_purchase_return_journal_lines,
)
from services.accounting_service import AccountingError


# =========================================================
# Fake DB — Cursor-Based (مثل الگوی test_sales_service.py)
# =========================================================

class _FakeCursor:
    def __init__(self, state):
        self.state = state
        self._last_result = None
        self._last_fetchall = None

    def execute(self, sql, params=()):
        normalized = " ".join(sql.split()).upper()
        state = self.state

        if normalized.startswith("SELECT ISNULL(MAX(INVOICENUMBER), 1000)"):
            next_num = max((i["InvoiceNumber"] for i in state["invoices"]), default=1000) + 1
            self._last_result = (next_num,)
            return

        if normalized.startswith("INSERT INTO PURCHASEINVOICES"):
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

        if normalized.startswith("INSERT INTO PURCHASEINVOICEITEMS"):
            (invoice_ref, product_ref, qty, unit_price, discount_amount, total_price,
             description) = params
            new_id = state["_next_item_id"]
            state["_next_item_id"] += 1
            state["items"].append({
                "ID": new_id, "InvoiceRef": invoice_ref, "ProductRef": product_ref,
                "Quantity": qty, "UnitPrice": unit_price, "DiscountAmount": discount_amount,
                "TotalPrice": total_price, "Description": description,
            })
            state["_last_identity"] = new_id
            self._last_result = None
            return

        if normalized.startswith("INSERT INTO PRODUCTPURCHASELAYERS"):
            (product_ref, invoice_item_ref, shamsi_date, original_qty, remaining_qty,
             unit_price) = params
            new_id = state["_next_layer_id"]
            state["_next_layer_id"] += 1
            state["layers"].append({
                "ID": new_id, "ProductRef": product_ref, "InvoiceItemRef": invoice_item_ref,
                "ShamsiDate": shamsi_date, "OriginalQuantity": original_qty,
                "RemainingQuantity": remaining_qty, "UnitPrice": unit_price,
            })
            state["_last_identity"] = new_id
            self._last_result = None
            return

        if normalized.startswith("SELECT COUNT(*) FROM PRODUCTSERIALS WHERE SERIALNUMBER=? AND STATUS=N'INSTOCK'"):
            serial = params[0]
            count = sum(1 for s in state["serials"] if s["SerialNumber"] == serial and s["Status"] == "InStock")
            self._last_result = (count,)
            return

        if normalized.startswith("INSERT INTO PRODUCTSERIALS"):
            product_ref, serial_number, imei, layer_ref = params
            new_id = state["_next_serial_id"]
            state["_next_serial_id"] += 1
            state["serials"].append({
                "ID": new_id, "ProductRef": product_ref, "SerialNumber": serial_number,
                "IMEI": imei, "Status": "InStock", "PurchaseLayerRef": layer_ref,
            })
            state["_last_identity"] = new_id
            self._last_result = None
            return

        if normalized.startswith("UPDATE PRODUCTS SET CURRENTSTOCK = CURRENTSTOCK + ?"):
            qty, price, product_id = params
            state["products"][product_id]["CurrentStock"] += qty
            state["products"][product_id]["PurchasePrice"] = price
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
            is_return = "N'BUYRETURN'" in normalized
            (product_ref, shamsi_date, ref_id, moved_qty, unit_price,
             balance, description, user_ref) = params
            entry = {
                "ProductRef": product_ref, "ShamsiDate": shamsi_date, "RefID": ref_id,
                "UnitPrice": unit_price, "BalanceQuantity": balance,
                "Description": description, "UserRef": user_ref,
            }
            if is_return:
                entry["MovementType"] = "BuyReturn"
                entry["RefTable"] = "PurchaseReturnInvoices"
                entry["InQuantity"] = 0
                entry["OutQuantity"] = moved_qty
            else:
                entry["MovementType"] = "Buy"
                entry["RefTable"] = "PurchaseInvoices"
                entry["InQuantity"] = moved_qty
                entry["OutQuantity"] = 0
            state["cardex"].append(entry)
            self._last_result = None
            return

        # --- هسته create_purchase_return_invoice (Phase 15.6) ---
        if normalized.startswith("SELECT PERSONREF, INVOICENUMBER FROM PURCHASEINVOICES WHERE ID = ? AND ISDELETED = 0"):
            invoice_id = params[0]
            inv = next((i for i in state["invoices"]
                        if i["ID"] == invoice_id and not i.get("IsDeleted", False)), None)
            self._last_result = (inv["PersonRef"], inv["InvoiceNumber"]) if inv else None
            return

        if normalized.startswith("SELECT ISNULL(MAX(INVOICENUMBER), 4000)"):
            next_num = max((r["InvoiceNumber"] for r in state["return_invoices"]), default=4000) + 1
            self._last_result = (next_num,)
            return

        if normalized.startswith("INSERT INTO PURCHASERETURNINVOICES"):
            (invoice_number, person_ref, original_invoice_ref, shamsi_date,
             total_amount, payable_amount, description, user_ref) = params
            new_id = state["_next_return_invoice_id"]
            state["_next_return_invoice_id"] += 1
            state["return_invoices"].append({
                "ID": new_id, "InvoiceNumber": invoice_number, "PersonRef": person_ref,
                "OriginalPurchaseInvoiceRef": original_invoice_ref, "ShamsiDate": shamsi_date,
                "TotalAmount": total_amount, "PayableAmount": payable_amount,
                "Description": description, "UserRef": user_ref,
            })
            state["_last_identity"] = new_id
            self._last_result = None
            return

        if normalized.startswith("SELECT REMAININGQUANTITY FROM PRODUCTPURCHASELAYERS WHERE ID = ?"):
            layer_id = params[0]
            layer = next((l for l in state["layers"] if l["ID"] == layer_id), None)
            self._last_result = (layer["RemainingQuantity"],) if layer else None
            return

        if normalized.startswith("INSERT INTO PURCHASERETURNINVOICEITEMS"):
            (invoice_ref, product_ref, qty, unit_price, total_price, description) = params
            state["return_items"].append({
                "InvoiceRef": invoice_ref, "ProductRef": product_ref, "Quantity": qty,
                "UnitPrice": unit_price, "DiscountAmount": 0, "TotalPrice": total_price,
                "Description": description,
            })
            self._last_result = None
            return

        if normalized.startswith("UPDATE PRODUCTPURCHASELAYERS SET REMAININGQUANTITY = REMAININGQUANTITY - ?"):
            qty, layer_id = params
            layer = next(l for l in state["layers"] if l["ID"] == layer_id)
            layer["RemainingQuantity"] -= qty
            return

        if normalized.startswith("SELECT STATUS, PURCHASELAYERREF FROM PRODUCTSERIALS WHERE ID = ?"):
            serial_id = params[0]
            serial = next((s for s in state["serials"] if s["ID"] == serial_id), None)
            self._last_result = (serial["Status"], serial["PurchaseLayerRef"]) if serial else None
            return

        if normalized.startswith("UPDATE PRODUCTSERIALS SET STATUS = N'RETURNED' WHERE ID = ?"):
            serial_id = params[0]
            serial = next(s for s in state["serials"] if s["ID"] == serial_id)
            serial["Status"] = "Returned"
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
    """جایگزین سبک services.inventory_service.Database (و services.accounting_service.Database
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
            "serials": [],
            "invoices": [],
            "items": [],
            "cardex": [],
            "return_invoices": [],
            "return_items": [],
            "accounts": [
                {"ID": 1, "Code": "1200", "Name": "موجودی کالا", "IsActive": True},
                {"ID": 2, "Code": "1400", "Name": "مالیات خرید", "IsActive": True},
                {"ID": 3, "Code": "5100", "Name": "تخفیف خرید", "IsActive": True},
                {"ID": 4, "Code": "2000", "Name": "حساب‌های پرداختنی", "IsActive": True},
            ],
            "journal_entries": [],
            "journal_lines": [],
            "_next_invoice_id": 1,
            "_next_item_id": 1,
            "_next_layer_id": 1,
            "_next_journal_id": 1,
            "_next_serial_id": 1,
            "_next_return_invoice_id": 1,
            "_last_identity": None,
        }


def setup_function():
    _FakeDatabase.reset()
    inventory_service.Database = _FakeDatabase

    import services.accounting_service as accounting_service
    accounting_service.Database = _FakeDatabase

    import services.audit_service as audit_service
    audit_service.Database = _FakeDatabase

    state = _FakeDatabase._shared_state
    state["products"][1] = {"ID": 1, "CurrentStock": 10, "PurchasePrice": 90.0}


def _basic_item(qty=5, price=200.0, discount=0.0, **extra):
    item = {"product_id": 1, "quantity": qty, "unit_price": price, "discount": discount}
    item.update(extra)
    return item


def _create_base_purchase(qty=5, price=200.0, has_serial=False, serials=None):
    """یک فاکتور خرید پایه می‌سازد که فاکتور برگشت روی آن ثبت می‌شود.
    شناسه فاکتور، شماره فاکتور و شناسه لایه FIFO ساخته‌شده را برمی‌گرداند."""
    item = _basic_item(qty=qty, price=price)
    if has_serial:
        item["has_serial"] = True
        item["serials"] = serials or [f"SN-{i}" for i in range(int(qty))]
    invoice_id, invoice_number = inventory_service.create_purchase_invoice(
        1, "1404-06-01", 0, 0, "", 1, [item]
    )
    state = _FakeDatabase._shared_state
    layer_id = state["layers"][-1]["ID"]
    return invoice_id, invoice_number, layer_id


def _return_item(qty=5, price=200.0, layer_id=1, serial_ids=None, **extra):
    item = {"product_id": 1, "quantity": qty, "unit_price": price, "layer_id": layer_id}
    if serial_ids is not None:
        item["has_serial"] = True
        item["serial_ids"] = serial_ids
    item.update(extra)
    return item


# =========================================================
# بخش ۱ — Regression: رفتار فعلی خرید (نباید با اتصال Ledger بشکند)
# =========================================================

def test_create_purchase_invoice_requires_items():
    with pytest.raises(InventoryError):
        inventory_service.create_purchase_invoice(1, "1404-06-01", 0, 0, "", 1, [])
    state = _FakeDatabase._shared_state
    assert state["invoices"] == []


def test_create_purchase_invoice_rejects_zero_quantity():
    with pytest.raises(InventoryError):
        inventory_service.create_purchase_invoice(1, "1404-06-01", 0, 0, "", 1, [_basic_item(qty=0)])


def test_create_purchase_invoice_rejects_negative_price():
    with pytest.raises(InventoryError):
        inventory_service.create_purchase_invoice(1, "1404-06-01", 0, 0, "", 1, [_basic_item(price=-1)])


def test_create_purchase_invoice_requires_matching_serial_count():
    item = _basic_item(qty=2, has_serial=True, serials=["A1"])
    with pytest.raises(InventoryError):
        inventory_service.create_purchase_invoice(1, "1404-06-01", 0, 0, "", 1, [item])


def test_create_purchase_invoice_stores_raw_unit_price_in_layer():
    """طبق Option C: ProductPurchaseLayers.UnitPrice همیشه قیمت خام است،
    حتی اگر تخفیف قلمی داشته باشیم — تخفیف هرگز در لایه FIFO اعمال نمی‌شود."""
    inventory_service.create_purchase_invoice(
        1, "1404-06-01", 0, 0, "", 1, [_basic_item(qty=5, price=200.0, discount=50.0)]
    )
    state = _FakeDatabase._shared_state
    layer = state["layers"][0]
    assert layer["UnitPrice"] == 200.0  # قیمت خام، نه (200 - تخفیف)
    assert layer["OriginalQuantity"] == 5
    assert layer["RemainingQuantity"] == 5


def test_create_purchase_invoice_updates_stock_and_cardex():
    inventory_service.create_purchase_invoice(
        1, "1404-06-01", 0, 0, "", 1, [_basic_item(qty=5, price=200.0)]
    )
    state = _FakeDatabase._shared_state
    assert state["products"][1]["CurrentStock"] == 15
    assert len(state["cardex"]) == 1
    assert state["cardex"][0]["InQuantity"] == 5
    assert state["cardex"][0]["BalanceQuantity"] == 15


def test_create_purchase_invoice_marks_serials_in_stock():
    invoice_id, _ = inventory_service.create_purchase_invoice(
        1, "1404-06-01", 0, 0, "", 1,
        [_basic_item(qty=1, price=200.0, has_serial=True, serials=["SN-001"])]
    )
    state = _FakeDatabase._shared_state
    assert state["serials"][0]["SerialNumber"] == "SN-001"
    assert state["serials"][0]["Status"] == "InStock"


def test_create_purchase_invoice_rejects_duplicate_serial_in_stock():
    state = _FakeDatabase._shared_state
    state["serials"].append({"ProductRef": 1, "SerialNumber": "SN-DUP", "Status": "InStock"})
    with pytest.raises(InventoryError):
        inventory_service.create_purchase_invoice(
            1, "1404-06-01", 0, 0, "", 1,
            [_basic_item(qty=1, price=200.0, has_serial=True, serials=["SN-DUP"])]
        )
    assert state["invoices"] == []


# =========================================================
# بخش ۲ — اتصال Ledger: سند حسابداری دوطرفه (Option C)
# =========================================================

def test_create_purchase_invoice_posts_balanced_journal_entry():
    invoice_id, invoice_number = inventory_service.create_purchase_invoice(
        1, "1404-06-01", 0, 0, "", 1, [_basic_item(qty=5, price=200.0)]
    )
    state = _FakeDatabase._shared_state

    assert len(state["journal_entries"]) == 1
    entry = state["journal_entries"][0]
    assert entry["SourceTable"] == "PurchaseInvoices"
    assert entry["SourceID"] == invoice_id

    lines = state["journal_lines"]
    total_debit = sum(l["Debit"] for l in lines)
    total_credit = sum(l["Credit"] for l in lines)
    assert total_debit == total_credit  # موازنه واقعی

    accounts_by_id = {a["ID"]: a["Code"] for a in state["accounts"]}
    debit_inv = next(l["Debit"] for l in lines if accounts_by_id[l["AccountRef"]] == "1200")
    credit_ap = next(l["Credit"] for l in lines if accounts_by_id[l["AccountRef"]] == "2000")

    # 5*200 = 1000، بدون تخفیف/مالیات
    assert debit_inv == 1000.0
    assert credit_ap == 1000.0
    assert all(accounts_by_id[l["AccountRef"]] != "1400" for l in lines)
    assert all(accounts_by_id[l["AccountRef"]] != "5100" for l in lines)


def test_create_purchase_invoice_journal_matches_all_four_accounts_with_tax_and_discounts():
    """اثبات دقیق چهار رقم مشخص‌شده در Brief:
    1200 = SUM(qty × raw_price) ; 1400 = TaxAmount ;
    5100 = item_discount_total + header_discount ; 2000 = PayableAmount."""
    items = [
        _basic_item(qty=5, price=200.0, discount=30.0),   # raw=1000, item_disc=30
        _basic_item(qty=2, price=100.0, discount=10.0),   # raw=200,  item_disc=10
    ]
    header_discount = 15.0
    tax_amount = 42.0

    invoice_id, _ = inventory_service.create_purchase_invoice(
        1, "1404-06-01", header_discount, tax_amount, "", 1, items
    )
    state = _FakeDatabase._shared_state
    accounts_by_id = {a["ID"]: a["Code"] for a in state["accounts"]}
    lines = state["journal_lines"]

    debit_inv = next(l["Debit"] for l in lines if accounts_by_id[l["AccountRef"]] == "1200")
    debit_tax = next(l["Debit"] for l in lines if accounts_by_id[l["AccountRef"]] == "1400")
    credit_disc = next(l["Credit"] for l in lines if accounts_by_id[l["AccountRef"]] == "5100")
    credit_ap = next(l["Credit"] for l in lines if accounts_by_id[l["AccountRef"]] == "2000")

    raw_inventory = 5 * 200.0 + 2 * 100.0  # = 1200 (قیمت خام، بدون تخفیف)
    item_discount_total = 30.0 + 10.0       # = 40
    invoice = state["invoices"][0]

    assert debit_inv == raw_inventory == 1200.0
    assert debit_tax == tax_amount == 42.0
    assert credit_disc == item_discount_total + header_discount == 55.0
    assert credit_ap == invoice["PayableAmount"] == payable_expected(
        raw_inventory, item_discount_total, header_discount, tax_amount
    )
    assert sum(l["Debit"] for l in lines) == sum(l["Credit"] for l in lines)


def payable_expected(raw_inventory, item_discount_total, header_discount, tax_amount):
    total_amount = raw_inventory - item_discount_total
    return total_amount - header_discount + tax_amount


def test_create_purchase_invoice_does_not_change_fifo_layer_price_when_discount_present():
    """تضمین Option C: حتی وقتی 5100 در سند حسابداری تخفیف را ثبت می‌کند،
    خودِ ProductPurchaseLayers.UnitPrice دست‌نخورده (قیمت خام) باقی می‌ماند."""
    inventory_service.create_purchase_invoice(
        1, "1404-06-01", 20.0, 0, "", 1, [_basic_item(qty=5, price=200.0, discount=50.0)]
    )
    state = _FakeDatabase._shared_state
    layer = state["layers"][0]
    assert layer["UnitPrice"] == 200.0

    accounts_by_id = {a["ID"]: a["Code"] for a in state["accounts"]}
    credit_disc = next(l["Credit"] for l in state["journal_lines"]
                        if accounts_by_id[l["AccountRef"]] == "5100")
    assert credit_disc == 70.0  # 50 (قلمی) + 20 (سربرگ)


def test_create_purchase_invoice_journal_entry_number_increments_across_invoices():
    inventory_service.create_purchase_invoice(1, "1404-06-01", 0, 0, "", 1, [_basic_item(qty=2, price=200.0)])
    inventory_service.create_purchase_invoice(1, "1404-06-02", 0, 0, "", 1, [_basic_item(qty=2, price=200.0)])
    state = _FakeDatabase._shared_state
    numbers = sorted(e["EntryNumber"] for e in state["journal_entries"])
    assert numbers == [1, 2]


def test_create_purchase_invoice_rolls_back_everything_when_ledger_account_missing():
    """اگر Chart of Accounts حساب لازم (مثلاً 1400) را نداشته باشد، کل
    فاکتور خرید (سربرگ، اقلام، لایه FIFO، سریال، موجودی، کاردکس) باید
    Rollback شود — نه اینکه فاکتور بدون سند حسابداری موازنه‌شده باقی بماند."""
    state = _FakeDatabase._shared_state
    state["accounts"] = [a for a in state["accounts"] if a["Code"] != "1400"]

    with pytest.raises(AccountingError):
        inventory_service.create_purchase_invoice(
            1, "1404-06-01", 0, tax_amount=50, description="", user_id=1,
            items=[_basic_item(qty=5, price=200.0)]
        )

    assert state["invoices"] == []
    assert state["items"] == []
    assert state["layers"] == []
    assert state["journal_entries"] == []
    assert state["journal_lines"] == []
    assert state["products"][1]["CurrentStock"] == 10  # موجودی هم دست‌نخورده


def test_create_purchase_invoice_pure_validation_failure_never_touches_ledger():
    state = _FakeDatabase._shared_state
    with pytest.raises(InventoryError):
        inventory_service.create_purchase_invoice(1, "1404-06-01", 0, 0, "", 1, [])
    assert state["journal_entries"] == []
    assert state["journal_lines"] == []


# =========================================================
# بخش ۳ — _build_purchase_journal_lines: تست خالص (بدون دیتابیس)
# =========================================================

def test_build_purchase_journal_lines_balanced_pure():
    lines = _build_purchase_journal_lines(
        inventory_amount=1000, tax_amount=0, discount_total=0, payable=1000
    )
    assert sum(l.get("debit", 0) for l in lines) == sum(l.get("credit", 0) for l in lines)
    codes = {l["account_code"] for l in lines}
    assert codes == {"1200", "2000"}


def test_build_purchase_journal_lines_skips_zero_tax_and_discount_lines():
    lines = _build_purchase_journal_lines(
        inventory_amount=1000, tax_amount=0, discount_total=0, payable=1000
    )
    assert all(l["account_code"] not in ("1400", "5100") for l in lines)


def test_build_purchase_journal_lines_includes_tax_and_discount_lines_when_present():
    lines = _build_purchase_journal_lines(
        inventory_amount=1200, tax_amount=42, discount_total=55, payable=1187
    )
    tax_line = next(l for l in lines if l["account_code"] == "1400")
    disc_line = next(l for l in lines if l["account_code"] == "5100")
    assert tax_line["debit"] == 42
    assert disc_line["credit"] == 55
    assert sum(l.get("debit", 0) for l in lines) == sum(l.get("credit", 0) for l in lines)


def test_build_purchase_journal_lines_uses_raw_inventory_amount_not_net_of_discount():
    """inventory_amount باید SUM(qty × raw_price) باشد؛ تابع نباید خودش
    تخفیف را از موجودی کم کند — این وظیفه ردیف 5100 است، نه ردیف 1200."""
    lines = _build_purchase_journal_lines(
        inventory_amount=1200, tax_amount=0, discount_total=40, payable=1160
    )
    inv_line = next(l for l in lines if l["account_code"] == "1200")
    assert inv_line["debit"] == 1200  # نه 1200-40


# =========================================================
# Phase 15.6 — اتصال برگشت از خرید به حسابداری دوطرفه
# =========================================================
#
# ۱) Regression — رفتار **فعلی** create_purchase_return_invoice (کاهش لایه
#    FIFO، کاهش موجودی، برگرداندن وضعیت سریال/IMEI، کاردکس BuyReturn،
#    اعتبارسنجی ورودی، رد برگشت بیش از موجودی باقیمانده لایه، Rollback) که
#    باید دقیقاً همان‌طور که قبل از این فاز کار می‌کرد ادامه یابد، به‌علاوه
#    رفع باگ از قبل موجود: فراخوانی create_audit_entry با متغیر نامعتبر
#    invoice_id باعث می‌شد یک برگشت موفق، بعد از commit، با NameError خطا
#    بدهد. این فاز آن متغیر را به return_invoice_id اصلاح می‌کند.
# ۲) اتصال Ledger — سند حسابداری دوطرفه‌ای که حالا برای هر فاکتور برگشت از
#    خرید در همان Transaction اتمیک ساخته می‌شود:
#        بدهکار   2000 حساب‌های پرداختنی = TotalAmount
#        بستانکار 1200 موجودی کالا       = TotalAmount
#    بدون مالیات/تخفیف (طبق تصمیم صریح Brief).

def test_create_purchase_return_invoice_requires_at_least_one_item():
    _create_base_purchase(qty=5, price=200.0)
    with pytest.raises(InventoryError):
        inventory_service.create_purchase_return_invoice(1, "1404-06-05", "", 1, [])
    state = _FakeDatabase._shared_state
    assert state["return_invoices"] == []


def test_create_purchase_return_invoice_ignores_zero_quantity_items_and_then_rejects_empty():
    _create_base_purchase(qty=5, price=200.0)
    with pytest.raises(InventoryError):
        inventory_service.create_purchase_return_invoice(
            1, "1404-06-05", "", 1, [_return_item(qty=0, price=200.0, layer_id=1)]
        )


def test_create_purchase_return_invoice_rejects_negative_price():
    _create_base_purchase(qty=5, price=200.0)
    with pytest.raises(InventoryError):
        inventory_service.create_purchase_return_invoice(
            1, "1404-06-05", "", 1, [_return_item(qty=1, price=-1, layer_id=1)]
        )


def test_create_purchase_return_invoice_requires_matching_serial_count():
    _create_base_purchase(qty=2, price=200.0, has_serial=True)
    item = _return_item(qty=2, price=200.0, layer_id=1, serial_ids=[1])  # فقط یک سریال به‌جای دو
    with pytest.raises(InventoryError):
        inventory_service.create_purchase_return_invoice(1, "1404-06-05", "", 1, [item])


def test_create_purchase_return_invoice_rejects_unknown_original_invoice():
    with pytest.raises(InventoryError):
        inventory_service.create_purchase_return_invoice(
            999, "1404-06-05", "", 1, [_return_item(qty=1, price=200.0, layer_id=1)]
        )


def test_create_purchase_return_invoice_decrements_fifo_remaining_quantity():
    _create_base_purchase(qty=5, price=200.0)
    inventory_service.create_purchase_return_invoice(
        1, "1404-06-05", "", 1, [_return_item(qty=2, price=200.0, layer_id=1)]
    )
    state = _FakeDatabase._shared_state
    assert state["layers"][0]["RemainingQuantity"] == 3


def test_create_purchase_return_invoice_decrements_product_stock():
    _create_base_purchase(qty=5, price=200.0)  # CurrentStock: 10 + 5 = 15
    inventory_service.create_purchase_return_invoice(
        1, "1404-06-05", "", 1, [_return_item(qty=2, price=200.0, layer_id=1)]
    )
    state = _FakeDatabase._shared_state
    assert state["products"][1]["CurrentStock"] == 13


def test_create_purchase_return_invoice_marks_serials_returned():
    _create_base_purchase(qty=1, price=200.0, has_serial=True, serials=["SN-R1"])
    state = _FakeDatabase._shared_state
    serial_id = state["serials"][0]["ID"]
    inventory_service.create_purchase_return_invoice(
        1, "1404-06-05", "", 1, [_return_item(qty=1, price=200.0, layer_id=1, serial_ids=[serial_id])]
    )
    assert state["serials"][0]["Status"] == "Returned"


def test_create_purchase_return_invoice_rejects_serial_not_in_stock():
    _create_base_purchase(qty=1, price=200.0, has_serial=True, serials=["SN-R2"])
    state = _FakeDatabase._shared_state
    serial_id = state["serials"][0]["ID"]
    state["serials"][0]["Status"] = "Sold"  # قبلاً فروخته شده
    with pytest.raises(InventoryError):
        inventory_service.create_purchase_return_invoice(
            1, "1404-06-05", "", 1, [_return_item(qty=1, price=200.0, layer_id=1, serial_ids=[serial_id])]
        )


def test_create_purchase_return_invoice_creates_buyreturn_cardex_entry():
    _create_base_purchase(qty=5, price=200.0)
    return_invoice_id, _ = inventory_service.create_purchase_return_invoice(
        1, "1404-06-05", "", 1, [_return_item(qty=2, price=200.0, layer_id=1)]
    )
    state = _FakeDatabase._shared_state
    cardex_entry = state["cardex"][-1]
    assert cardex_entry["MovementType"] == "BuyReturn"
    assert cardex_entry["RefTable"] == "PurchaseReturnInvoices"
    assert cardex_entry["RefID"] == return_invoice_id
    assert cardex_entry["OutQuantity"] == 2
    assert cardex_entry["InQuantity"] == 0


def test_create_purchase_return_invoice_rejects_over_return_beyond_remaining_layer_quantity():
    """اگر بخشی از لایه قبلاً فروخته شده باشد (RemainingQuantity کمتر از
    OriginalQuantity)، برگشت بیش از باقیمانده باید رد شود."""
    _create_base_purchase(qty=5, price=200.0)
    state = _FakeDatabase._shared_state
    state["layers"][0]["RemainingQuantity"] = 3  # فرض: ۲ واحد قبلاً فروخته شده
    with pytest.raises(InventoryError):
        inventory_service.create_purchase_return_invoice(
            1, "1404-06-05", "", 1, [_return_item(qty=4, price=200.0, layer_id=1)]
        )
    assert state["return_invoices"] == []


def test_create_purchase_return_invoice_succeeds_without_nameerror_and_writes_audit():
    """رگرسیون اصلی این فاز: قبلاً یک برگشت موفق بعد از commit با NameError
    (متغیر نامعتبر invoice_id در create_audit_entry) خطا می‌داد. حالا باید
    بدون هیچ Exception ای کامل شود."""
    _create_base_purchase(qty=5, price=200.0)
    return_invoice_id, invoice_number = inventory_service.create_purchase_return_invoice(
        1, "1404-06-05", "", 1, [_return_item(qty=2, price=200.0, layer_id=1)]
    )
    assert return_invoice_id is not None
    assert invoice_number is not None
    state = _FakeDatabase._shared_state
    assert len(state["return_invoices"]) == 1


def test_create_purchase_return_invoice_rolls_back_everything_on_failure():
    """اگر یکی از اقلام برگشت نامعتبر باشد (مثلاً بیش از موجودی باقیمانده
    لایه)، کل فاکتور برگشت (سربرگ، اقلام، لایه FIFO، سریال، موجودی، کاردکس،
    سند حسابداری) باید Rollback شود — نه فقط بخشی از آن."""
    _create_base_purchase(qty=5, price=200.0)
    state = _FakeDatabase._shared_state
    stock_before = state["products"][1]["CurrentStock"]
    journal_entries_before = len(state["journal_entries"])  # سند فاکتور خرید پایه

    with pytest.raises(InventoryError):
        inventory_service.create_purchase_return_invoice(
            1, "1404-06-05", "", 1, [
                _return_item(qty=2, price=200.0, layer_id=1),   # قلم معتبر
                _return_item(qty=100, price=200.0, layer_id=1),  # قلم نامعتبر (بیش از باقیمانده)
            ]
        )

    assert state["return_invoices"] == []
    assert state["return_items"] == []
    assert len(state["journal_entries"]) == journal_entries_before  # هیچ سند جدیدی اضافه نشد
    assert state["products"][1]["CurrentStock"] == stock_before
    assert state["layers"][0]["RemainingQuantity"] == 5  # لایه FIFO دست‌نخورده


# --- اتصال Ledger ---

def test_create_purchase_return_invoice_posts_balanced_journal_entry():
    _create_base_purchase(qty=5, price=200.0)
    return_invoice_id, _ = inventory_service.create_purchase_return_invoice(
        1, "1404-06-05", "", 1, [_return_item(qty=2, price=200.0, layer_id=1)]
    )
    state = _FakeDatabase._shared_state

    # یک سند برای فاکتور خرید پایه (Phase 15.3) + یک سند برای این برگشت
    assert len(state["journal_entries"]) == 2
    entry = next(e for e in state["journal_entries"] if e["SourceTable"] == "PurchaseReturnInvoices")
    assert entry["SourceID"] == return_invoice_id

    # فقط ردیف‌های همین سند برگشت (نه سند فاکتور خرید پایه) را بررسی می‌کنیم
    lines = [l for l in state["journal_lines"] if l["JournalEntryRef"] == entry["ID"]]
    total_debit = sum(l["Debit"] for l in lines)
    total_credit = sum(l["Credit"] for l in lines)
    assert total_debit == total_credit  # موازنه واقعی

    accounts_by_id = {a["ID"]: a["Code"] for a in state["accounts"]}
    debit_ap = next(l["Debit"] for l in lines if accounts_by_id[l["AccountRef"]] == "2000")
    credit_inv = next(l["Credit"] for l in lines if accounts_by_id[l["AccountRef"]] == "1200")

    # 2 * 200 = 400
    assert debit_ap == 400.0
    assert credit_inv == 400.0


def test_create_purchase_return_invoice_journal_entry_number_increments_after_purchase_entry():
    """شماره سند حسابداری برگشت باید ادامهٔ سری سند فاکتور خرید اصلی باشد،
    نه از نو شروع شود (هر دو در همان دفتر روزنامه مشترک ثبت می‌شوند)."""
    _create_base_purchase(qty=5, price=200.0)  # سند شماره ۱ (فاکتور خرید)
    inventory_service.create_purchase_return_invoice(
        1, "1404-06-05", "", 1, [_return_item(qty=2, price=200.0, layer_id=1)]
    )
    state = _FakeDatabase._shared_state
    numbers = sorted(e["EntryNumber"] for e in state["journal_entries"])
    assert numbers == [1, 2]


def test_create_purchase_return_invoice_rolls_back_when_account_missing():
    """اگر Chart of Accounts حساب لازم (1200 یا 2000) را نداشته باشد، کل
    فاکتور برگشت باید Rollback شود."""
    _create_base_purchase(qty=5, price=200.0)
    state = _FakeDatabase._shared_state
    journal_entries_before = len(state["journal_entries"])
    state["accounts"] = [a for a in state["accounts"] if a["Code"] != "1200"]

    with pytest.raises(AccountingError):
        inventory_service.create_purchase_return_invoice(
            1, "1404-06-05", "", 1, [_return_item(qty=2, price=200.0, layer_id=1)]
        )

    assert state["return_invoices"] == []
    assert len(state["journal_entries"]) == journal_entries_before  # هیچ سند جدیدی اضافه نشد
    assert state["layers"][0]["RemainingQuantity"] == 5
    assert state["products"][1]["CurrentStock"] == 15  # موجودی هم دست‌نخورده


def test_create_purchase_return_invoice_rolls_back_when_account_inactive():
    _create_base_purchase(qty=5, price=200.0)
    state = _FakeDatabase._shared_state
    journal_entries_before = len(state["journal_entries"])
    next(a for a in state["accounts"] if a["Code"] == "2000")["IsActive"] = False

    with pytest.raises(AccountingError):
        inventory_service.create_purchase_return_invoice(
            1, "1404-06-05", "", 1, [_return_item(qty=2, price=200.0, layer_id=1)]
        )

    assert state["return_invoices"] == []
    assert len(state["journal_entries"]) == journal_entries_before


# --- _build_purchase_return_journal_lines: تست خالص (بدون دیتابیس) ---

def test_build_purchase_return_journal_lines_balanced_pure():
    lines = _build_purchase_return_journal_lines(total_amount=400.0)
    assert sum(l.get("debit", 0) for l in lines) == sum(l.get("credit", 0) for l in lines)
    codes = {l["account_code"] for l in lines}
    assert codes == {"2000", "1200"}


def test_build_purchase_return_journal_lines_correct_debit_credit_sides():
    lines = _build_purchase_return_journal_lines(total_amount=400.0)
    debit_line = next(l for l in lines if l["account_code"] == "2000")
    credit_line = next(l for l in lines if l["account_code"] == "1200")
    assert debit_line["debit"] == 400.0
    assert "credit" not in debit_line or debit_line.get("credit", 0) == 0
    assert credit_line["credit"] == 400.0
    assert "debit" not in credit_line or credit_line.get("debit", 0) == 0


def test_build_purchase_return_journal_lines_returns_empty_for_zero_amount():
    """اگر مبلغ کل صفر باشد (مثلاً هر دو ردیف صفر)، هیچ ردیفی نباید ساخته
    شود؛ فراخوان نباید یک سند حسابداری خالی Post کند."""
    lines = _build_purchase_return_journal_lines(total_amount=0.0)
    assert lines == []
