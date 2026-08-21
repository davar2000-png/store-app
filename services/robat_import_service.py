# -*- coding: utf-8 -*-
"""
لایه انتقال اطلاعات از نرم‌افزار قبلی (ربات).
چون نام دقیق ستون‌ها در جدول‌های ربات ممکن است بین نصب‌های مختلف کمی فرق کند،
این ماژول بجای فرض کردن نام ستون‌ها، امکان «نگاشت ستون» (Column Mapping) را
به کاربر می‌دهد: کاربر مشخص می‌کند کدام ستون ربات به کدام فیلد نرم‌افزار جدید
تبدیل شود.

فرض: دیتابیس ربات (مثلا RoboAccDB) روی همان SQL Server نرم‌افزار جدید Restore شده.
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import Database
from utils.persian_date import today_shamsi_str
from utils.fifo import add_purchase_layer, add_cardex_entry


class ImportError_(Exception):
    pass


# =========================================================
# کشف ساختار دیتابیس ربات (برای ساخت لیست‌های کشویی در رابط کاربری)
# =========================================================
def get_robat_databases():
    """لیست همه دیتابیس‌های موجود روی این سرور (برای انتخاب دیتابیس ربات)"""
    db = Database()
    rows = db.fetch_all(
        "SELECT name FROM sys.databases WHERE database_id > 4 ORDER BY name"
    )
    db.close()
    return [r["name"] for r in rows]


def get_tables(database_name: str):
    """لیست جدول‌های یک دیتابیس مشخص"""
    _validate_identifier(database_name)
    db = Database()
    rows = db.fetch_all(
        f"SELECT TABLE_NAME FROM [{database_name}].INFORMATION_SCHEMA.TABLES "
        f"WHERE TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_NAME"
    )
    db.close()
    return [r["TABLE_NAME"] for r in rows]


def get_columns(database_name: str, table_name: str):
    """لیست ستون‌های یک جدول مشخص"""
    _validate_identifier(database_name)
    _validate_identifier(table_name)
    db = Database()
    rows = db.fetch_all(
        f"SELECT COLUMN_NAME FROM [{database_name}].INFORMATION_SCHEMA.COLUMNS "
        f"WHERE TABLE_NAME = ? ORDER BY ORDINAL_POSITION",
        (table_name,)
    )
    db.close()
    return [r["COLUMN_NAME"] for r in rows]


def preview_table(database_name: str, table_name: str, limit: int = 15):
    """نمایش چند ردیف اول یک جدول برای کمک به تشخیص کاربر"""
    _validate_identifier(database_name)
    _validate_identifier(table_name)
    db = Database()
    rows = db.fetch_all(f"SELECT TOP {int(limit)} * FROM [{database_name}].dbo.[{table_name}]")
    db.close()
    return rows


def _validate_identifier(name: str):
    """جلوگیری از SQL Injection - فقط حروف، عدد و آندرلاین مجاز است"""
    if not name or not all(c.isalnum() or c == "_" for c in name):
        raise ImportError_(f"نام نامعتبر: {name}")


def _fetch_mapped(database_name: str, table_name: str, mapping: dict, limit: int = None):
    """
    اجرای SELECT با نگاشت ستون‌ها.
    mapping: {'FieldName_in_new_software': 'source_column_in_robat' or None}
    """
    _validate_identifier(database_name)
    _validate_identifier(table_name)

    select_parts = []
    for target_field, source_col in mapping.items():
        if source_col:
            _validate_identifier(source_col)
            select_parts.append(f"[{source_col}] AS [{target_field}]")
        else:
            select_parts.append(f"NULL AS [{target_field}]")

    top_clause = f"TOP {int(limit)} " if limit else ""
    query = f"SELECT {top_clause}{', '.join(select_parts)} FROM [{database_name}].dbo.[{table_name}]"

    db = Database()
    rows = db.fetch_all(query)
    db.close()
    return rows


# =========================================================
# Import اشخاص (مشتریان/فروشندگان)
# =========================================================
def import_persons(database_name: str, table_name: str, mapping: dict,
                    default_is_customer: bool = True, default_is_seller: bool = False):
    """
    mapping باید شامل کلیدهای زیر باشد (مقدار هرکدام = نام ستون در ربات یا None):
    FullName (اجباری), Mobile, Phone, NationalCode, Address
    خروجی: {'imported': N, 'skipped': N, 'errors': [...]}
    """
    if not mapping.get("FullName"):
        raise ImportError_("حداقل ستون «نام» باید نگاشت شود.")

    rows = _fetch_mapped(database_name, table_name, mapping)

    imported, skipped, errors = 0, 0, []
    db = Database()

    for r in rows:
        full_name = (r.get("FullName") or "").strip()
        if not full_name:
            skipped += 1
            continue

        national_code = (r.get("NationalCode") or "").strip() if r.get("NationalCode") else None
        mobile = (r.get("Mobile") or "").strip() if r.get("Mobile") else None

        # بررسی تکراری نبودن (بر اساس کد ملی در صورت وجود، وگرنه نام+موبایل)
        existing = None
        if national_code:
            existing = db.fetch_one(
                "SELECT ID FROM Persons WHERE NationalCode = ? AND IsDeleted = 0", (national_code,)
            )
        if not existing:
            existing = db.fetch_one(
                "SELECT ID FROM Persons WHERE FullName = ? AND ISNULL(Mobile,'') = ? AND IsDeleted = 0",
                (full_name, mobile or "")
            )

        if existing:
            skipped += 1
            continue

        try:
            db.execute(
                """INSERT INTO Persons
                   (FullName, Mobile, Phone, NationalCode, Address,
                    IsCustomer, IsSeller, CreatedShamsiDate)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (full_name, mobile, r.get("Phone"), national_code, r.get("Address"),
                 int(default_is_customer), int(default_is_seller), today_shamsi_str())
            )
            imported += 1
        except Exception as e:
            errors.append(f"{full_name}: {e}")

    db.close()
    return {"imported": imported, "skipped": skipped, "errors": errors}


