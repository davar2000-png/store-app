# -*- coding: utf-8 -*-
"""
Phase 15.6.5 — برگشت از فروش (Sales Return Core) + اتصال به حسابداری دوطرفه

از یک Fake Cursor/Connection سبک استفاده می‌شود (دقیقاً همان الگوی
tests/test_sales_service.py و tests/test_inventory_service.py) که رفتار
Cursor واقعی pyodbc را برای دقیقاً همان Queryهایی که
sales_service.create_sales_invoice، sales_service.create_sales_return_invoice
و accounting_service._post_journal_entry_on_cursor صادر می‌کنند شبیه‌سازی
می‌کند و از یک Snapshot برای Rollback واقعی استفاده می‌کند.

هر فاکتور فروش پایه (base sale) با خودِ sales_service.create_sales_invoice
واقعی ساخته می‌شود (نه Mock دستی) تا SalesInvoiceItemLayers دقیقاً همان
چیزی باشد که خودِ سیستم در فروش واقعی می‌سازد — پس برگشت روی همان داده
واقعی تست می‌شود، نه یک Fixture دستی که ممکن است با واقعیت فرق کند.
"""

import copy

import pytest

import services.sales_service as sales_service
from services.sales_service import (
    SalesError,
    _build_sales_return_journal_lines,
)
from services.accounting_service import AccountingError


# =========================================================
# Fake DB — Cursor-Based (مثل الگوی test_sales_service.py / test_inventory_service.py)
# =========================================================

