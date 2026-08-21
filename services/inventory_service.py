# -*- coding: utf-8 -*-
"""
لایه منطق تجاری «خرید و انبار».
همه محاسبات FIFO، کاردکس، موجودی و سریال/IMEI اینجا انجام می‌شود
تا پنجره‌های UI فقط نمایش‌دهنده باشند و منطق اصلی یک‌جا و قابل‌اعتماد بماند.
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import Database


class InventoryError(Exception):
    """خطای قابل‌فهم برای نمایش به کاربر (نه خطای فنی دیتابیس)"""
    pass


def get_suppliers():
    """لیست اشخاصی که به‌عنوان فروشنده/تأمین‌کننده علامت خورده‌اند"""
    db = Database()
    rows = db.fetch_all(
        "SELECT ID, FullName FROM Persons WHERE IsSeller = 1 AND IsDeleted = 0 ORDER BY FullName"
    )
    db.close()
    return rows


def search_products(text: str = ""):
    """جستجوی کالا برای انتخاب در فاکتور خرید"""
    db = Database()
    like = f"%{text.strip()}%"
    rows = db.fetch_all(
        """SELECT ID, Name, Code, Brand, Model, HasSerial, CurrentStock, PurchasePrice, OrderPoint
           FROM Products
           WHERE IsDeleted = 0 AND (Name LIKE ? OR Code LIKE ? OR Brand LIKE ?)
           ORDER BY Name""",
        (like, like, like)
    )
    db.close()
    return rows


def get_low_stock_products():
    """کالاهایی که موجودی‌شان به نقطه سفارش رسیده یا کمتر شده"""
    db = Database()
    rows = db.fetch_all(
        """SELECT ID, Name, Code, CurrentStock, OrderPoint
           FROM Products
           WHERE IsDeleted = 0 AND OrderPoint > 0 AND CurrentStock <= OrderPoint
           ORDER BY Name"""
    )
    db.close()
    return rows


def get_purchase_invoices(search: str = ""):
    db = Database()
    like = f"%{search.strip()}%"
    rows = db.fetch_all(
        """SELECT pi.ID, pi.InvoiceNumber, pi.ShamsiDate, p.FullName AS SupplierName,
                  pi.PayableAmount, pi.Description
           FROM PurchaseInvoices pi
           JOIN Persons p ON p.ID = pi.PersonRef
           WHERE pi.IsDeleted = 0 AND
                 (CAST(pi.InvoiceNumber AS NVARCHAR(50)) LIKE ? OR p.FullName LIKE ?)
           ORDER BY pi.ID DESC""",
        (like, like)
    )
    db.close()
    return rows


def get_invoice_items(invoice_id: int):
    db = Database()
    rows = db.fetch_all(
        """SELECT pii.ID, pr.Name AS ProductName, pii.Quantity, pii.UnitPrice,
                  pii.DiscountAmount, pii.TotalPrice
           FROM PurchaseInvoiceItems pii
           JOIN Products pr ON pr.ID = pii.ProductRef
           WHERE pii.InvoiceRef = ?
           ORDER BY pii.ID""",
        (invoice_id,)
    )
    db.close()
    return rows


def get_product_cardex(product_id: int):
    """گزارش کاردکس یک کالا (تاریخچه کامل ورود/خروج)"""
    db = Database()
    rows = db.fetch_all(
        """SELECT ShamsiDate, MovementType, InQuantity, OutQuantity,
                  UnitPrice, BalanceQuantity, Description
           FROM ProductCardex
           WHERE ProductRef = ?
           ORDER BY ID""",
        (product_id,)
    )
    db.close()
    return rows


def serial_exists_in_stock(serial: str) -> bool:
    db = Database()
    row = db.fetch_one(
        "SELECT COUNT(*) AS c FROM ProductSerials WHERE SerialNumber = ? AND Status = N'InStock'",
        (serial,)
    )
    db.close()
    return bool(row and row["c"] > 0)


def create_purchase_invoice(supplier_id: int, shamsi_date: str, discount_amount: float,
                             tax_amount: float, description: str, user_id: int, items: list):
    """
    ثبت یک فاکتور خرید کامل به‌صورت یکپارچه (Transaction):
    سربرگ فاکتور + اقلام + لایه FIFO + سریال/IMEI + بروزرسانی موجودی + کاردکس.
    اگر هر بخشی با خطا مواجه شود، هیچ‌کدام ذخیره نمی‌شود (rollback کامل).

    items: لیستی از دیکشنری با کلیدهای:
        product_id, quantity, unit_price, discount (اختیاری), serials (لیست رشته یا None)
    """
    if not items:
        raise InventoryError("حداقل یک قلم کالا باید به فاکتور اضافه شود.")

    for item in items:
        qty = float(item.get("quantity") or 0)
        if qty <= 0:
            raise InventoryError("تعداد هر قلم کالا باید بزرگ‌تر از صفر باشد.")
        if float(item.get("unit_price") or 0) < 0:
            raise InventoryError("قیمت خرید نمی‌تواند منفی باشد.")
        serials = item.get("serials") or []
        if item.get("has_serial") and len(serials) != int(qty):
            raise InventoryError(
                f"برای «{item.get('product_name', 'کالا')}» باید دقیقاً {int(qty)} سریال/IMEI وارد شود."
            )

    db = Database()
    conn = db.connect()
    cursor = conn.cursor()
    try:
        total_amount = sum(
            float(i["quantity"]) * float(i["unit_price"]) - float(i.get("discount", 0) or 0)
            for i in items
        )
        payable = total_amount - float(discount_amount or 0) + float(tax_amount or 0)

        cursor.execute("SELECT ISNULL(MAX(InvoiceNumber), 1000) + 1 AS NextNum FROM PurchaseInvoices")
        invoice_number = int(cursor.fetchone()[0])

        cursor.execute(
            """INSERT INTO PurchaseInvoices
               (InvoiceNumber, PersonRef, ShamsiDate, TotalAmount, DiscountAmount,
                TaxAmount, PayableAmount, Description, UserRef)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (invoice_number, supplier_id, shamsi_date, total_amount, discount_amount or 0,
             tax_amount or 0, payable, description or "", user_id)
        )
        cursor.execute("SELECT @@IDENTITY AS id")
        invoice_id = int(cursor.fetchone()[0])

        for item in items:
            product_id = int(item["product_id"])
            qty = float(item["quantity"])
            price = float(item["unit_price"])
            disc = float(item.get("discount", 0) or 0)
            total_price = qty * price - disc

            cursor.execute(
                """INSERT INTO PurchaseInvoiceItems
                   (InvoiceRef, ProductRef, Quantity, UnitPrice, DiscountAmount, TotalPrice, Description)
                   VALUES (?,?,?,?,?,?,?)""",
                (invoice_id, product_id, qty, price, disc, total_price, item.get("description", ""))
            )
            cursor.execute("SELECT @@IDENTITY AS id")
            item_id = int(cursor.fetchone()[0])

            cursor.execute(
                """INSERT INTO ProductPurchaseLayers
                   (ProductRef, InvoiceItemRef, ShamsiDate, OriginalQuantity, RemainingQuantity, UnitPrice)
                   VALUES (?,?,?,?,?,?)""",
                (product_id, item_id, shamsi_date, qty, qty, price)
            )
            cursor.execute("SELECT @@IDENTITY AS id")
            layer_id = int(cursor.fetchone()[0])

            serials = item.get("serials") or []
            for s in serials:
                s = (s or "").strip()
                if not s:
                    raise InventoryError("سریال/IMEI نمی‌تواند خالی باشد.")
                cursor.execute(
                    "SELECT COUNT(*) FROM ProductSerials WHERE SerialNumber=? AND Status=N'InStock'",
                    (s,)
                )
                if cursor.fetchone()[0] > 0:
                    raise InventoryError(f"سریال/IMEI تکراری است (قبلاً در انبار موجود است): {s}")
                cursor.execute(
                    """INSERT INTO ProductSerials (ProductRef, SerialNumber, IMEI, Status, PurchaseLayerRef)
                       VALUES (?,?,?,N'InStock',?)""",
                    (product_id, s, s, layer_id)
                )

            cursor.execute(
                "UPDATE Products SET CurrentStock = CurrentStock + ?, PurchasePrice = ?, UpdatedAt = GETDATE() WHERE ID = ?",
                (qty, price, product_id)
            )
            cursor.execute("SELECT CurrentStock FROM Products WHERE ID = ?", (product_id,))
            balance = cursor.fetchone()[0]

            cursor.execute(
                """INSERT INTO ProductCardex
                   (ProductRef, ShamsiDate, MovementType, RefTable, RefID,
                    InQuantity, OutQuantity, UnitPrice, BalanceQuantity, Description, UserRef)
                   VALUES (?,?,N'Buy',N'PurchaseInvoices',?,?,0,?,?,?,?)""",
                (product_id, shamsi_date, invoice_id, qty, price, balance,
                 f"فاکتور خرید شماره {invoice_number}", user_id)
            )

        conn.commit()
        return invoice_id, invoice_number

    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        db.close()


