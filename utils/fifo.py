# -*- coding: utf-8 -*-
"""
ماژول مرکزی FIFO / کاردکس انبار.

توضیح مهم درباره جایگاه این فایل در پروژه:
--------------------------------------------
ثبت فاکتور خرید و فاکتور فروش از داخل رابط کاربری (purchase_window.py / sales_window.py)
به‌صورت یک تراکنش دیتابیسی واحد (cursor + commit/rollback) در خودِ
services/inventory_service.py و services/sales_service.py پیاده‌سازی شده تا در صورت خطا،
هیچ بخشی (فاکتور، لایه FIFO، کاردکس، سریال) به‌تنهایی ثبت نشود.

این فایل (utils/fifo.py) برای عملیات‌های ساده‌تر و مستقل است که لازم نیست حتماً بخشی
از یک فاکتور تعاملی باشند - مهم‌ترین مصرف‌کننده فعلی آن services/robat_import_service.py
است (Import موجودی اولیه از نرم‌افزار قبلی «ربات»). توابع این فایل مستقیماً روی
شیء Database (که هر db.execute خودش commit می‌کند) کار می‌کنند، دقیقاً هم‌ساختار با
همان جدول‌هایی که در inventory_service.py / sales_service.py استفاده شده‌اند:

    ProductPurchaseLayers (ProductRef, InvoiceItemRef, ShamsiDate,
                            OriginalQuantity, RemainingQuantity, UnitPrice)
    ProductCardex         (ProductRef, ShamsiDate, MovementType, RefTable, RefID,
                            InQuantity, OutQuantity, UnitPrice, BalanceQuantity,
                            Description, UserRef)
    Products.CurrentStock
    ProductSerials         (ProductRef, SerialNumber, IMEI, Status, PurchaseLayerRef)
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.persian_date import today_shamsi_str


# =========================================================
# افزودن یک لایه خرید جدید (FIFO) + افزایش موجودی کالا
# =========================================================
def add_purchase_layer(db, product_id: int, invoice_item_id: int,
                        quantity: float, unit_price: float,
                        shamsi_date: str = None) -> int:
    """
    یک لایه خرید جدید در ProductPurchaseLayers می‌سازد (برای مصرف بعدی توسط فروش‌ها
    با منطق FIFO - قدیمی‌ترین لایه اول مصرف می‌شود) و هم‌زمان موجودی فعلی کالا
    (Products.CurrentStock) را به همان اندازه افزایش می‌دهد.

    ورودی‌ها:
        db              نمونه‌ای از database.db.Database (باید متصل/آماده باشد)
        product_id      ID کالا در جدول Products
        invoice_item_id ID ردیف فاکتور خرید مرتبط (PurchaseInvoiceItems.ID)
        quantity        تعداد این لایه (باید > 0 باشد)
        unit_price      قیمت خرید واحد در این لایه
        shamsi_date     تاریخ شمسی لایه؛ اگر داده نشود، تاریخ امروز استفاده می‌شود

    خروجی: ID لایه ساخته‌شده (ProductPurchaseLayers.ID)
    """
    if quantity is None or float(quantity) <= 0:
        raise ValueError("تعداد لایه خرید باید بزرگ‌تر از صفر باشد.")

    shamsi_date = shamsi_date or today_shamsi_str()
    quantity = float(quantity)
    unit_price = float(unit_price or 0)

    layer_id = db.execute(
        """INSERT INTO ProductPurchaseLayers
           (ProductRef, InvoiceItemRef, ShamsiDate, OriginalQuantity, RemainingQuantity, UnitPrice)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (product_id, invoice_item_id, shamsi_date, quantity, quantity, unit_price)
    )

    db.execute(
        """UPDATE Products
           SET CurrentStock = CurrentStock + ?, PurchasePrice = ?, UpdatedAt = GETDATE()
           WHERE ID = ?""",
        (quantity, unit_price, product_id)
    )

    return layer_id


