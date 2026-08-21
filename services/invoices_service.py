# -*- coding: utf-8 -*-
"""
لایه یکپارچه «لیست همه فاکتورها»: خرید، فروش و برگشت از خرید در یک جدول،
با قابلیت فیلتر بر اساس نوع فاکتور و جستجوی مشترک (شماره فاکتور یا نام طرف حساب).
این فایل فقط SELECT انجام می‌دهد؛ ثبت/ویرایش هر نوع فاکتور همچنان در
services/inventory_service.py و services/sales_service.py انجام می‌شود.
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import Database

INVOICE_TYPE_LABELS = {
    "Purchase": "خرید",
    "Sales": "فروش",
    "PurchaseReturn": "برگشت از خرید",
}


def get_all_invoices(search: str = "", invoice_type: str = "All"):
    """
    invoice_type یکی از: All, Purchase, Sales, PurchaseReturn

    خروجی هر ردیف: InvoiceType, ID, InvoiceNumber, ShamsiDate,
                    PersonName, PayableAmount, Description
    مرتب‌شده بر اساس تاریخ (جدیدترین اول).
    """
    like = f"%{search.strip()}%"
    parts = []
    params = []

    if invoice_type in ("All", "Purchase"):
        parts.append(
            """SELECT N'Purchase' AS InvoiceType, pi.ID, pi.InvoiceNumber, pi.ShamsiDate,
                      p.FullName AS PersonName, pi.PayableAmount, pi.Description
               FROM PurchaseInvoices pi JOIN Persons p ON p.ID = pi.PersonRef
               WHERE pi.IsDeleted = 0 AND
                     (CAST(pi.InvoiceNumber AS NVARCHAR(50)) LIKE ? OR p.FullName LIKE ?)"""
        )
        params += [like, like]

    if invoice_type in ("All", "Sales"):
        parts.append(
            """SELECT N'Sales', si.ID, si.InvoiceNumber, si.ShamsiDate,
                      p.FullName, si.PayableAmount, si.Description
               FROM SalesInvoices si JOIN Persons p ON p.ID = si.PersonRef
               WHERE si.IsDeleted = 0 AND
                     (CAST(si.InvoiceNumber AS NVARCHAR(50)) LIKE ? OR p.FullName LIKE ?)"""
        )
        params += [like, like]

    if invoice_type in ("All", "PurchaseReturn"):
        parts.append(
            """SELECT N'PurchaseReturn', pri.ID, pri.InvoiceNumber, pri.ShamsiDate,
                      p.FullName, pri.PayableAmount, pri.Description
               FROM PurchaseReturnInvoices pri JOIN Persons p ON p.ID = pri.PersonRef
               WHERE pri.IsDeleted = 0 AND
                     (CAST(pri.InvoiceNumber AS NVARCHAR(50)) LIKE ? OR p.FullName LIKE ?)"""
        )
        params += [like, like]

    if not parts:
        return []

    query = (
        "SELECT * FROM (" + " UNION ALL ".join(parts) + ") AS AllInvoices "
        "ORDER BY ShamsiDate DESC, ID DESC"
    )

    db = Database()
    rows = db.fetch_all(query, tuple(params))
    db.close()
    return rows