# =========================================================
# مرحله ۱۰: فاکتور برگشت از خرید
# =========================================================

def get_returnable_items(purchase_invoice_id: int):
    """
    اقلام یک فاکتور خرید مشخص، همراه با حداکثر تعداد قابل‌برگشت.
    حداکثر قابل‌برگشت = موجودی باقیمانده همان لایه FIFO (RemainingQuantity)،
    یعنی اگر بخشی از آن قبلاً فروخته شده باشد، دیگر قابل برگشت به تأمین‌کننده نیست.
    """
    db = Database()
    rows = db.fetch_all(
        """SELECT pii.ID AS ItemID, pr.ID AS ProductID, pr.Name AS ProductName, pr.HasSerial,
                  pii.Quantity AS OriginalQuantity, pii.UnitPrice,
                  ppl.ID AS LayerID, ppl.RemainingQuantity
           FROM PurchaseInvoiceItems pii
           JOIN Products pr ON pr.ID = pii.ProductRef
           JOIN ProductPurchaseLayers ppl ON ppl.InvoiceItemRef = pii.ID
           WHERE pii.InvoiceRef = ?
           ORDER BY pii.ID""",
        (purchase_invoice_id,)
    )
    db.close()
    return rows


def get_layer_available_serials(layer_id: int):
    """سریال/IMEی‌های موجود در انبار (هنوز فروخته‌نشده) که از یک لایه خرید مشخص آمده‌اند"""
    db = Database()
    rows = db.fetch_all(
        """SELECT ID, SerialNumber, IMEI
           FROM ProductSerials
           WHERE PurchaseLayerRef = ? AND Status = N'InStock'
           ORDER BY ID""",
        (layer_id,)
    )
    db.close()
    return rows