# =========================================================
# ثبت یک ردیف کاردکس (تاریخچه ورود/خروج کالا)
# =========================================================
def add_cardex_entry(db, product_id: int, movement_type: str, ref_table: str, ref_id: int,
                      in_qty: float = 0, out_qty: float = 0, unit_cost: float = 0,
                      description: str = "", user_id: int = None,
                      shamsi_date: str = None) -> int:
    """
    یک ردیف در ProductCardex ثبت می‌کند. موجودی لحظه‌ای (BalanceQuantity) از روی
    Products.CurrentStock فعلی خوانده می‌شود - بنابراین اگر این تابع بعد از
    add_purchase_layer یا هر تغییر دیگری در موجودی صدا زده شود، مانده صحیح ثبت خواهد شد.

    ورودی‌ها:
        db             نمونه‌ای از database.db.Database
        product_id     ID کالا
        movement_type  نوع حرکت، مثلاً 'Purchase' / 'Buy' / 'Sell' / 'Adjustment'
        ref_table      نام جدول مرجع (مثلاً 'PurchaseInvoices', 'SalesInvoices')
        ref_id         ID رکورد مرجع در همان جدول
        in_qty         مقدار ورودی (برای خرید/افزایش)
        out_qty        مقدار خروجی (برای فروش/کاهش)
        unit_cost      قیمت واحد این حرکت (در ستون UnitPrice جدول کاردکس ذخیره می‌شود)
        description    توضیح متنی
        user_id        ID کاربر ثبت‌کننده (اختیاری)
        shamsi_date    تاریخ شمسی؛ اگر داده نشود، تاریخ امروز استفاده می‌شود

    خروجی: ID ردیف کاردکس ساخته‌شده (ProductCardex.ID)
    """
    shamsi_date = shamsi_date or today_shamsi_str()
    in_qty = float(in_qty or 0)
    out_qty = float(out_qty or 0)
    unit_cost = float(unit_cost or 0)

    balance_row = db.fetch_one("SELECT CurrentStock FROM Products WHERE ID = ?", (product_id,))
    balance = float(balance_row["CurrentStock"]) if balance_row else 0.0

    cardex_id = db.execute(
        """INSERT INTO ProductCardex
           (ProductRef, ShamsiDate, MovementType, RefTable, RefID,
            InQuantity, OutQuantity, UnitPrice, BalanceQuantity, Description, UserRef)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (product_id, shamsi_date, movement_type, ref_table, ref_id,
         in_qty, out_qty, unit_cost, balance, description or "", user_id)
    )

    return cardex_id


# =========================================================
# کسر از قدیمی‌ترین لایه‌های FIFO (برای مصرف‌های مستقل خارج از فاکتور فروش تعاملی)
# =========================================================
def consume_fifo(db, product_id: int, quantity: float, allow_negative: bool = False):
    """
    از قدیمی‌ترین لایه‌های خرید باقیمانده یک کالا به ترتیب FIFO مصرف می‌کند، لایه‌ها را
    به‌روزرسانی و موجودی کالا (Products.CurrentStock) را کم می‌کند.

    توجه: هنگام ثبت فاکتور فروش از داخل رابط کاربری، services/sales_service.py منطق
    مشابه این تابع را خودش و در همان تراکنش فاکتور (cursor واحد) انجام می‌دهد تا
    اتمی بودن کل فاکتور تضمین شود؛ این تابع برای مصرف‌های ساده و مستقل (خارج از یک
    فاکتور تعاملی) است.

    ورودی‌ها:
        db              نمونه‌ای از database.db.Database
        product_id      ID کالا
        quantity        مقدار موردنیاز برای کسر (باید > 0 باشد)
        allow_negative  اگر True باشد و موجودی/لایه‌ها کافی نباشد، کمبود با آخرین
                         قیمت خرید کالا (Products.PurchasePrice) به‌عنوان بها محاسبه می‌شود

    خروجی: دیکشنری شامل:
        consumed:    لیستی از (layer_id, qty_from_layer, layer_unit_price)
        cost_amount: مجموع بهای تمام‌شده مصرف‌شده
        shortage:    مقداری که از موجودی/لایه‌ها کم آمده (۰ یعنی کاملاً پوشش داده شد)
    """
    if quantity is None or float(quantity) <= 0:
        raise ValueError("تعداد مصرف باید بزرگ‌تر از صفر باشد.")

    quantity = float(quantity)

    layers = db.fetch_all(
        """SELECT ID, RemainingQuantity, UnitPrice FROM ProductPurchaseLayers
           WHERE ProductRef = ? AND RemainingQuantity > 0
           ORDER BY ID""",
        (product_id,)
    )

    remaining_needed = quantity
    cost_amount = 0.0
    consumed = []

    for layer in layers:
        if remaining_needed <= 0:
            break
        layer_id = layer["ID"]
        layer_remaining = float(layer["RemainingQuantity"])
        layer_price = float(layer["UnitPrice"])
        take = min(layer_remaining, remaining_needed)

        db.execute(
            "UPDATE ProductPurchaseLayers SET RemainingQuantity = RemainingQuantity - ? WHERE ID = ?",
            (take, layer_id)
        )

        consumed.append((layer_id, take, layer_price))
        cost_amount += take * layer_price
        remaining_needed -= take

    shortage = remaining_needed
    if shortage > 0:
        if not allow_negative:
            raise ValueError(
                f"موجودی کالا (شناسه {product_id}) کافی نیست - کمبود: {shortage:g} عدد."
            )
        last_price_row = db.fetch_one("SELECT PurchasePrice FROM Products WHERE ID = ?", (product_id,))
        last_price = float(last_price_row["PurchasePrice"]) if last_price_row and last_price_row.get("PurchasePrice") else 0.0
        cost_amount += shortage * last_price

    db.execute(
        "UPDATE Products SET CurrentStock = CurrentStock - ?, UpdatedAt = GETDATE() WHERE ID = ?",
        (quantity, product_id)
    )

    return {"consumed": consumed, "cost_amount": cost_amount, "shortage": shortage}