# =========================================================
# Import کالاها
# =========================================================
def import_products(database_name: str, table_name: str, mapping: dict):
    """
    mapping باید شامل کلیدهای زیر باشد:
    Name (اجباری), Code, Brand, Model, PurchasePrice, SalePrice
    """
    if not mapping.get("Name"):
        raise ImportError_("حداقل ستون «نام کالا» باید نگاشت شود.")

    rows = _fetch_mapped(database_name, table_name, mapping)

    imported, skipped, errors = 0, 0, []
    db = Database()

    for r in rows:
        name = (r.get("Name") or "").strip()
        if not name:
            skipped += 1
            continue

        code = (r.get("Code") or "").strip() if r.get("Code") else None

        existing = None
        if code:
            existing = db.fetch_one("SELECT ID FROM Products WHERE Code = ? AND IsDeleted = 0", (code,))
        if not existing:
            existing = db.fetch_one("SELECT ID FROM Products WHERE Name = ? AND IsDeleted = 0", (name,))

        if existing:
            skipped += 1
            continue

        try:
            purchase_price = _to_float(r.get("PurchasePrice"))
            sale_price = _to_float(r.get("SalePrice"))
            db.execute(
                """INSERT INTO Products (Name, Code, Brand, Model, PurchasePrice, SalePrice)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (name, code, r.get("Brand"), r.get("Model"), purchase_price, sale_price)
            )
            imported += 1
        except Exception as e:
            errors.append(f"{name}: {e}")

    db.close()
    return {"imported": imported, "skipped": skipped, "errors": errors}


def _to_float(val):
    try:
        return float(val) if val is not None and str(val).strip() != "" else 0.0
    except (ValueError, TypeError):
        return 0.0


# =========================================================
# Import موجودی اولیه (تبدیل به یک لایه FIFO برای هر کالا)
# =========================================================
def import_opening_stock(database_name: str, table_name: str, mapping: dict):
    """
    mapping باید شامل کلیدهای زیر باشد:
    ProductCode یا ProductName (برای تطبیق با کالای موجود), Quantity (اجباری), UnitCost
    برای هر ردیف با تعداد > 0، یک لایه خرید (موجودی ابتدای دوره) در نرم‌افزار جدید ساخته می‌شود.
    """
    if not mapping.get("Quantity"):
        raise ImportError_("ستون «تعداد موجودی» باید نگاشت شود.")
    if not mapping.get("ProductCode") and not mapping.get("ProductName"):
        raise ImportError_("حداقل یکی از «کد کالا» یا «نام کالا» باید برای تطبیق نگاشت شود.")

    rows = _fetch_mapped(database_name, table_name, mapping)

    db = Database()

    # ساخت یا پیدا کردن شخص سیستمی برای فاکتور موجودی ابتدای دوره
    system_person = db.fetch_one(
        "SELECT ID FROM Persons WHERE FullName = N'موجودی ابتدای دوره (Import)' AND IsDeleted = 0"
    )
    if system_person:
        system_person_id = system_person["ID"]
    else:
        system_person_id = db.execute(
            """INSERT INTO Persons (FullName, IsSeller, CreatedShamsiDate)
               VALUES (N'موجودی ابتدای دوره (Import)', 1, ?)""",
            (today_shamsi_str(),)
        )

    invoice_id = db.execute(
        """INSERT INTO PurchaseInvoices (InvoiceNumber, PersonRef, ShamsiDate, Description)
           VALUES (?, ?, ?, N'موجودی اولیه وارد شده از نرم‌افزار ربات')""",
        (f"IMPORT-{today_shamsi_str().replace('/', '')}", system_person_id, today_shamsi_str())
    )

    imported, skipped, errors = 0, 0, []

    for r in rows:
        qty = _to_float(r.get("Quantity"))
        if qty <= 0:
            skipped += 1
            continue

        code = (r.get("ProductCode") or "").strip() if r.get("ProductCode") else None
        name = (r.get("ProductName") or "").strip() if r.get("ProductName") else None

        product = None
        if code:
            product = db.fetch_one("SELECT * FROM Products WHERE Code = ? AND IsDeleted = 0", (code,))
        if not product and name:
            product = db.fetch_one("SELECT * FROM Products WHERE Name = ? AND IsDeleted = 0", (name,))

        if not product:
            errors.append(f"کالا یافت نشد: {code or name}")
            skipped += 1
            continue

        unit_cost = _to_float(r.get("UnitCost")) or float(product.get("PurchasePrice") or 0)

        try:
            item_id = db.execute(
                """INSERT INTO PurchaseInvoiceItems
                   (InvoiceRef, ProductRef, Quantity, UnitPrice, Discount, TotalPrice)
                   VALUES (?, ?, ?, ?, 0, ?)""",
                (invoice_id, product["ID"], qty, unit_cost, qty * unit_cost)
            )
            add_purchase_layer(db, product["ID"], item_id, qty, unit_cost)
            add_cardex_entry(
                db, product["ID"], "Purchase", "PurchaseInvoices", invoice_id,
                in_qty=qty, unit_cost=unit_cost,
                description="موجودی ابتدای دوره - Import از ربات"
            )
            imported += 1
        except Exception as e:
            errors.append(f"{code or name}: {e}")

    db.close()
    return {"imported": imported, "skipped": skipped, "errors": errors, "invoice_id": invoice_id}