def get_purchase_return_invoices(search: str = ""):
    db = Database()
    like = f"%{search.strip()}%"
    rows = db.fetch_all(
        """SELECT pri.ID, pri.InvoiceNumber, pri.ShamsiDate, p.FullName AS SupplierName,
                  pri.PayableAmount, pri.Description, pi.InvoiceNumber AS OriginalInvoiceNumber
           FROM PurchaseReturnInvoices pri
           JOIN Persons p ON p.ID = pri.PersonRef
           LEFT JOIN PurchaseInvoices pi ON pi.ID = pri.OriginalPurchaseInvoiceRef
           WHERE pri.IsDeleted = 0 AND
                 (CAST(pri.InvoiceNumber AS NVARCHAR(50)) LIKE ? OR p.FullName LIKE ?)
           ORDER BY pri.ID DESC""",
        (like, like)
    )
    db.close()
    return rows


def get_purchase_return_invoice_items(invoice_id: int):
    db = Database()
    rows = db.fetch_all(
        """SELECT prii.ID, pr.Name AS ProductName, prii.Quantity, prii.UnitPrice,
                  prii.DiscountAmount, prii.TotalPrice
           FROM PurchaseReturnInvoiceItems prii
           JOIN Products pr ON pr.ID = prii.ProductRef
           WHERE prii.InvoiceRef = ?
           ORDER BY prii.ID""",
        (invoice_id,)
    )
    db.close()
    return rows