class _FakeCursor:
    def __init__(self, state):
        self.state = state
        self._last_result = None
        self._last_fetchall = None

    def execute(self, sql, params=()):
        normalized = " ".join(sql.split()).upper()
        state = self.state

        # --- create_sales_invoice (فروش پایه — Phase 15.2، دست‌نخورده) ---

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
                "PayableAmount": payable_amount, "Description": description,
                "UserRef": user_ref, "IsDeleted": False,
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

        if normalized.startswith("UPDATE PRODUCTPURCHASELAYERS SET REMAININGQUANTITY = REMAININGQUANTITY - ?"):
            take, layer_id = params
            for l in state["layers"]:
                if l["ID"] == layer_id:
                    l["RemainingQuantity"] -= take
            return

        if normalized.startswith("INSERT INTO SALESINVOICEITEMLAYERS"):
            item_ref, layer_ref, qty, unit_price = params
            new_id = state["_next_item_layer_id"]
            state["_next_item_layer_id"] += 1
            state["item_layers"].append({
                "ID": new_id, "SalesInvoiceItemRef": item_ref, "PurchaseLayerRef": layer_ref,
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

        if normalized.startswith("UPDATE PRODUCTS SET CURRENTSTOCK = CURRENTSTOCK + ?"):
            qty, product_id = params
            state["products"][product_id]["CurrentStock"] += qty
            return

        if normalized.startswith("SELECT CURRENTSTOCK FROM PRODUCTS WHERE ID = ?"):
            product_id = params[0]
            self._last_result = (state["products"][product_id]["CurrentStock"],)
            return

        if normalized.startswith("INSERT INTO PRODUCTCARDEX"):
            if "N'SELL'" in normalized:
                (product_ref, shamsi_date, invoice_ref, out_qty, unit_price,
                 balance, description, user_ref) = params
                state["cardex"].append({
                    "ProductRef": product_ref, "ShamsiDate": shamsi_date, "RefID": invoice_ref,
                    "MovementType": "Sell", "RefTable": "SalesInvoices",
                    "InQuantity": 0, "OutQuantity": out_qty, "UnitPrice": unit_price,
                    "BalanceQuantity": balance, "Description": description, "UserRef": user_ref,
                })
            elif "N'SELLRETURN'" in normalized:
                (product_ref, shamsi_date, invoice_ref, in_qty, unit_price,
                 balance, description, user_ref) = params
                state["cardex"].append({
                    "ProductRef": product_ref, "ShamsiDate": shamsi_date, "RefID": invoice_ref,
                    "MovementType": "SellReturn", "RefTable": "SalesReturnInvoices",
                    "InQuantity": in_qty, "OutQuantity": 0, "UnitPrice": unit_price,
                    "BalanceQuantity": balance, "Description": description, "UserRef": user_ref,
                })
            else:
                raise AssertionError(f"Unexpected ProductCardex insert: {sql}")
            self._last_result = None
            return

        # --- create_sales_return_invoice (Phase 15.6.5) ---

        if normalized.startswith("SELECT PERSONREF, INVOICENUMBER FROM SALESINVOICES WHERE ID = ? AND ISDELETED = 0"):
            invoice_id = params[0]
            inv = next((i for i in state["invoices"] if i["ID"] == invoice_id and not i.get("IsDeleted")), None)
            self._last_result = (inv["PersonRef"], inv["InvoiceNumber"]) if inv else None
            return

        if normalized.startswith("SELECT PRODUCTREF, UNITPRICE FROM SALESINVOICEITEMS WHERE ID = ? AND INVOICEREF = ?"):
            item_id, invoice_ref = params
            it = next((i for i in state["items"] if i["ID"] == item_id and i["InvoiceRef"] == invoice_ref), None)
            self._last_result = (it["ProductRef"], it["UnitPrice"]) if it else None
            return

        if normalized.startswith("SELECT ISNULL(MAX(INVOICENUMBER), 2999)"):
            next_num = max((i["InvoiceNumber"] for i in state["return_invoices"]), default=2999) + 1
            self._last_result = (next_num,)
            return

        if normalized.startswith("INSERT INTO SALESRETURNINVOICES"):
            (invoice_number, person_ref, original_ref, shamsi_date,
             total_amount, tax_amount, payable_amount, description, user_ref) = params
            new_id = state["_next_return_invoice_id"]
            state["_next_return_invoice_id"] += 1
            state["return_invoices"].append({
                "ID": new_id, "InvoiceNumber": invoice_number, "PersonRef": person_ref,
                "OriginalSalesInvoiceRef": original_ref, "ShamsiDate": shamsi_date,
                "TotalAmount": total_amount, "TaxAmount": tax_amount,
                "PayableAmount": payable_amount, "Description": description, "UserRef": user_ref,
            })
            state["_last_identity"] = new_id
            self._last_result = None
            return

        if normalized.startswith("SELECT ID, PURCHASELAYERREF, QUANTITY, UNITPRICE FROM SALESINVOICEITEMLAYERS"):
            item_ref = params[0]
            recs = [l for l in state["item_layers"] if l["SalesInvoiceItemRef"] == item_ref]
            recs.sort(key=lambda l: l["ID"])
            self._last_fetchall = [(l["ID"], l["PurchaseLayerRef"], l["Quantity"], l["UnitPrice"]) for l in recs]
            return

        if normalized.startswith("SELECT ISNULL(SUM(QUANTITY), 0) FROM SALESRETURNINVOICEITEMLAYERS"):
            source_layer_id = params[0]
            total = sum(
                r["Quantity"] for r in state["return_item_layers"]
                if r["SalesInvoiceItemLayerRef"] == source_layer_id
            )
            self._last_result = (total,)
            return

        if normalized.startswith("SELECT STATUS, SOLDININVOICEITEMREF, PURCHASELAYERREF FROM PRODUCTSERIALS WHERE ID = ?"):
            serial_id = params[0]
            s = state["serials"].get(serial_id)
            self._last_result = (s["Status"], s.get("SoldInInvoiceItemRef"), s["PurchaseLayerRef"]) if s else None
            return

        if normalized.startswith("SELECT UNITPRICE FROM PRODUCTPURCHASELAYERS WHERE ID = ?"):
            layer_id = params[0]
            layer = next((l for l in state["layers"] if l["ID"] == layer_id), None)
            self._last_result = (layer["UnitPrice"],) if layer else None
            return

        if normalized.startswith("INSERT INTO SALESRETURNINVOICEITEMS"):
            (invoice_ref, item_ref, product_ref, qty, unit_price, total_price,
             cost_amount, description) = params
            new_id = state["_next_return_item_id"]
            state["_next_return_item_id"] += 1
            state["return_items"].append({
                "ID": new_id, "InvoiceRef": invoice_ref, "SalesInvoiceItemRef": item_ref,
                "ProductRef": product_ref, "Quantity": qty, "UnitPrice": unit_price,
                "TotalPrice": total_price, "CostAmount": cost_amount, "Description": description,
            })
            state["_last_identity"] = new_id
            self._last_result = None
            return

        if normalized.startswith("INSERT INTO SALESRETURNINVOICEITEMLAYERS"):
            return_item_ref, source_layer_ref, purchase_layer_ref, qty, unit_price = params
            state["return_item_layers"].append({
                "SalesReturnInvoiceItemRef": return_item_ref,
                "SalesInvoiceItemLayerRef": source_layer_ref,
                "PurchaseLayerRef": purchase_layer_ref,
                "Quantity": qty, "UnitPrice": unit_price,
            })
            self._last_result = None
            return

        if normalized.startswith("UPDATE PRODUCTPURCHASELAYERS SET REMAININGQUANTITY = REMAININGQUANTITY + ? WHERE"):
            take, layer_id = params
            for l in state["layers"]:
                if l["ID"] == layer_id:
                    l["RemainingQuantity"] += take
            return

        if normalized.startswith("UPDATE PRODUCTPURCHASELAYERS SET REMAININGQUANTITY = REMAININGQUANTITY + 1 WHERE"):
            layer_id = params[0]
            for l in state["layers"]:
                if l["ID"] == layer_id:
                    l["RemainingQuantity"] += 1
            return

        if normalized.startswith("UPDATE PRODUCTSERIALS SET STATUS = N'INSTOCK' WHERE ID = ?"):
            serial_id = params[0]
            s = state["serials"].get(serial_id)
            if s:
                s["Status"] = "InStock"
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
    """Snapshot در connect() و بازگردانی کامل آن در rollback()."""

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
    _shared_state = None

    def __init__(self):
        self._conn = None

    def connect(self):
        self._conn = _FakeConnection(self.__class__._shared_state)
        return self._conn

    def close(self):
        pass

    def execute(self, query, params=()):
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
            "return_invoices": [],
            "return_items": [],
            "return_item_layers": [],
            "accounts": [
                {"ID": 1, "Code": "1100", "Name": "دریافتنی", "IsActive": True},
                {"ID": 2, "Code": "1200", "Name": "موجودی کالا", "IsActive": True},
                {"ID": 3, "Code": "2200", "Name": "مالیات", "IsActive": True},
                {"ID": 4, "Code": "4000", "Name": "درآمد فروش", "IsActive": True},
                {"ID": 5, "Code": "5000", "Name": "بهای تمام‌شده", "IsActive": True},
                {"ID": 6, "Code": "4100", "Name": "برگشت از فروش", "IsActive": True},
            ],
            "journal_entries": [],
            "journal_lines": [],
            "_next_invoice_id": 1,
            "_next_item_id": 1,
            "_next_item_layer_id": 1,
            "_next_return_invoice_id": 1,
            "_next_return_item_id": 1,
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


def _basic_item(qty=5, price=200.0, discount=0.0, **extra):
    item = {"product_id": 1, "quantity": qty, "unit_price": price, "discount": discount}
    item.update(extra)
    return item


def _create_base_sale(qty=10, price=200.0, layers=None, has_serial=False, serial_ids=None):
    """یک کالای پایه (Product ID=1) با لایه(های) خرید داده‌شده می‌سازد و یک
    فاکتور فروش واقعی (با خودِ create_sales_invoice) روی آن ثبت می‌کند تا
    SalesInvoiceItemLayers دقیقاً همان چیزی باشد که خودِ سیستم تولید می‌کند."""
    state = _FakeDatabase._shared_state
    if 1 not in state["products"]:
        state["products"][1] = {"ID": 1, "CurrentStock": 0, "PurchasePrice": 100.0}

    layers = layers or [(10000, price)]
    for remaining, layer_price in layers:
        new_id = len(state["layers"]) + 1
        state["layers"].append({
            "ID": new_id, "ProductRef": 1, "RemainingQuantity": remaining, "UnitPrice": layer_price,
        })
    state["products"][1]["CurrentStock"] += sum(r for r, _ in layers)

    item = _basic_item(qty=qty, price=price + 50.0, has_serial=has_serial, serial_ids=serial_ids or [])
    invoice_id, invoice_number = sales_service.create_sales_invoice(
        1, "1404-06-01", 0, 0, "", 1, [item]
    )
    item_id = state["items"][-1]["ID"]
    return invoice_id, invoice_number, item_id


def _return_item(item_id, qty, has_serial=False, serial_ids=None, **extra):
    d = {
        "item_id": item_id, "quantity": qty, "has_serial": has_serial,
        "serial_ids": serial_ids or [], "product_name": "کالای تست",
    }
    d.update(extra)
    return d


# =========================================================
# بخش ۱ — اعتبارسنجی ورودی
# =========================================================

def test_create_sales_return_invoice_requires_at_least_one_item():
    invoice_id, _, item_id = _create_base_sale(qty=5)
    with pytest.raises(SalesError):
        sales_service.create_sales_return_invoice(invoice_id, "1404-06-05", 0, "", 1, [])
    assert _FakeDatabase._shared_state["return_invoices"] == []


def test_create_sales_return_invoice_ignores_zero_quantity_items_and_then_rejects_empty():
    invoice_id, _, item_id = _create_base_sale(qty=5)
    with pytest.raises(SalesError):
        sales_service.create_sales_return_invoice(
            invoice_id, "1404-06-05", 0, "", 1, [_return_item(item_id, qty=0)]
        )


def test_create_sales_return_invoice_requires_matching_serial_count():
    state = _FakeDatabase._shared_state
    state["serials"][501] = {"ID": 501, "ProductRef": 1, "Status": "InStock", "PurchaseLayerRef": 1}
    state["serials"][502] = {"ID": 502, "ProductRef": 1, "Status": "InStock", "PurchaseLayerRef": 1}
    invoice_id, _, item_id = _create_base_sale(
        qty=2, layers=[(2, 100.0)], has_serial=True, serial_ids=[501, 502]
    )
    item = _return_item(item_id, qty=2, has_serial=True, serial_ids=[501])  # فقط یک سریال به‌جای دو
    with pytest.raises(SalesError):
        sales_service.create_sales_return_invoice(invoice_id, "1404-06-05", 0, "", 1, [item])


def test_create_sales_return_invoice_rejects_duplicate_serial_in_same_request():
    state = _FakeDatabase._shared_state
    state["serials"][501] = {"ID": 501, "ProductRef": 1, "Status": "InStock", "PurchaseLayerRef": 1}
    invoice_id, _, item_id = _create_base_sale(qty=1, layers=[(1, 100.0)], has_serial=True, serial_ids=[501])
    item = _return_item(item_id, qty=2, has_serial=True, serial_ids=[501, 501])
    with pytest.raises(SalesError):
        sales_service.create_sales_return_invoice(invoice_id, "1404-06-05", 0, "", 1, [item])


def test_create_sales_return_invoice_rejects_unknown_original_invoice():
    with pytest.raises(SalesError):
        sales_service.create_sales_return_invoice(
            999, "1404-06-05", 0, "", 1, [_return_item(item_id=1, qty=1)]
        )


def test_create_sales_return_invoice_rejects_invalid_sales_invoice_item_ref():
    invoice_id, _, item_id = _create_base_sale(qty=5)
    with pytest.raises(SalesError):
        sales_service.create_sales_return_invoice(
            invoice_id, "1404-06-05", 0, "", 1, [_return_item(item_id=99999, qty=1)]
        )
    assert _FakeDatabase._shared_state["return_invoices"] == []


# =========================================================
# بخش ۲ — FIFO چندلایه و برگشت چندمرحله‌ای
# =========================================================

def test_create_sales_return_invoice_single_layer_restores_fifo():
    invoice_id, _, item_id = _create_base_sale(qty=5, layers=[(10, 100.0)])
    state = _FakeDatabase._shared_state
    assert state["layers"][0]["RemainingQuantity"] == 5  # ۵ از ۱۰ مصرف شد

    sales_service.create_sales_return_invoice(
        invoice_id, "1404-06-05", 0, "", 1, [_return_item(item_id, qty=2)]
    )
    assert state["layers"][0]["RemainingQuantity"] == 7  # ۲ عدد بازیابی شد


def test_create_sales_return_invoice_multi_stage_partial_returns_across_two_layers():
    """سناریوی دقیق Brief: Layer A مصرف=6، Layer B مصرف=4 (فروش ۱۰ عددی
    که از دو لایه FIFO تأمین شده). سه برگشت متوالی، دقیقاً طبق مقادیر
    تعیین‌شده در Handoff."""
    # لایه‌ها با ظرفیت دقیق که در فروش یک‌جا مصرف شوند: لایه اول=6، دوم=4
    invoice_id, _, item_id = _create_base_sale(qty=10, layers=[(6, 100.0), (4, 120.0)])
    state = _FakeDatabase._shared_state

    layer_a_id = state["layers"][0]["ID"]
    layer_b_id = state["layers"][1]["ID"]
    assert state["layers"][0]["RemainingQuantity"] == 0
    assert state["layers"][1]["RemainingQuantity"] == 0

    # Return #1 = 3 -> A restored = 3
    sales_service.create_sales_return_invoice(
        invoice_id, "1404-06-05", 0, "", 1, [_return_item(item_id, qty=3)]
    )
    assert next(l for l in state["layers"] if l["ID"] == layer_a_id)["RemainingQuantity"] == 3
    assert next(l for l in state["layers"] if l["ID"] == layer_b_id)["RemainingQuantity"] == 0

    # Return #2 = 5 -> A restored total = 6, B restored = 2
    sales_service.create_sales_return_invoice(
        invoice_id, "1404-06-06", 0, "", 1, [_return_item(item_id, qty=5)]
    )
    assert next(l for l in state["layers"] if l["ID"] == layer_a_id)["RemainingQuantity"] == 6
    assert next(l for l in state["layers"] if l["ID"] == layer_b_id)["RemainingQuantity"] == 2

    # Return #3 = 3 -> rejected (فقط ۲ باقی مانده)
    with pytest.raises(SalesError):
        sales_service.create_sales_return_invoice(
            invoice_id, "1404-06-07", 0, "", 1, [_return_item(item_id, qty=3)]
        )
    # هیچ‌چیزی نباید تغییر کرده باشد (Rollback کامل)
    assert next(l for l in state["layers"] if l["ID"] == layer_a_id)["RemainingQuantity"] == 6
    assert next(l for l in state["layers"] if l["ID"] == layer_b_id)["RemainingQuantity"] == 2

    # Return #3 (اصلاح‌شده) = 2 -> succeeds, B restored total = 4
    sales_service.create_sales_return_invoice(
        invoice_id, "1404-06-08", 0, "", 1, [_return_item(item_id, qty=2)]
    )
    assert next(l for l in state["layers"] if l["ID"] == layer_a_id)["RemainingQuantity"] == 6
    assert next(l for l in state["layers"] if l["ID"] == layer_b_id)["RemainingQuantity"] == 4


def test_create_sales_return_invoice_rejects_over_return_beyond_original_quantity():
    invoice_id, _, item_id = _create_base_sale(qty=5, layers=[(5, 100.0)])
    with pytest.raises(SalesError):
        sales_service.create_sales_return_invoice(
            invoice_id, "1404-06-05", 0, "", 1, [_return_item(item_id, qty=6)]
        )
    assert _FakeDatabase._shared_state["return_invoices"] == []


def test_create_sales_return_invoice_does_not_mutate_original_sales_invoice_item_layers():
    invoice_id, _, item_id = _create_base_sale(qty=5, layers=[(5, 100.0)])
    state = _FakeDatabase._shared_state
    original_snapshot = copy.deepcopy(state["item_layers"])

    sales_service.create_sales_return_invoice(
        invoice_id, "1404-06-05", 0, "", 1, [_return_item(item_id, qty=2)]
    )
    assert state["item_layers"] == original_snapshot  # SalesInvoiceItemLayers اصلی دست‌نخورده


def test_create_sales_return_invoice_records_return_item_layers():
    invoice_id, _, item_id = _create_base_sale(qty=5, layers=[(5, 100.0)])
    sales_service.create_sales_return_invoice(
        invoice_id, "1404-06-05", 0, "", 1, [_return_item(item_id, qty=2)]
    )
    state = _FakeDatabase._shared_state
    assert len(state["return_item_layers"]) == 1
    assert state["return_item_layers"][0]["Quantity"] == 2


# =========================================================
# بخش ۳ — سریال/IMEI
# =========================================================

def test_create_sales_return_invoice_restores_serial_to_instock():
    state = _FakeDatabase._shared_state
    state["serials"][501] = {"ID": 501, "ProductRef": 1, "Status": "InStock", "PurchaseLayerRef": 1}
    invoice_id, _, item_id = _create_base_sale(qty=1, layers=[(1, 100.0)], has_serial=True, serial_ids=[501])
    assert state["serials"][501]["Status"] == "Sold"

    sales_service.create_sales_return_invoice(
        invoice_id, "1404-06-05", 0, "", 1, [_return_item(item_id, qty=1, has_serial=True, serial_ids=[501])]
    )
    assert state["serials"][501]["Status"] == "InStock"
    # SoldInInvoiceItemRef باید حفظ شود (نه پاک شود)
    assert state["serials"][501]["SoldInInvoiceItemRef"] == item_id


def test_create_sales_return_invoice_creates_no_layer_records_for_serial_items():
    state = _FakeDatabase._shared_state
    state["serials"][501] = {"ID": 501, "ProductRef": 1, "Status": "InStock", "PurchaseLayerRef": 1}
    invoice_id, _, item_id = _create_base_sale(qty=1, layers=[(1, 100.0)], has_serial=True, serial_ids=[501])

    sales_service.create_sales_return_invoice(
        invoice_id, "1404-06-05", 0, "", 1, [_return_item(item_id, qty=1, has_serial=True, serial_ids=[501])]
    )
    assert state["return_item_layers"] == []


def test_create_sales_return_invoice_restores_purchase_layer_for_serial():
    state = _FakeDatabase._shared_state
    state["serials"][501] = {"ID": 501, "ProductRef": 1, "Status": "InStock", "PurchaseLayerRef": 1}
    invoice_id, _, item_id = _create_base_sale(qty=1, layers=[(1, 100.0)], has_serial=True, serial_ids=[501])
    layer_id = state["layers"][0]["ID"]
    assert state["layers"][0]["RemainingQuantity"] == 0

    sales_service.create_sales_return_invoice(
        invoice_id, "1404-06-05", 0, "", 1, [_return_item(item_id, qty=1, has_serial=True, serial_ids=[501])]
    )
    assert next(l for l in state["layers"] if l["ID"] == layer_id)["RemainingQuantity"] == 1


def test_create_sales_return_invoice_rejects_unknown_serial():
    invoice_id, _, item_id = _create_base_sale(qty=1, layers=[(1, 100.0)])
    with pytest.raises(SalesError):
        sales_service.create_sales_return_invoice(
            invoice_id, "1404-06-05", 0, "", 1,
            [_return_item(item_id, qty=1, has_serial=True, serial_ids=[9999])]
        )


def test_create_sales_return_invoice_rejects_serial_belonging_to_other_item():
    state = _FakeDatabase._shared_state
    state["serials"][501] = {"ID": 501, "ProductRef": 1, "Status": "InStock", "PurchaseLayerRef": 1}
    state["serials"][502] = {"ID": 502, "ProductRef": 1, "Status": "InStock", "PurchaseLayerRef": 1}
    # لایه با ظرفیت ۲ تا هر دو فروش (یک‌واحدی) از همان لایه تأمین شوند
    invoice_id, _, item_id_1 = _create_base_sale(qty=1, layers=[(2, 100.0)], has_serial=True, serial_ids=[501])

    # یک قلم فروش دوم مستقل با سریال دیگر
    item2 = _basic_item(qty=1, price=250.0, has_serial=True, serial_ids=[502])
    invoice_id_2, _ = sales_service.create_sales_invoice(1, "1404-06-02", 0, 0, "", 1, [item2])
    item_id_2 = state["items"][-1]["ID"]

    # تلاش برای برگشت سریال ۵۰۲ (متعلق به فاکتور دوم) با item_id فاکتور اول
    with pytest.raises(SalesError):
        sales_service.create_sales_return_invoice(
            invoice_id, "1404-06-05", 0, "", 1,
            [_return_item(item_id_1, qty=1, has_serial=True, serial_ids=[502])]
        )


def test_create_sales_return_invoice_rejects_already_returned_serial():
    state = _FakeDatabase._shared_state
    state["serials"][501] = {"ID": 501, "ProductRef": 1, "Status": "InStock", "PurchaseLayerRef": 1}
    invoice_id, _, item_id = _create_base_sale(qty=1, layers=[(1, 100.0)], has_serial=True, serial_ids=[501])

    sales_service.create_sales_return_invoice(
        invoice_id, "1404-06-05", 0, "", 1, [_return_item(item_id, qty=1, has_serial=True, serial_ids=[501])]
    )
    # تلاش دوم برای برگشت همان سریال (که الان InStock است، دیگر Sold نیست)
    with pytest.raises(SalesError):
        sales_service.create_sales_return_invoice(
            invoice_id, "1404-06-06", 0, "", 1, [_return_item(item_id, qty=1, has_serial=True, serial_ids=[501])]
        )


# =========================================================
# بخش ۴ — موجودی و کاردکس
# =========================================================

def test_create_sales_return_invoice_increments_product_stock():
    invoice_id, _, item_id = _create_base_sale(qty=5, layers=[(10, 100.0)])
    state = _FakeDatabase._shared_state
    stock_after_sale = state["products"][1]["CurrentStock"]

    sales_service.create_sales_return_invoice(
        invoice_id, "1404-06-05", 0, "", 1, [_return_item(item_id, qty=2)]
    )
    assert state["products"][1]["CurrentStock"] == stock_after_sale + 2


def test_create_sales_return_invoice_creates_sellreturn_cardex_entry():
    invoice_id, _, item_id = _create_base_sale(qty=5, layers=[(10, 100.0)])
    return_invoice_id, _ = sales_service.create_sales_return_invoice(
        invoice_id, "1404-06-05", 0, "", 1, [_return_item(item_id, qty=2)]
    )
    state = _FakeDatabase._shared_state
    entry = state["cardex"][-1]
    assert entry["MovementType"] == "SellReturn"
    assert entry["RefTable"] == "SalesReturnInvoices"
    assert entry["RefID"] == return_invoice_id
    assert entry["InQuantity"] == 2
    assert entry["OutQuantity"] == 0


# =========================================================
# بخش ۵ — حسابداری (Journal) دوطرفه
# =========================================================

def test_create_sales_return_invoice_posts_balanced_journal_entry():
    invoice_id, _, item_id = _create_base_sale(qty=5, price=100.0, layers=[(10, 100.0)])
    state = _FakeDatabase._shared_state
    journal_entries_before = len(state["journal_entries"])  # سند فاکتور فروش پایه

    return_invoice_id, _ = sales_service.create_sales_return_invoice(
        invoice_id, "1404-06-05", 0, "", 1, [_return_item(item_id, qty=2)]
    )
    assert len(state["journal_entries"]) == journal_entries_before + 1
    entry = next(e for e in state["journal_entries"] if e["SourceTable"] == "SalesReturnInvoices")
    assert entry["SourceID"] == return_invoice_id

    lines = [l for l in state["journal_lines"] if l["JournalEntryRef"] == entry["ID"]]
    total_debit = sum(l["Debit"] for l in lines)
    total_credit = sum(l["Credit"] for l in lines)
    assert total_debit == total_credit  # موازنه واقعی

    accounts_by_id = {a["ID"]: a["Code"] for a in state["accounts"]}
    debit_return = next(l["Debit"] for l in lines if accounts_by_id[l["AccountRef"]] == "4100")
    credit_ar = next(l["Credit"] for l in lines if accounts_by_id[l["AccountRef"]] == "1100")
    debit_inv = next(l["Debit"] for l in lines if accounts_by_id[l["AccountRef"]] == "1200")
    credit_cogs = next(l["Credit"] for l in lines if accounts_by_id[l["AccountRef"]] == "5000")

    # فروش پایه با قیمت واحد 150 (100+50) بود؛ ۲ عدد برگشتی => 300
    assert debit_return == 300.0
    assert credit_ar == 300.0
    # بهای بازیابی‌شده: ۲ عدد از لایه با UnitPrice=100 => 200
    assert debit_inv == 200.0
    assert credit_cogs == 200.0

    # حساب 4000 (درآمد فروش) هرگز نباید در این سند ظاهر شود
    assert all(accounts_by_id[l["AccountRef"]] != "4000" for l in lines)
    # بدون مالیات، هیچ ردیفی برای 2200 نباید ساخته شود
    assert all(accounts_by_id[l["AccountRef"]] != "2200" for l in lines)


def test_create_sales_return_invoice_journal_includes_tax_line_when_tax_present():
    invoice_id, _, item_id = _create_base_sale(qty=5, price=100.0, layers=[(10, 100.0)])
    return_invoice_id, _ = sales_service.create_sales_return_invoice(
        invoice_id, "1404-06-05", 27, "", 1, [_return_item(item_id, qty=2)]
    )
    state = _FakeDatabase._shared_state
    accounts_by_id = {a["ID"]: a["Code"] for a in state["accounts"]}
    entry = next(e for e in state["journal_entries"] if e["SourceTable"] == "SalesReturnInvoices")
    lines = [l for l in state["journal_lines"] if l["JournalEntryRef"] == entry["ID"]]

    debit_tax = next(l["Debit"] for l in lines if accounts_by_id[l["AccountRef"]] == "2200")
    credit_ar = next(l["Credit"] for l in lines if accounts_by_id[l["AccountRef"]] == "1100")
    assert debit_tax == 27.0
    assert credit_ar == 327.0  # 300 + 27
    assert sum(l["Debit"] for l in lines) == sum(l["Credit"] for l in lines)


def test_create_sales_return_invoice_journal_entry_number_increments_after_sale_entry():
    invoice_id, _, item_id = _create_base_sale(qty=5, layers=[(10, 100.0)])  # سند شماره ۱
    sales_service.create_sales_return_invoice(
        invoice_id, "1404-06-05", 0, "", 1, [_return_item(item_id, qty=2)]
    )
    state = _FakeDatabase._shared_state
    numbers = sorted(e["EntryNumber"] for e in state["journal_entries"])
    assert numbers == [1, 2]


def test_create_sales_return_invoice_uses_original_unit_price_not_caller_supplied():
    """قیمت واحد باید از خودِ SalesInvoiceItems اصلی خوانده شود، نه ورودی
    کاربر — even اگر caller مقدار متفاوتی در دیکشنری item بگذارد."""
    invoice_id, _, item_id = _create_base_sale(qty=5, price=200.0, layers=[(10, 100.0)])
    item = _return_item(item_id, qty=1, unit_price=1.0)  # تلاش برای جعل قیمت؛ باید نادیده گرفته شود
    sales_service.create_sales_return_invoice(invoice_id, "1404-06-05", 0, "", 1, [item])
    state = _FakeDatabase._shared_state
    # فروش پایه با قیمت 250 (200+50) بود
    assert state["return_items"][0]["UnitPrice"] == 250.0


# =========================================================
# بخش ۶ — Transaction / Rollback / Audit-after-commit
# =========================================================

def test_create_sales_return_invoice_rolls_back_everything_on_over_return_failure():
    invoice_id, _, item_id = _create_base_sale(qty=10, layers=[(6, 100.0), (4, 120.0)])
    state = _FakeDatabase._shared_state
    stock_before = state["products"][1]["CurrentStock"]
    journal_entries_before = len(state["journal_entries"])

    with pytest.raises(SalesError):
        sales_service.create_sales_return_invoice(
            invoice_id, "1404-06-05", 0, "", 1, [
                _return_item(item_id, qty=3),     # قلم معتبر به‌تنهایی
                _return_item(999999, qty=1),      # قلم نامعتبر (SalesInvoiceItemRef غلط)
            ]
        )

    assert state["return_invoices"] == []
    assert state["return_items"] == []
    assert state["return_item_layers"] == []
    assert len(state["journal_entries"]) == journal_entries_before
    assert state["products"][1]["CurrentStock"] == stock_before
    assert state["layers"][0]["RemainingQuantity"] == 0  # لایه‌ها دست‌نخورده
    assert state["layers"][1]["RemainingQuantity"] == 0


def test_create_sales_return_invoice_rolls_back_when_account_missing():
    invoice_id, _, item_id = _create_base_sale(qty=5, layers=[(10, 100.0)])
    state = _FakeDatabase._shared_state
    journal_entries_before = len(state["journal_entries"])
    state["accounts"] = [a for a in state["accounts"] if a["Code"] != "4100"]

    with pytest.raises(AccountingError):
        sales_service.create_sales_return_invoice(
            invoice_id, "1404-06-05", 0, "", 1, [_return_item(item_id, qty=2)]
        )

    assert state["return_invoices"] == []
    assert len(state["journal_entries"]) == journal_entries_before
    assert state["layers"][0]["RemainingQuantity"] == 5  # هیچ بازیابی‌ای انجام نشد


def test_create_sales_return_invoice_rolls_back_when_account_inactive():
    invoice_id, _, item_id = _create_base_sale(qty=5, layers=[(10, 100.0)])
    state = _FakeDatabase._shared_state
    journal_entries_before = len(state["journal_entries"])
    next(a for a in state["accounts"] if a["Code"] == "1100")["IsActive"] = False

    with pytest.raises(AccountingError):
        sales_service.create_sales_return_invoice(
            invoice_id, "1404-06-05", 0, "", 1, [_return_item(item_id, qty=2)]
        )

    assert state["return_invoices"] == []
    assert len(state["journal_entries"]) == journal_entries_before


def test_create_sales_return_invoice_pure_validation_failure_never_touches_ledger():
    invoice_id, _, item_id = _create_base_sale(qty=5, layers=[(10, 100.0)])
    state = _FakeDatabase._shared_state
    journal_entries_before = len(state["journal_entries"])
    with pytest.raises(SalesError):
        sales_service.create_sales_return_invoice(invoice_id, "1404-06-05", 0, "", 1, [])
    assert len(state["journal_entries"]) == journal_entries_before


def test_create_sales_return_invoice_succeeds_and_writes_audit_after_commit():
    invoice_id, _, item_id = _create_base_sale(qty=5, layers=[(10, 100.0)])
    return_invoice_id, invoice_number = sales_service.create_sales_return_invoice(
        invoice_id, "1404-06-05", 0, "", 1, [_return_item(item_id, qty=2)]
    )
    assert return_invoice_id is not None
    assert invoice_number is not None
    state = _FakeDatabase._shared_state
    assert len(state["return_invoices"]) == 1


def test_create_sales_return_invoice_commits_before_audit_runs(monkeypatch):
    """audit باید فقط بعد از commit موفق اجرا شود — این تست ترتیب واقعی
    فراخوانی conn.commit() و create_audit_entry را بررسی می‌کند."""
    invoice_id, _, item_id = _create_base_sale(qty=5, layers=[(10, 100.0)])

    call_order = []
    real_commit = _FakeConnection.commit

    def tracking_commit(self):
        call_order.append("commit")
        real_commit(self)

    monkeypatch.setattr(_FakeConnection, "commit", tracking_commit)

    import services.audit_service as audit_service
    real_create_audit_entry = audit_service.create_audit_entry

    def tracking_audit(*args, **kwargs):
        call_order.append("audit")
        return real_create_audit_entry(*args, **kwargs)

    monkeypatch.setattr(sales_service, "create_audit_entry", tracking_audit)

    sales_service.create_sales_return_invoice(
        invoice_id, "1404-06-05", 0, "", 1, [_return_item(item_id, qty=2)]
    )
    assert call_order == ["commit", "audit"]


def test_create_sales_return_invoice_invoice_number_starts_after_2999():
    invoice_id, _, item_id = _create_base_sale(qty=5, layers=[(10, 100.0)])
    _, invoice_number = sales_service.create_sales_return_invoice(
        invoice_id, "1404-06-05", 0, "", 1, [_return_item(item_id, qty=2)]
    )
    assert invoice_number == 3000


# =========================================================
# بخش ۷ — get_sales_return_invoices / get_sales_return_invoice_items:
#          فقط بررسی می‌شود که Query معتبر بسازند و خطا ندهند (خروجی
#          واقعی به fetch_all یک FakeDatabase بستگی دارد که [] برمی‌گرداند).
# =========================================================

def test_get_sales_return_invoices_does_not_raise():
    assert sales_service.get_sales_return_invoices("") == []


def test_get_sales_return_invoice_items_does_not_raise():
    assert sales_service.get_sales_return_invoice_items(1) == []


def test_get_sales_invoice_returnable_items_does_not_raise():
    assert sales_service.get_sales_invoice_returnable_items(1) == []


# =========================================================
# بخش ۸ — _build_sales_return_journal_lines: تست خالص (بدون دیتابیس)
# =========================================================

def test_build_sales_return_journal_lines_balanced_pure():
    lines = _build_sales_return_journal_lines(net_amount=300, tax_amount=0, total_cost_amount=200)
    assert sum(l.get("debit", 0) for l in lines) == sum(l.get("credit", 0) for l in lines)
    codes = {l["account_code"] for l in lines}
    assert codes == {"4100", "1100", "1200", "5000"}
    assert "4000" not in codes


def test_build_sales_return_journal_lines_skips_zero_tax_line():
    lines = _build_sales_return_journal_lines(net_amount=300, tax_amount=0, total_cost_amount=200)
    assert all(l["account_code"] != "2200" for l in lines)


def test_build_sales_return_journal_lines_includes_tax_line_when_present():
    lines = _build_sales_return_journal_lines(net_amount=300, tax_amount=27, total_cost_amount=200)
    tax_line = next(l for l in lines if l["account_code"] == "2200")
    ar_line = next(l for l in lines if l["account_code"] == "1100")
    assert tax_line["debit"] == 27
    assert ar_line["credit"] == 327  # 300 + 27


def test_build_sales_return_journal_lines_omits_cost_lines_when_cost_zero():
    lines = _build_sales_return_journal_lines(net_amount=300, tax_amount=0, total_cost_amount=0)
    codes = {l["account_code"] for l in lines}
    assert "1200" not in codes and "5000" not in codes


def test_build_sales_return_journal_lines_returns_empty_for_all_zero():
    lines = _build_sales_return_journal_lines(net_amount=0, tax_amount=0, total_cost_amount=0)
    assert lines == []


def test_build_sales_return_journal_lines_never_uses_sales_revenue_account():
    lines = _build_sales_return_journal_lines(net_amount=300, tax_amount=27, total_cost_amount=200)
    assert all(l["account_code"] != "4000" for l in lines)
