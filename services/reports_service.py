# -*- coding: utf-8 -*-
"""
لایه منطق تجاری «گزارش‌ها».
تمام گزارش‌ها (فروش، خرید، سود، سود و زیان خالص، موجودی، بدهکاران/بستانکاران،
چک‌ها، اقساط) از دیتابیس موجود (بدون نیاز به جدول جدید) محاسبه می‌شوند.
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import Database


# =========================================================
# گزارش فروش
# =========================================================
def sales_report(date_from: str, date_to: str, customer_id: int = None, product_id: int = None):
    """
    گزارش فروش در بازه تاریخ شمسی [date_from, date_to].
    اگر customer_id یا product_id داده شود، فیلتر اضافه می‌شود.
    خروجی: (rows, totals)
    """
    db = Database()

    if product_id:
        query = """
            SELECT si.ID, si.InvoiceNumber, si.ShamsiDate, p.FullName AS CustomerName,
                   pr.Name AS ProductName, sii.Quantity, sii.UnitPrice,
                   sii.DiscountAmount, sii.TotalPrice
            FROM SalesInvoiceItems sii
            JOIN SalesInvoices si ON si.ID = sii.InvoiceRef
            JOIN Persons p ON p.ID = si.PersonRef
            JOIN Products pr ON pr.ID = sii.ProductRef
            WHERE si.IsDeleted = 0 AND si.ShamsiDate BETWEEN ? AND ?
                  AND sii.ProductRef = ?
                  AND (? IS NULL OR si.PersonRef = ?)
            ORDER BY si.ShamsiDate, si.ID
        """
        rows = db.fetch_all(query, (date_from, date_to, product_id, customer_id, customer_id))
        total_sale = sum(float(r["TotalPrice"]) for r in rows)
        totals = {"count": len(rows), "total_sale": total_sale}
    else:
        query = """
            SELECT si.ID, si.InvoiceNumber, si.ShamsiDate, p.FullName AS CustomerName,
                   si.TotalAmount, si.DiscountAmount, si.TaxAmount, si.PayableAmount, si.PaidAmount
            FROM SalesInvoices si
            JOIN Persons p ON p.ID = si.PersonRef
            WHERE si.IsDeleted = 0 AND si.ShamsiDate BETWEEN ? AND ?
                  AND (? IS NULL OR si.PersonRef = ?)
            ORDER BY si.ShamsiDate, si.ID
        """
        rows = db.fetch_all(query, (date_from, date_to, customer_id, customer_id))
        totals = {
            "count": len(rows),
            "total_amount": sum(float(r["TotalAmount"]) for r in rows),
            "discount": sum(float(r["DiscountAmount"]) for r in rows),
            "payable": sum(float(r["PayableAmount"]) for r in rows),
            "paid": sum(float(r["PaidAmount"]) for r in rows),
        }
    db.close()
    return rows, totals


# =========================================================
# گزارش خرید
# =========================================================
def purchase_report(date_from: str, date_to: str, supplier_id: int = None):
    db = Database()
    query = """
        SELECT pi.ID, pi.InvoiceNumber, pi.ShamsiDate, p.FullName AS SupplierName,
               pi.TotalAmount, pi.DiscountAmount, pi.TaxAmount, pi.PayableAmount, pi.PaidAmount
        FROM PurchaseInvoices pi
        JOIN Persons p ON p.ID = pi.PersonRef
        WHERE pi.IsDeleted = 0 AND pi.ShamsiDate BETWEEN ? AND ?
              AND (? IS NULL OR pi.PersonRef = ?)
        ORDER BY pi.ShamsiDate, pi.ID
    """
    rows = db.fetch_all(query, (date_from, date_to, supplier_id, supplier_id))
    db.close()
    totals = {
        "count": len(rows),
        "total_amount": sum(float(r["TotalAmount"]) for r in rows),
        "payable": sum(float(r["PayableAmount"]) for r in rows),
        "paid": sum(float(r["PaidAmount"]) for r in rows),
    }
    return rows, totals


# =========================================================
# گزارش سود (بر اساس فاکتور، کالا یا مشتری)
# =========================================================
def profit_report(date_from: str, date_to: str, group_by: str = "invoice"):
    """
    group_by: 'invoice' | 'product' | 'customer'
    سود هر قلم = TotalPrice (فروش) - CostAmount (بهای تمام‌شده FIFO)
    """
    db = Database()

    if group_by == "product":
        query = """
            SELECT pr.ID, pr.Name AS ProductName,
                   SUM(sii.Quantity) AS TotalQty,
                   SUM(sii.TotalPrice) AS TotalSale,
                   SUM(sii.CostAmount) AS TotalCost,
                   SUM(sii.TotalPrice - sii.CostAmount) AS Profit
            FROM SalesInvoiceItems sii
            JOIN SalesInvoices si ON si.ID = sii.InvoiceRef
            JOIN Products pr ON pr.ID = sii.ProductRef
            WHERE si.IsDeleted = 0 AND si.ShamsiDate BETWEEN ? AND ?
            GROUP BY pr.ID, pr.Name
            ORDER BY Profit DESC
        """
    elif group_by == "customer":
        query = """
            SELECT p.ID, p.FullName AS CustomerName,
                   SUM(sii.TotalPrice) AS TotalSale,
                   SUM(sii.CostAmount) AS TotalCost,
                   SUM(sii.TotalPrice - sii.CostAmount) AS Profit
            FROM SalesInvoiceItems sii
            JOIN SalesInvoices si ON si.ID = sii.InvoiceRef
            JOIN Persons p ON p.ID = si.PersonRef
            WHERE si.IsDeleted = 0 AND si.ShamsiDate BETWEEN ? AND ?
            GROUP BY p.ID, p.FullName
            ORDER BY Profit DESC
        """
    else:  # invoice
        query = """
            SELECT si.ID, si.InvoiceNumber, si.ShamsiDate, p.FullName AS CustomerName,
                   SUM(sii.TotalPrice) AS TotalSale,
                   SUM(sii.CostAmount) AS TotalCost,
                   SUM(sii.TotalPrice - sii.CostAmount) AS Profit
            FROM SalesInvoiceItems sii
            JOIN SalesInvoices si ON si.ID = sii.InvoiceRef
            JOIN Persons p ON p.ID = si.PersonRef
            WHERE si.IsDeleted = 0 AND si.ShamsiDate BETWEEN ? AND ?
            GROUP BY si.ID, si.InvoiceNumber, si.ShamsiDate, p.FullName
            ORDER BY si.ShamsiDate, si.ID
        """

    rows = db.fetch_all(query, (date_from, date_to))
    db.close()

    totals = {
        "total_sale": sum(float(r["TotalSale"] or 0) for r in rows),
        "total_cost": sum(float(r["TotalCost"] or 0) for r in rows),
        "total_profit": sum(float(r["Profit"] or 0) for r in rows),
    }
    return rows, totals


# =========================================================
# سود و زیان خالص
# =========================================================
def net_profit_loss_report(date_from: str, date_to: str):
    db = Database()

    sales_row = db.fetch_one(
        """SELECT ISNULL(SUM(TotalAmount),0) AS TotalAmount,
                  ISNULL(SUM(DiscountAmount),0) AS Discount,
                  ISNULL(SUM(PayableAmount),0) AS Payable
           FROM SalesInvoices
           WHERE IsDeleted = 0 AND ShamsiDate BETWEEN ? AND ?""",
        (date_from, date_to)
    )

    cost_row = db.fetch_one(
        """SELECT ISNULL(SUM(sii.CostAmount),0) AS TotalCost
           FROM SalesInvoiceItems sii
           JOIN SalesInvoices si ON si.ID = sii.InvoiceRef
           WHERE si.IsDeleted = 0 AND si.ShamsiDate BETWEEN ? AND ?""",
        (date_from, date_to)
    )

    db.close()

    revenue = float(sales_row["Payable"] or 0)
    sales_discount = float(sales_row["Discount"] or 0)
    cogs = float(cost_row["TotalCost"] or 0)
    gross_profit = revenue - cogs

    return {
        "revenue": revenue,
        "sales_discount": sales_discount,
        "cogs": cogs,
        "gross_profit": gross_profit,
        # هزینه‌های عملیاتی هنوز جدول جداگانه ندارد؛ در توسعه آینده اضافه می‌شود
        "operating_expenses": 0,
        "net_profit": gross_profit,
    }


# =========================================================
# گزارش موجودی
# =========================================================
def inventory_report(search: str = ""):
    db = Database()
    like = f"%{search.strip()}%"
    rows = db.fetch_all(
        """SELECT pr.ID, pr.Name, pr.Code, pg.Name AS GroupName, pr.Brand,
                  pr.CurrentStock, pr.MinStock, pr.OrderPoint, pr.PurchasePrice, pr.SalePrice
           FROM Products pr
           LEFT JOIN ProductGroups pg ON pg.ID = pr.GroupRef
           WHERE pr.IsDeleted = 0 AND (pr.Name LIKE ? OR pr.Code LIKE ?)
           ORDER BY pr.Name""",
        (like, like)
    )

    # ارزش ریالی دقیق موجودی هر کالا بر اساس لایه‌های باقیمانده FIFO
    layer_values = db.fetch_all(
        """SELECT ProductRef, SUM(RemainingQuantity * UnitPrice) AS StockValue
           FROM ProductPurchaseLayers
           WHERE RemainingQuantity > 0
           GROUP BY ProductRef"""
    )
    db.close()

    value_map = {r["ProductRef"]: float(r["StockValue"] or 0) for r in layer_values}

    result = []
    total_qty = 0
    total_value = 0
    low_stock_count = 0
    zero_stock_count = 0

    for r in rows:
        stock = float(r["CurrentStock"] or 0)
        stock_value = value_map.get(r["ID"], 0)
        status = "عادی"
        if stock <= 0:
            status = "بدون موجودی"
            zero_stock_count += 1
        elif r["OrderPoint"] and stock <= float(r["OrderPoint"]):
            status = "کمبود"
            low_stock_count += 1
        elif r["MinStock"] and stock <= float(r["MinStock"]):
            status = "کمبود"
            low_stock_count += 1

        result.append({**r, "StockValue": stock_value, "Status": status})
        total_qty += stock
        total_value += stock_value

    totals = {
        "count": len(result),
        "total_qty": total_qty,
        "total_value": total_value,
        "low_stock_count": low_stock_count,
        "zero_stock_count": zero_stock_count,
    }
    return result, totals


def stagnant_products_report(days: int = 60):
    """کالاهایی که در N روز اخیر هیچ فروشی نداشته‌اند (کالای راکد)"""
    db = Database()
    rows = db.fetch_all(
        """SELECT pr.ID, pr.Name, pr.Code, pr.CurrentStock,
                  (SELECT MAX(c.ShamsiDate) FROM ProductCardex c
                   WHERE c.ProductRef = pr.ID AND c.MovementType = N'Sell') AS LastSaleDate
           FROM Products pr
           WHERE pr.IsDeleted = 0 AND pr.CurrentStock > 0
           ORDER BY pr.Name"""
    )
    db.close()
    # فیلتر راکدها در پایتون انجام می‌شود (چون تاریخ شمسی رشته‌ای است)
    stagnant = [r for r in rows if r["LastSaleDate"] is None]
    return stagnant


# =========================================================
# گزارش بدهکاران و بستانکاران
# =========================================================
def debtors_report():
    """بدهی مشتریان به فروشگاه = مجموع فاکتورهای فروش - مجموع دریافتی‌های تخصیص‌یافته"""
    db = Database()
    rows = db.fetch_all(
        """SELECT p.ID, p.FullName,
                  ISNULL(SUM(si.PayableAmount), 0) AS TotalSales,
                  ISNULL((SELECT SUM(ra.Amount) FROM ReceiptAllocations ra
                          JOIN SalesInvoices si2 ON si2.ID = ra.SalesInvoiceRef
                          WHERE si2.PersonRef = p.ID), 0) AS TotalReceived
           FROM Persons p
           JOIN SalesInvoices si ON si.PersonRef = p.ID AND si.IsDeleted = 0
           WHERE p.IsCustomer = 1 AND p.IsDeleted = 0
           GROUP BY p.ID, p.FullName
           HAVING ISNULL(SUM(si.PayableAmount), 0) >
                  ISNULL((SELECT SUM(ra.Amount) FROM ReceiptAllocations ra
                          JOIN SalesInvoices si2 ON si2.ID = ra.SalesInvoiceRef
                          WHERE si2.PersonRef = p.ID), 0)
           ORDER BY TotalSales DESC"""
    )
    db.close()
    result = []
    for r in rows:
        debt = float(r["TotalSales"] or 0) - float(r["TotalReceived"] or 0)
        result.append({"ID": r["ID"], "FullName": r["FullName"], "Debt": debt})
    total_debt = sum(r["Debt"] for r in result)
    return result, total_debt


def creditors_report():
    """بستانکاری تأمین‌کنندگان از فروشگاه = مجموع فاکتورهای خرید - مجموع پرداختی‌های تخصیص‌یافته"""
    db = Database()
    rows = db.fetch_all(
        """SELECT p.ID, p.FullName,
                  ISNULL(SUM(pi.PayableAmount), 0) AS TotalPurchases,
                  ISNULL((SELECT SUM(pa.Amount) FROM PaymentAllocations pa
                          JOIN PurchaseInvoices pi2 ON pi2.ID = pa.PurchaseInvoiceRef
                          WHERE pi2.PersonRef = p.ID), 0) AS TotalPaid
           FROM Persons p
           JOIN PurchaseInvoices pi ON pi.PersonRef = p.ID AND pi.IsDeleted = 0
           WHERE p.IsSeller = 1 AND p.IsDeleted = 0
           GROUP BY p.ID, p.FullName
           HAVING ISNULL(SUM(pi.PayableAmount), 0) >
                  ISNULL((SELECT SUM(pa.Amount) FROM PaymentAllocations pa
                          JOIN PurchaseInvoices pi2 ON pi2.ID = pa.PurchaseInvoiceRef
                          WHERE pi2.PersonRef = p.ID), 0)
           ORDER BY TotalPurchases DESC"""
    )
    db.close()
    result = []
    for r in rows:
        credit = float(r["TotalPurchases"] or 0) - float(r["TotalPaid"] or 0)
        result.append({"ID": r["ID"], "FullName": r["FullName"], "Credit": credit})
    total_credit = sum(r["Credit"] for r in result)
    return result, total_credit


# =========================================================
# گزارش چک‌ها
# =========================================================
def cheques_report(cheque_type: str = None, status: str = None, search: str = ""):
    db = Database()
    like = f"%{search.strip()}%"
    query = """
        SELECT c.ID, c.ChequeType, c.ChequeNumber, c.BankName, p.FullName AS PersonName,
               c.Amount, c.ShamsiDate, c.DueShamsiDate, c.Status
        FROM Cheques c
        JOIN Persons p ON p.ID = c.PersonRef
        WHERE (? IS NULL OR c.ChequeType = ?)
              AND (? IS NULL OR c.Status = ?)
              AND (c.ChequeNumber LIKE ? OR p.FullName LIKE ?)
        ORDER BY c.DueShamsiDate
    """
    rows = db.fetch_all(query, (cheque_type, cheque_type, status, status, like, like))
    db.close()
    total_amount = sum(float(r["Amount"]) for r in rows)
    return rows, total_amount


# =========================================================
# گزارش اقساط
# =========================================================
def installments_report(status: str = None):
    db = Database()
    query = """
        SELECT ii.ID, ip.ID AS PlanID, p.FullName AS CustomerName, ii.SeqNumber,
               ii.DueShamsiDate, ii.Amount, ii.Status, ii.PaidShamsiDate
        FROM InstallmentItems ii
        JOIN InstallmentPlans ip ON ip.ID = ii.PlanRef
        JOIN Persons p ON p.ID = ip.PersonRef
        WHERE ip.IsDeleted = 0 AND (? IS NULL OR ii.Status = ?)
        ORDER BY ii.DueShamsiDate
    """
    rows = db.fetch_all(query, (status, status))
    db.close()
    total_amount = sum(float(r["Amount"]) for r in rows)
    return rows, total_amount