def create_purchase_return_invoice(original_invoice_id: int, shamsi_date: str,
                                    description: str, user_id: int, items: list):
    """
    ثبت یک فاکتور برگشت از خرید کامل به‌صورت یکپارچه (Transaction):
    سربرگ + اقلام + کاهش از لایه FIFO مربوطه + برگرداندن وضعیت سریال/IMEI +
    کاهش موجودی + کاردکس (MovementType='BuyReturn').
    اگر هر بخشی با خطا مواجه شود، هیچ‌کدام ذخیره نمی‌شود (rollback کامل).

    items: لیستی از دیکشنری با کلیدهای:
        item_id (PurchaseInvoiceItems.ID), product_id, product_name, layer_id,
        quantity, unit_price, has_serial, serial_ids (لیست ID از ProductSerials - فقط کالای سریالی)
    """
    items = [i for i in items if float(i.get("quantity") or 0) > 0]
    if not items:
        raise InventoryError("حداقل تعداد برگشتی یک قلم کالا را وارد کنید.")

    for item in items:
        qty = float(item["quantity"])
        if float(item.get("unit_price") or 0) < 0:
            raise InventoryError("قیمت نمی‌تواند منفی باشد.")
        serial_ids = item.get("serial_ids") or []
        if item.get("has_serial") and len(serial_ids) != int(qty):
            raise InventoryError(
                f"برای «{item.get('product_name', 'کالا')}» باید دقیقاً {int(qty)} سریال/IMEI انتخاب شود."
            )

    db = Database()
    conn = db.connect()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT PersonRef, InvoiceNumber FROM PurchaseInvoices WHERE ID = ? AND IsDeleted = 0",
            (original_invoice_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise InventoryError("فاکتور خرید اصلی پیدا نشد.")
        supplier_id, original_invoice_number = int(row[0]), int(row[1])

        total_amount = sum(float(i["quantity"]) * float(i["unit_price"]) for i in items)

        cursor.execute("SELECT ISNULL(MAX(InvoiceNumber), 4000) + 1 AS NextNum FROM PurchaseReturnInvoices")
        invoice_number = int(cursor.fetchone()[0])

        cursor.execute(
            """INSERT INTO PurchaseReturnInvoices
               (InvoiceNumber, PersonRef, OriginalPurchaseInvoiceRef, ShamsiDate,
                TotalAmount, PayableAmount, Description, UserRef)
               VALUES (?,?,?,?,?,?,?,?)""",
            (invoice_number, supplier_id, original_invoice_id, shamsi_date,
             total_amount, total_amount, description or "", user_id)
        )
        cursor.execute("SELECT @@IDENTITY AS id")
        return_invoice_id = int(cursor.fetchone()[0])

        for item in items:
            product_id = int(item["product_id"])
            qty = float(item["quantity"])
            price = float(item["unit_price"])
            total_price = qty * price
            layer_id = int(item["layer_id"])

            # موجودی باقیمانده همان لایه خرید را دوباره (داخل تراکنش) بررسی می‌کنیم
            cursor.execute("SELECT RemainingQuantity FROM ProductPurchaseLayers WHERE ID = ?", (layer_id,))
            layer_row = cursor.fetchone()
            if not layer_row or float(layer_row[0]) < qty:
                raise InventoryError(
                    f"«{item.get('product_name', 'این کالا')}» بیشتر از موجودی باقیمانده از همین "
                    f"فاکتور خرید قابل برگشت نیست (احتمالاً بخشی از آن قبلاً فروخته شده)."
                )

            cursor.execute(
                """INSERT INTO PurchaseReturnInvoiceItems
                   (InvoiceRef, ProductRef, Quantity, UnitPrice, DiscountAmount, TotalPrice, Description)
                   VALUES (?,?,?,?,0,?,?)""",
                (return_invoice_id, product_id, qty, price, total_price, item.get("description", ""))
            )

            cursor.execute(
                "UPDATE ProductPurchaseLayers SET RemainingQuantity = RemainingQuantity - ? WHERE ID = ?",
                (qty, layer_id)
            )

            serial_ids = item.get("serial_ids") or []
            for serial_id in serial_ids:
                cursor.execute(
                    "SELECT Status, PurchaseLayerRef FROM ProductSerials WHERE ID = ?", (serial_id,)
                )
                srow = cursor.fetchone()
                if not srow or srow[0] != "InStock" or int(srow[1]) != layer_id:
                    raise InventoryError("یکی از سریال/IMEی‌های انتخاب‌شده دیگر معتبر نیست.")
                cursor.execute(
                    "UPDATE ProductSerials SET Status = N'Returned' WHERE ID = ?", (serial_id,)
                )

            cursor.execute(
                "UPDATE Products SET CurrentStock = CurrentStock - ?, UpdatedAt = GETDATE() WHERE ID = ?",
                (qty, product_id)
            )
            cursor.execute("SELECT CurrentStock FROM Products WHERE ID = ?", (product_id,))
            balance = cursor.fetchone()[0]

            cursor.execute(
                """INSERT INTO ProductCardex
                   (ProductRef, ShamsiDate, MovementType, RefTable, RefID,
                    InQuantity, OutQuantity, UnitPrice, BalanceQuantity, Description, UserRef)
                   VALUES (?,?,N'BuyReturn',N'PurchaseReturnInvoices',?,0,?,?,?,?,?)""",
                (product_id, shamsi_date, return_invoice_id, qty, price, balance,
                 f"فاکتور برگشت خرید شماره {invoice_number} (فاکتور خرید اصلی: {original_invoice_number})",
                 user_id)
            )

        conn.commit()
        return return_invoice_id, invoice_number

    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        db.close()
