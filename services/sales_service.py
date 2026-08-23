# -*- coding: utf-8 -*-
"""
لایه منطق تجاری «فروش».
کسر خودکار از قدیمی‌ترین لایه FIFO، بروزرسانی موجودی، کاردکس و وضعیت سریال/IMEI
همه اینجا انجام می‌شود تا پنجره‌های UI فقط نمایش‌دهنده باشند.
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import Database
from services.audit_service import create_audit_entry


class SalesError(Exception):
    """خطای قابل‌فهم برای نمایش به کاربر (نه خطای فنی دیتابیس)"""
    pass


def get_customers():
    """لیست اشخاصی که به‌عنوان مشتری علامت خورده‌اند"""
    db = Database()
    rows = db.fetch_all(
        "SELECT ID, FullName FROM Persons WHERE IsCustomer = 1 AND IsDeleted = 0 ORDER BY FullName"
    )
    db.close()
    return rows


def get_available_serials(product_id: int):
    """سریال/IMEی‌های موجود در انبار برای یک کالای سریالی (برای انتخاب هنگام فروش)"""
    db = Database()
    rows = db.fetch_all(
        """SELECT ID, SerialNumber, IMEI
           FROM ProductSerials
           WHERE ProductRef = ? AND Status = N'InStock'
           ORDER BY ID""",
        (product_id,)
    )
    db.close()
    return rows


def get_sales_invoices(search: str = ""):
    db = Database()
    like = f"%{search.strip()}%"
    rows = db.fetch_all(
        """SELECT si.ID, si.InvoiceNumber, si.ShamsiDate, p.FullName AS CustomerName,
                  si.PayableAmount, si.Description
           FROM SalesInvoices si
           JOIN Persons p ON p.ID = si.PersonRef
           WHERE si.IsDeleted = 0 AND
                 (CAST(si.InvoiceNumber AS NVARCHAR(50)) LIKE ? OR p.FullName LIKE ?)
           ORDER BY si.ID DESC""",
        (like, like)
    )
    db.close()
    return rows


def get_sales_invoice_items(invoice_id: int):
    db = Database()
    rows = db.fetch_all(
        """SELECT sii.ID, pr.Name AS ProductName, sii.Quantity, sii.UnitPrice,
                  sii.DiscountAmount, sii.TotalPrice
           FROM SalesInvoiceItems sii
           JOIN Products pr ON pr.ID = sii.ProductRef
           WHERE sii.InvoiceRef = ?
           ORDER BY sii.ID""",
        (invoice_id,)
    )
    db.close()
    return rows


def _get_setting(cursor, key: str, default: str) -> str:
    cursor.execute("SELECT SettingValue FROM Settings WHERE SettingKey = ?", (key,))
    row = cursor.fetchone()
    return row[0] if row and row[0] is not None else default


def create_sales_invoice(customer_id: int, shamsi_date: str, discount_amount: float,
                          tax_amount: float, description: str, user_id: int, items: list):
    """
    ثبت یک فاکتور فروش کامل به‌صورت یکپارچه (Transaction):
    سربرگ فاکتور + اقلام + کسر از لایه‌های FIFO + فروخته‌شدن سریال/IMEI +
    بروزرسانی موجودی + کاردکس.
    اگر هر بخشی با خطا مواجه شود، هیچ‌کدام ذخیره نمی‌شود (rollback کامل).

    items: لیستی از دیکشنری با کلیدهای:
        product_id, quantity, unit_price, discount (اختیاری),
        has_serial, serial_ids (لیست ID از ProductSerials - فقط برای کالای سریالی)
    """
    if not items:
        raise SalesError("حداقل یک قلم کالا باید به فاکتور اضافه شود.")

    for item in items:
        qty = float(item.get("quantity") or 0)
        if qty <= 0:
            raise SalesError("تعداد هر قلم کالا باید بزرگ‌تر از صفر باشد.")
        if float(item.get("unit_price") or 0) < 0:
            raise SalesError("قیمت فروش نمی‌تواند منفی باشد.")
        serial_ids = item.get("serial_ids") or []
        if item.get("has_serial") and len(serial_ids) != int(qty):
            raise SalesError(
                f"برای «{item.get('product_name', 'کالا')}» باید دقیقاً {int(qty)} سریال/IMEI انتخاب شود."
            )

    db = Database()
    conn = db.connect()
    cursor = conn.cursor()
    try:
        allow_negative = _get_setting(cursor, "AllowNegativeStock", "0") == "1"

        total_amount = sum(
            float(i["quantity"]) * float(i["unit_price"]) - float(i.get("discount", 0) or 0)
            for i in items
        )
        payable = total_amount - float(discount_amount or 0) + float(tax_amount or 0)

        cursor.execute("SELECT ISNULL(MAX(InvoiceNumber), 2000) + 1 AS NextNum FROM SalesInvoices")
        invoice_number = int(cursor.fetchone()[0])

        cursor.execute(
            """INSERT INTO SalesInvoices
               (InvoiceNumber, PersonRef, ShamsiDate, TotalAmount, DiscountAmount,
                TaxAmount, PayableAmount, Description, UserRef)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (invoice_number, customer_id, shamsi_date, total_amount, discount_amount or 0,
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

            # --- کسر از قدیمی‌ترین لایه‌های FIFO ---
            cursor.execute(
                """SELECT ID, RemainingQuantity, UnitPrice FROM ProductPurchaseLayers
                   WHERE ProductRef = ? AND RemainingQuantity > 0
                   ORDER BY ID""",
                (product_id,)
            )
            layers = cursor.fetchall()

            remaining_needed = qty
            cost_amount = 0.0
            consumed = []  # (layer_id, qty_from_layer, layer_unit_price)
            for layer in layers:
                if remaining_needed <= 0:
                    break
                layer_id, layer_remaining, layer_price = layer[0], float(layer[1]), float(layer[2])
                take = min(layer_remaining, remaining_needed)
                consumed.append((layer_id, take, layer_price))
                cost_amount += take * layer_price
                remaining_needed -= take

            if remaining_needed > 0 and not allow_negative:
                raise SalesError(
                    f"موجودی «{item.get('product_name', 'این کالا')}» کافی نیست "
                    f"(کمبود: {remaining_needed:g} عدد نسبت به لایه‌های خرید ثبت‌شده)."
                )
            elif remaining_needed > 0:
                # اجازه موجودی منفی فعال است؛ کمبود را با آخرین قیمت خرید کالا به‌عنوان بها ثبت می‌کنیم
                cursor.execute("SELECT PurchasePrice FROM Products WHERE ID = ?", (product_id,))
                last_price = float(cursor.fetchone()[0] or 0)
                cost_amount += remaining_needed * last_price

            cursor.execute(
                """INSERT INTO SalesInvoiceItems
                   (InvoiceRef, ProductRef, Quantity, UnitPrice, DiscountAmount,
                    TotalPrice, CostAmount, Description)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (invoice_id, product_id, qty, price, disc, total_price,
                 cost_amount, item.get("description", ""))
            )
            cursor.execute("SELECT @@IDENTITY AS id")
            item_id = int(cursor.fetchone()[0])

            for layer_id, take, layer_price in consumed:
                cursor.execute(
                    "UPDATE ProductPurchaseLayers SET RemainingQuantity = RemainingQuantity - ? WHERE ID = ?",
                    (take, layer_id)
                )
                cursor.execute(
                    """INSERT INTO SalesInvoiceItemLayers
                       (SalesInvoiceItemRef, PurchaseLayerRef, Quantity, UnitPrice)
                       VALUES (?,?,?,?)""",
                    (item_id, layer_id, take, layer_price)
                )

            # --- سریال/IMEی‌های انتخاب‌شده را «فروخته‌شده» می‌کنیم ---
            serial_ids = item.get("serial_ids") or []
            for serial_id in serial_ids:
                cursor.execute(
                    "SELECT Status FROM ProductSerials WHERE ID = ? AND ProductRef = ?",
                    (serial_id, product_id)
                )
                row = cursor.fetchone()
                if not row or row[0] != "InStock":
                    raise SalesError("یکی از سریال/IMEی‌های انتخاب‌شده دیگر در انبار موجود نیست.")
                cursor.execute(
                    """UPDATE ProductSerials
                       SET Status = N'Sold', SoldInInvoiceItemRef = ?
                       WHERE ID = ?""",
                    (item_id, serial_id)
                )

            # --- بروزرسانی موجودی و کاردکس ---
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
                   VALUES (?,?,N'Sell',N'SalesInvoices',?,0,?,?,?,?,?)""",
                (product_id, shamsi_date, invoice_id, qty, price, balance,
                 f"فاکتور فروش شماره {invoice_number}", user_id)
            )

        conn.commit()
        create_audit_entry(user_id, "Create", "SalesInvoices", invoice_id, f"Sales invoice {invoice_number}")
        return invoice_id, invoice_number

    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        db.close()
