# -*- coding: utf-8 -*-
"""
لایه منطق تجاری «مالی»: صندوق، بانک، دریافت، پرداخت، چک، اقساط.
هر عملیات مالی به‌صورت تراکنش اتمیک ثبت می‌شود (یا کامل ثبت می‌شود یا هیچ‌چیز).
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import Database
from services.audit_service import create_audit_entry
from utils.persian_date import add_months_shamsi


class FinancialError(Exception):
    """خطای قابل‌فهم برای نمایش به کاربر (نه خطای فنی دیتابیس)"""
    pass


# =========================================================
# صندوق‌ها و حساب‌های بانکی
# =========================================================

def get_cash_boxes(active_only: bool = False):
    db = Database()
    q = "SELECT ID, Name, InitialBalance, CurrentBalance, IsActive FROM CashBoxes"
    if active_only:
        q += " WHERE IsActive = 1"
    q += " ORDER BY Name"
    rows = db.fetch_all(q)
    db.close()
    return rows


def get_bank_accounts(active_only: bool = False):
    db = Database()
    q = ("SELECT ID, BankName, AccountTitle, AccountNumber, Sheba, CardNumber, "
         "InitialBalance, CurrentBalance, IsActive FROM BankAccounts")
    if active_only:
        q += " WHERE IsActive = 1"
    q += " ORDER BY BankName"
    rows = db.fetch_all(q)
    db.close()
    return rows


def create_cash_box(name: str, initial_balance: float):
    if not name.strip():
        raise FinancialError("نام صندوق نمی‌تواند خالی باشد.")
    db = Database()
    db.execute(
        "INSERT INTO CashBoxes (Name, InitialBalance, CurrentBalance) VALUES (?,?,?)",
        (name.strip(), initial_balance or 0, initial_balance or 0)
    )
    db.close()


def create_bank_account(bank_name: str, account_title: str, account_number: str,
                         sheba: str, card_number: str, initial_balance: float):
    if not bank_name.strip():
        raise FinancialError("نام بانک نمی‌تواند خالی باشد.")
    db = Database()
    db.execute(
        """INSERT INTO BankAccounts
           (BankName, AccountTitle, AccountNumber, Sheba, CardNumber, InitialBalance, CurrentBalance)
           VALUES (?,?,?,?,?,?,?)""",
        (bank_name.strip(), account_title or "", account_number or "", sheba or "",
         card_number or "", initial_balance or 0, initial_balance or 0)
    )
    db.close()


def set_cash_box_active(cash_box_id: int, is_active: bool):
    db = Database()
    db.execute("UPDATE CashBoxes SET IsActive = ? WHERE ID = ?", (1 if is_active else 0, cash_box_id))
    db.close()


def set_bank_account_active(bank_account_id: int, is_active: bool):
    db = Database()
    db.execute("UPDATE BankAccounts SET IsActive = ? WHERE ID = ?", (1 if is_active else 0, bank_account_id))
    db.close()


def get_cash_box_transactions(cash_box_id: int):
    db = Database()
    rows = db.fetch_all(
        """SELECT ID, TransactionType, Amount, BalanceAfter, RefTable, RefID,
                  ShamsiDate, Description
           FROM CashBoxTransactions WHERE CashBoxRef = ? ORDER BY ID DESC""",
        (cash_box_id,)
    )
    db.close()
    return rows


def get_bank_transactions(bank_account_id: int):
    db = Database()
    rows = db.fetch_all(
        """SELECT ID, TransactionType, Amount, BalanceAfter, RefTable, RefID,
                  ShamsiDate, Description
           FROM BankTransactions WHERE BankAccountRef = ? ORDER BY ID DESC""",
        (bank_account_id,)
    )
    db.close()
    return rows


def manual_cash_box_transaction(cash_box_id: int, tx_type: str, amount: float,
                                 shamsi_date: str, description: str, user_id: int):
    """واریز/برداشت دستی به صندوق (مثلاً واریز سرمایه اولیه)"""
    if amount is None or amount <= 0:
        raise FinancialError("مبلغ باید بزرگ‌تر از صفر باشد.")
    if tx_type not in ("In", "Out"):
        raise FinancialError("نوع تراکنش نامعتبر است.")
    db = Database()
    conn = db.connect()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT CurrentBalance FROM CashBoxes WHERE ID = ?", (cash_box_id,))
        row = cursor.fetchone()
        if not row:
            raise FinancialError("صندوق یافت نشد.")
        balance = float(row[0])
        new_balance = balance + amount if tx_type == "In" else balance - amount
        cursor.execute("UPDATE CashBoxes SET CurrentBalance = ? WHERE ID = ?", (new_balance, cash_box_id))
        cursor.execute(
            """INSERT INTO CashBoxTransactions
               (CashBoxRef, TransactionType, Amount, BalanceAfter, RefTable, ShamsiDate, Description, UserRef)
               VALUES (?,?,?,?,N'Manual',?,?,?)""",
            (cash_box_id, tx_type, amount, new_balance, shamsi_date, description or "", user_id)
        )
        conn.commit()
        create_audit_entry(user_id, "Create", "Payments", payment_id, f"Payment {payment_number}")
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        db.close()


def manual_bank_transaction(bank_account_id: int, tx_type: str, amount: float,
                             shamsi_date: str, description: str, user_id: int):
    """واریز/برداشت دستی به حساب بانکی"""
    if amount is None or amount <= 0:
        raise FinancialError("مبلغ باید بزرگ‌تر از صفر باشد.")
    if tx_type not in ("Deposit", "Withdraw"):
        raise FinancialError("نوع تراکنش نامعتبر است.")
    db = Database()
    conn = db.connect()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT CurrentBalance FROM BankAccounts WHERE ID = ?", (bank_account_id,))
        row = cursor.fetchone()
        if not row:
            raise FinancialError("حساب بانکی یافت نشد.")
        balance = float(row[0])
        new_balance = balance + amount if tx_type == "Deposit" else balance - amount
        cursor.execute("UPDATE BankAccounts SET CurrentBalance = ? WHERE ID = ?", (new_balance, bank_account_id))
        cursor.execute(
            """INSERT INTO BankTransactions
               (BankAccountRef, TransactionType, Amount, BalanceAfter, RefTable, ShamsiDate, Description, UserRef)
               VALUES (?,?,?,?,N'Manual',?,?,?)""",
            (bank_account_id, tx_type, amount, new_balance, shamsi_date, description or "", user_id)
        )
        conn.commit()
        create_audit_entry(user_id, "Create", "Payments", payment_id, f"Payment {payment_number}")
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        db.close()


# =========================================================
# اشخاص با بدهی/طلب باز (برای انتخاب در فرم دریافت/پرداخت)
# =========================================================

def get_customers():
    db = Database()
    rows = db.fetch_all(
        "SELECT ID, FullName FROM Persons WHERE IsCustomer = 1 AND IsDeleted = 0 ORDER BY FullName"
    )
    db.close()
    return rows


def get_suppliers():
    db = Database()
    rows = db.fetch_all(
        "SELECT ID, FullName FROM Persons WHERE IsSeller = 1 AND IsDeleted = 0 ORDER BY FullName"
    )
    db.close()
    return rows


def get_unpaid_sales_invoices(person_id: int):
    """فاکتورهای فروش این مشتری که هنوز کامل تسویه نشده‌اند"""
    db = Database()
    rows = db.fetch_all(
        """SELECT ID, InvoiceNumber, ShamsiDate, PayableAmount, PaidAmount,
                  (PayableAmount - PaidAmount) AS Remaining
           FROM SalesInvoices
           WHERE PersonRef = ? AND IsDeleted = 0 AND (PayableAmount - PaidAmount) > 0.5
           ORDER BY ID""",
        (person_id,)
    )
    db.close()
    return rows


def get_unpaid_purchase_invoices(person_id: int):
    """فاکتورهای خرید این تأمین‌کننده که هنوز کامل تسویه نشده‌اند"""
    db = Database()
    rows = db.fetch_all(
        """SELECT ID, InvoiceNumber, ShamsiDate, PayableAmount, PaidAmount,
                  (PayableAmount - PaidAmount) AS Remaining
           FROM PurchaseInvoices
           WHERE PersonRef = ? AND IsDeleted = 0 AND (PayableAmount - PaidAmount) > 0.5
           ORDER BY ID""",
        (person_id,)
    )
    db.close()
    return rows


# =========================================================
# دریافت وجه (از مشتری)
# =========================================================

def get_receipts(search: str = ""):
    db = Database()
    like = f"%{search.strip()}%"
    rows = db.fetch_all(
        """SELECT r.ID, r.ReceiptNumber, r.ShamsiDate, p.FullName AS PersonName,
                  r.TotalAmount, r.Description
           FROM Receipts r
           JOIN Persons p ON p.ID = r.PersonRef
           WHERE r.IsDeleted = 0 AND
                 (CAST(r.ReceiptNumber AS NVARCHAR(50)) LIKE ? OR p.FullName LIKE ?)
           ORDER BY r.ID DESC""",
        (like, like)
    )
    db.close()
    return rows


def _insert_cheque(cursor, cheque_type, cheque_info, person_id, ref_table, user_id):
    cursor.execute(
        """INSERT INTO Cheques
           (ChequeType, ChequeNumber, SayadNumber, BankName, PersonRef, Amount,
            ShamsiDate, DueShamsiDate, Status, RefTable, Description, UserRef)
           VALUES (?,?,?,?,?,?,?,?,N'InHand',?,?,?)""",
        (cheque_type, cheque_info["number"], cheque_info.get("sayad", ""), cheque_info.get("bank", ""),
         person_id, cheque_info["amount"], cheque_info.get("issue_date", ""), cheque_info["due_date"],
         ref_table, cheque_info.get("description", ""), user_id)
    )
    cursor.execute("SELECT @@IDENTITY AS id")
    cheque_id = int(cursor.fetchone()[0])
    return cheque_id


def create_receipt(customer_id: int, shamsi_date: str, description: str, user_id: int,
                    lines: list, allocations: list):
    """
    ثبت سند دریافت وجه از مشتری.
    lines: هر عنصر دیکشنری با کلید method ('Cash'/'Bank'/'Cheque') و amount، و بسته به نوع:
        Cash -> cash_box_id
        Bank -> bank_account_id
        Cheque -> cheque: {number, sayad, bank, issue_date, due_date, description}
    allocations: لیستی از {invoice_id, amount} - تخصیص مبلغ دریافتی به فاکتور(های) فروش
                 (جمع آن می‌تواند کمتر یا مساوی جمع کل باشد؛ مازاد به‌عنوان دریافت علی‌الحساب باقی می‌ماند)
    """
    if not lines:
        raise FinancialError("حداقل یک روش دریافت (نقد/بانک/چک) باید وارد شود.")

    total_amount = sum(float(l["amount"]) for l in lines)
    if total_amount <= 0:
        raise FinancialError("مبلغ کل دریافت باید بزرگ‌تر از صفر باشد.")

    alloc_sum = sum(float(a["amount"]) for a in (allocations or []))
    if alloc_sum > total_amount + 0.5:
        raise FinancialError("مجموع مبلغ تخصیص‌یافته به فاکتورها نمی‌تواند از مبلغ کل دریافت بیشتر باشد.")

    db = Database()
    conn = db.connect()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT ISNULL(MAX(ReceiptNumber), 4000) + 1 AS NextNum FROM Receipts")
        receipt_number = int(cursor.fetchone()[0])

        cursor.execute(
            """INSERT INTO Receipts (ReceiptNumber, PersonRef, ShamsiDate, TotalAmount, Description, UserRef)
               VALUES (?,?,?,?,?,?)""",
            (receipt_number, customer_id, shamsi_date, total_amount, description or "", user_id)
        )
        cursor.execute("SELECT @@IDENTITY AS id")
        receipt_id = int(cursor.fetchone()[0])

        for line in lines:
            method = line["method"]
            amount = float(line["amount"])
            if amount <= 0:
                raise FinancialError("مبلغ هر ردیف دریافت باید بزرگ‌تر از صفر باشد.")

            cash_box_id = bank_account_id = cheque_id = None

            if method == "Cash":
                cash_box_id = int(line["cash_box_id"])
                cursor.execute("SELECT CurrentBalance FROM CashBoxes WHERE ID = ?", (cash_box_id,))
                balance = float(cursor.fetchone()[0]) + amount
                cursor.execute("UPDATE CashBoxes SET CurrentBalance = ? WHERE ID = ?", (balance, cash_box_id))
                cursor.execute(
                    """INSERT INTO CashBoxTransactions
                       (CashBoxRef, TransactionType, Amount, BalanceAfter, RefTable, RefID, ShamsiDate, Description, UserRef)
                       VALUES (?,N'In',?,?,N'Receipts',?,?,?,?)""",
                    (cash_box_id, amount, balance, receipt_id, shamsi_date,
                     f"دریافت وجه سند شماره {receipt_number}", user_id)
                )

            elif method == "Bank":
                bank_account_id = int(line["bank_account_id"])
                cursor.execute("SELECT CurrentBalance FROM BankAccounts WHERE ID = ?", (bank_account_id,))
                balance = float(cursor.fetchone()[0]) + amount
                cursor.execute("UPDATE BankAccounts SET CurrentBalance = ? WHERE ID = ?", (balance, bank_account_id))
                cursor.execute(
                    """INSERT INTO BankTransactions
                       (BankAccountRef, TransactionType, Amount, BalanceAfter, RefTable, RefID, ShamsiDate, Description, UserRef)
                       VALUES (?,N'Deposit',?,?,N'Receipts',?,?,?,?)""",
                    (bank_account_id, amount, balance, receipt_id, shamsi_date,
                     f"دریافت وجه سند شماره {receipt_number}", user_id)
                )

            elif method == "Cheque":
                cheque_info = dict(line["cheque"])
                cheque_info["amount"] = amount
                cheque_id = _insert_cheque(cursor, "Received", cheque_info, customer_id, "Receipts", user_id)
                cursor.execute("UPDATE Cheques SET RefID = ? WHERE ID = ?", (receipt_id, cheque_id))

            else:
                raise FinancialError("روش دریافت نامعتبر است.")

            cursor.execute(
                """INSERT INTO ReceiptLines (ReceiptRef, MethodType, CashBoxRef, BankAccountRef, ChequeRef, Amount)
                   VALUES (?,?,?,?,?,?)""",
                (receipt_id, method, cash_box_id, bank_account_id, cheque_id, amount)
            )

        for alloc in (allocations or []):
            invoice_id = int(alloc["invoice_id"])
            amount = float(alloc["amount"])
            if amount <= 0:
                continue
            cursor.execute(
                "INSERT INTO ReceiptAllocations (ReceiptRef, SalesInvoiceRef, Amount) VALUES (?,?,?)",
                (receipt_id, invoice_id, amount)
            )
            cursor.execute(
                "UPDATE SalesInvoices SET PaidAmount = PaidAmount + ? WHERE ID = ?",
                (amount, invoice_id)
            )

        conn.commit()
        create_audit_entry(user_id, "Create", "Payments", payment_id, f"Payment {payment_number}")
        return receipt_id, receipt_number

    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        db.close()


# =========================================================
# پرداخت وجه (به تأمین‌کننده)
# =========================================================

def get_payments(search: str = ""):
    db = Database()
    like = f"%{search.strip()}%"
    rows = db.fetch_all(
        """SELECT p.ID, p.PaymentNumber, p.ShamsiDate, pr.FullName AS PersonName,
                  p.TotalAmount, p.Description
           FROM Payments p
           JOIN Persons pr ON pr.ID = p.PersonRef
           WHERE p.IsDeleted = 0 AND
                 (CAST(p.PaymentNumber AS NVARCHAR(50)) LIKE ? OR pr.FullName LIKE ?)
           ORDER BY p.ID DESC""",
        (like, like)
    )
    db.close()
    return rows


def create_payment(supplier_id: int, shamsi_date: str, description: str, user_id: int,
                    lines: list, allocations: list):
    """ثبت سند پرداخت وجه به تأمین‌کننده - مشابه create_receipt ولی برعکس (کاهش موجودی صندوق/بانک)"""
    if not lines:
        raise FinancialError("حداقل یک روش پرداخت (نقد/بانک/چک) باید وارد شود.")

    total_amount = sum(float(l["amount"]) for l in lines)
    if total_amount <= 0:
        raise FinancialError("مبلغ کل پرداخت باید بزرگ‌تر از صفر باشد.")

    alloc_sum = sum(float(a["amount"]) for a in (allocations or []))
    if alloc_sum > total_amount + 0.5:
        raise FinancialError("مجموع مبلغ تخصیص‌یافته به فاکتورها نمی‌تواند از مبلغ کل پرداخت بیشتر باشد.")

    db = Database()
    conn = db.connect()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT ISNULL(MAX(PaymentNumber), 5000) + 1 AS NextNum FROM Payments")
        payment_number = int(cursor.fetchone()[0])

        cursor.execute(
            """INSERT INTO Payments (PaymentNumber, PersonRef, ShamsiDate, TotalAmount, Description, UserRef)
               VALUES (?,?,?,?,?,?)""",
            (payment_number, supplier_id, shamsi_date, total_amount, description or "", user_id)
        )
        cursor.execute("SELECT @@IDENTITY AS id")
        payment_id = int(cursor.fetchone()[0])

        for line in lines:
            method = line["method"]
            amount = float(line["amount"])
            if amount <= 0:
                raise FinancialError("مبلغ هر ردیف پرداخت باید بزرگ‌تر از صفر باشد.")

            cash_box_id = bank_account_id = cheque_id = None

            if method == "Cash":
                cash_box_id = int(line["cash_box_id"])
                cursor.execute("SELECT CurrentBalance FROM CashBoxes WHERE ID = ?", (cash_box_id,))
                balance = float(cursor.fetchone()[0]) - amount
                cursor.execute("UPDATE CashBoxes SET CurrentBalance = ? WHERE ID = ?", (balance, cash_box_id))
                cursor.execute(
                    """INSERT INTO CashBoxTransactions
                       (CashBoxRef, TransactionType, Amount, BalanceAfter, RefTable, RefID, ShamsiDate, Description, UserRef)
                       VALUES (?,N'Out',?,?,N'Payments',?,?,?,?)""",
                    (cash_box_id, amount, balance, payment_id, shamsi_date,
                     f"پرداخت وجه سند شماره {payment_number}", user_id)
                )

            elif method == "Bank":
                bank_account_id = int(line["bank_account_id"])
                cursor.execute("SELECT CurrentBalance FROM BankAccounts WHERE ID = ?", (bank_account_id,))
                balance = float(cursor.fetchone()[0]) - amount
                cursor.execute("UPDATE BankAccounts SET CurrentBalance = ? WHERE ID = ?", (balance, bank_account_id))
                cursor.execute(
                    """INSERT INTO BankTransactions
                       (BankAccountRef, TransactionType, Amount, BalanceAfter, RefTable, RefID, ShamsiDate, Description, UserRef)
                       VALUES (?,N'Withdraw',?,?,N'Payments',?,?,?,?)""",
                    (bank_account_id, amount, balance, payment_id, shamsi_date,
                     f"پرداخت وجه سند شماره {payment_number}", user_id)
                )

            elif method == "Cheque":
                cheque_info = dict(line["cheque"])
                cheque_info["amount"] = amount
                cheque_id = _insert_cheque(cursor, "Issued", cheque_info, supplier_id, "Payments", user_id)
                cursor.execute("UPDATE Cheques SET RefID = ? WHERE ID = ?", (payment_id, cheque_id))

            else:
                raise FinancialError("روش پرداخت نامعتبر است.")

            cursor.execute(
                """INSERT INTO PaymentLines (PaymentRef, MethodType, CashBoxRef, BankAccountRef, ChequeRef, Amount)
                   VALUES (?,?,?,?,?,?)""",
                (payment_id, method, cash_box_id, bank_account_id, cheque_id, amount)
            )

        for alloc in (allocations or []):
            invoice_id = int(alloc["invoice_id"])
            amount = float(alloc["amount"])
            if amount <= 0:
                continue
            cursor.execute(
                "INSERT INTO PaymentAllocations (PaymentRef, PurchaseInvoiceRef, Amount) VALUES (?,?,?)",
                (payment_id, invoice_id, amount)
            )
            cursor.execute(
                "UPDATE PurchaseInvoices SET PaidAmount = PaidAmount + ? WHERE ID = ?",
                (amount, invoice_id)
            )

        conn.commit()
        create_audit_entry(user_id, "Create", "Payments", payment_id, f"Payment {payment_number}")
        return payment_id, payment_number

    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        db.close()


# =========================================================
# چک‌ها
# =========================================================

def get_cheques(cheque_type: str = None, search: str = ""):
    db = Database()
    like = f"%{search.strip()}%"
    q = """SELECT c.ID, c.ChequeType, c.ChequeNumber, c.BankName, p.FullName AS PersonName,
                  c.Amount, c.ShamsiDate, c.DueShamsiDate, c.Status, c.Description
           FROM Cheques c
           JOIN Persons p ON p.ID = c.PersonRef
           WHERE (CAST(c.ChequeNumber AS NVARCHAR(100)) LIKE ? OR p.FullName LIKE ? OR c.BankName LIKE ?)"""
    params = [like, like, like]
    if cheque_type in ("Received", "Issued"):
        q += " AND c.ChequeType = ?"
        params.append(cheque_type)
    q += " ORDER BY c.DueShamsiDate, c.ID DESC"
    rows = db.fetch_all(q, tuple(params))
    db.close()
    return rows


def change_cheque_status(cheque_id: int, new_status: str, shamsi_date: str, user_id: int,
                          cash_box_id: int = None, bank_account_id: int = None, note: str = ""):
    """
    تغییر وضعیت چک.
    - برای انتقال به Deposited: فقط وضعیت عوض می‌شود (چک به بانک برده شده، هنوز وصول نشده).
    - برای Cashed: باید یکی از cash_box_id یا bank_account_id داده شود تا مبلغ چک به آن اضافه/کم شود.
      (چک دریافتی -> افزایش موجودی صندوق/بانک ما / چک پرداختی -> کاهش موجودی صندوق/بانک ما)
    - برای Bounced/Returned: فقط وضعیت عوض می‌شود؛ حرکت مالی جدیدی ثبت نمی‌شود.
      توجه: در صورت برگشت خوردن چک دریافتی که بابت فاکتور فروش تخصیص یافته بود،
      لازم است وضعیت بدهی مشتری به‌صورت جداگانه (مثلاً با ثبت سند دریافت اصلاحی) بررسی شود.
    """
    valid_status = {"InHand", "Deposited", "Cashed", "Bounced", "Returned"}
    if new_status not in valid_status:
        raise FinancialError("وضعیت چک نامعتبر است.")

    db = Database()
    conn = db.connect()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT ChequeType, Amount, Status, ChequeNumber FROM Cheques WHERE ID = ?", (cheque_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise FinancialError("چک یافت نشد.")
        cheque_type, amount, current_status, cheque_number = row[0], float(row[1]), row[2], row[3]

        if current_status in ("Cashed", "Bounced", "Returned"):
            raise FinancialError("وضعیت این چک قبلاً نهایی شده و قابل تغییر مجدد نیست.")

        if new_status == "Cashed":
            if not cash_box_id and not bank_account_id:
                raise FinancialError("برای نقد کردن چک باید صندوق یا حساب بانکی مقصد را انتخاب کنید.")

            if cash_box_id:
                cursor.execute("SELECT CurrentBalance FROM CashBoxes WHERE ID = ?", (cash_box_id,))
                balance = float(cursor.fetchone()[0])
                balance = balance + amount if cheque_type == "Received" else balance - amount
                cursor.execute("UPDATE CashBoxes SET CurrentBalance = ? WHERE ID = ?", (balance, cash_box_id))
                cursor.execute(
                    """INSERT INTO CashBoxTransactions
                       (CashBoxRef, TransactionType, Amount, BalanceAfter, RefTable, RefID, ShamsiDate, Description, UserRef)
                       VALUES (?,?,?,?,N'Cheques',?,?,?,?)""",
                    (cash_box_id, "In" if cheque_type == "Received" else "Out", amount, balance,
                     cheque_id, shamsi_date, f"وصول چک شماره {cheque_number}", user_id)
                )
                cursor.execute("UPDATE Cheques SET CashBoxRef = ? WHERE ID = ?", (cash_box_id, cheque_id))

            if bank_account_id:
                cursor.execute("SELECT CurrentBalance FROM BankAccounts WHERE ID = ?", (bank_account_id,))
                balance = float(cursor.fetchone()[0])
                balance = balance + amount if cheque_type == "Received" else balance - amount
                cursor.execute("UPDATE BankAccounts SET CurrentBalance = ? WHERE ID = ?", (balance, bank_account_id))
                cursor.execute(
                    """INSERT INTO BankTransactions
                       (BankAccountRef, TransactionType, Amount, BalanceAfter, RefTable, RefID, ShamsiDate, Description, UserRef)
                       VALUES (?,?,?,?,N'Cheques',?,?,?,?)""",
                    (bank_account_id, "Deposit" if cheque_type == "Received" else "Withdraw", amount, balance,
                     cheque_id, shamsi_date, f"وصول چک شماره {cheque_number}", user_id)
                )
                cursor.execute("UPDATE Cheques SET BankAccountRef = ? WHERE ID = ?", (bank_account_id, cheque_id))

        extra_desc = f" | {note.strip()}" if note and note.strip() else ""
        cursor.execute(
            "UPDATE Cheques SET Status = ?, Description = ISNULL(Description,N'') + ? WHERE ID = ?",
            (new_status, extra_desc, cheque_id)
        )

        conn.commit()
        create_audit_entry(user_id, "Create", "Payments", payment_id, f"Payment {payment_number}")
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        db.close()


# =========================================================
# اقساط
# =========================================================

def get_installment_plans(search: str = ""):
    db = Database()
    like = f"%{search.strip()}%"
    rows = db.fetch_all(
        """SELECT ip.ID, ip.ShamsiDate, p.FullName AS PersonName, si.InvoiceNumber,
                  ip.TotalAmount, ip.InstallmentCount,
                  (SELECT COUNT(*) FROM InstallmentItems ii WHERE ii.PlanRef = ip.ID AND ii.Status = N'Paid') AS PaidCount
           FROM InstallmentPlans ip
           JOIN Persons p ON p.ID = ip.PersonRef
           JOIN SalesInvoices si ON si.ID = ip.SalesInvoiceRef
           WHERE ip.IsDeleted = 0 AND p.FullName LIKE ?
           ORDER BY ip.ID DESC""",
        (like,)
    )
    db.close()
    return rows


def get_installment_items(plan_id: int):
    db = Database()
    rows = db.fetch_all(
        """SELECT ID, SeqNumber, DueShamsiDate, Amount, Status, PaidShamsiDate
           FROM InstallmentItems WHERE PlanRef = ? ORDER BY SeqNumber""",
        (plan_id,)
    )
    db.close()
    return rows


def create_installment_plan(customer_id: int, sales_invoice_id: int, shamsi_date: str,
                             description: str, user_id: int, installments: list):
    """
    ثبت طرح اقساط برای یک فاکتور فروش.
    installments: لیستی از {due_date, amount} به ترتیب سررسید.
    """
    if not installments:
        raise FinancialError("حداقل یک قسط باید وارد شود.")

    total_amount = sum(float(i["amount"]) for i in installments)
    if total_amount <= 0:
        raise FinancialError("جمع مبلغ اقساط باید بزرگ‌تر از صفر باشد.")

    db = Database()
    conn = db.connect()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """INSERT INTO InstallmentPlans
               (PersonRef, SalesInvoiceRef, TotalAmount, InstallmentCount, ShamsiDate, Description, UserRef)
               VALUES (?,?,?,?,?,?,?)""",
            (customer_id, sales_invoice_id, total_amount, len(installments),
             shamsi_date, description or "", user_id)
        )
        cursor.execute("SELECT @@IDENTITY AS id")
        plan_id = int(cursor.fetchone()[0])

        for seq, item in enumerate(installments, start=1):
            amount = float(item["amount"])
            if amount <= 0:
                raise FinancialError(f"مبلغ قسط شماره {seq} باید بزرگ‌تر از صفر باشد.")
            cursor.execute(
                """INSERT INTO InstallmentItems (PlanRef, SeqNumber, DueShamsiDate, Amount)
                   VALUES (?,?,?,?)""",
                (plan_id, seq, item["due_date"], amount)
            )

        conn.commit()
        create_audit_entry(user_id, "Create", "Payments", payment_id, f"Payment {payment_number}")
        return plan_id
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        db.close()


def generate_equal_installments(total_amount: float, count: int, start_shamsi_date: str, months_apart: int = 1):
    """کمکی برای UI: تقسیم مساوی مبلغ کل به N قسط با فاصله چند ماهه (قابل ویرایش دستی بعد از تولید)"""
    if count <= 0:
        raise FinancialError("تعداد اقساط باید بزرگ‌تر از صفر باشد.")
    base = round(total_amount / count)
    items = []
    running_total = 0
    for i in range(count):
        amount = base
        if i == count - 1:
            amount = total_amount - running_total  # قسط آخر اختلاف رند شدن را جبران می‌کند
        running_total += amount
        due = add_months_shamsi(start_shamsi_date, months_apart * (i + 1))
        items.append({"due_date": due, "amount": amount})
    return items


def mark_installment_paid(item_id: int, method: str, shamsi_date: str, user_id: int,
                           cash_box_id: int = None, bank_account_id: int = None):
    """
    پرداخت یک قسط را ثبت می‌کند: یک سند دریافت خودکار (نقد یا بانک) می‌سازد،
    آن را به فاکتور فروش مربوطه تخصیص می‌دهد و وضعیت قسط را «پرداخت‌شده» می‌کند.
    """
    if method not in ("Cash", "Bank"):
        raise FinancialError("روش پرداخت قسط باید نقد یا بانک باشد.")

    db = Database()
    conn = db.connect()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """SELECT ii.Amount, ii.Status, ii.SeqNumber, ip.PersonRef, ip.SalesInvoiceRef
               FROM InstallmentItems ii JOIN InstallmentPlans ip ON ip.ID = ii.PlanRef
               WHERE ii.ID = ?""",
            (item_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise FinancialError("قسط یافت نشد.")
        amount, status, seq, person_id, invoice_id = float(row[0]), row[1], row[2], row[3], row[4]
        if status == "Paid":
            raise FinancialError("این قسط قبلاً پرداخت شده است.")

        cursor.execute("SELECT ISNULL(MAX(ReceiptNumber), 4000) + 1 AS NextNum FROM Receipts")
        receipt_number = int(cursor.fetchone()[0])
        cursor.execute(
            """INSERT INTO Receipts (ReceiptNumber, PersonRef, ShamsiDate, TotalAmount, Description, UserRef)
               VALUES (?,?,?,?,?,?)""",
            (receipt_number, person_id, shamsi_date, amount, f"دریافت قسط شماره {seq}", user_id)
        )
        cursor.execute("SELECT @@IDENTITY AS id")
        receipt_id = int(cursor.fetchone()[0])

        cash_box_ref = bank_account_ref = None
        if method == "Cash":
            cash_box_ref = int(cash_box_id)
            cursor.execute("SELECT CurrentBalance FROM CashBoxes WHERE ID = ?", (cash_box_ref,))
            balance = float(cursor.fetchone()[0]) + amount
            cursor.execute("UPDATE CashBoxes SET CurrentBalance = ? WHERE ID = ?", (balance, cash_box_ref))
            cursor.execute(
                """INSERT INTO CashBoxTransactions
                   (CashBoxRef, TransactionType, Amount, BalanceAfter, RefTable, RefID, ShamsiDate, Description, UserRef)
                   VALUES (?,N'In',?,?,N'Receipts',?,?,?,?)""",
                (cash_box_ref, amount, balance, receipt_id, shamsi_date, f"دریافت قسط شماره {seq}", user_id)
            )
        else:
            bank_account_ref = int(bank_account_id)
            cursor.execute("SELECT CurrentBalance FROM BankAccounts WHERE ID = ?", (bank_account_ref,))
            balance = float(cursor.fetchone()[0]) + amount
            cursor.execute("UPDATE BankAccounts SET CurrentBalance = ? WHERE ID = ?", (balance, bank_account_ref))
            cursor.execute(
                """INSERT INTO BankTransactions
                   (BankAccountRef, TransactionType, Amount, BalanceAfter, RefTable, RefID, ShamsiDate, Description, UserRef)
                   VALUES (?,N'Deposit',?,?,N'Receipts',?,?,?,?)""",
                (bank_account_ref, amount, balance, receipt_id, shamsi_date, f"دریافت قسط شماره {seq}", user_id)
            )

        cursor.execute(
            """INSERT INTO ReceiptLines (ReceiptRef, MethodType, CashBoxRef, BankAccountRef, Amount)
               VALUES (?,?,?,?,?)""",
            (receipt_id, method, cash_box_ref, bank_account_ref, amount)
        )
        cursor.execute(
            "INSERT INTO ReceiptAllocations (ReceiptRef, SalesInvoiceRef, Amount) VALUES (?,?,?)",
            (receipt_id, invoice_id, amount)
        )
        cursor.execute(
            "UPDATE SalesInvoices SET PaidAmount = PaidAmount + ? WHERE ID = ?", (amount, invoice_id)
        )
        cursor.execute(
            "UPDATE InstallmentItems SET Status = N'Paid', PaidShamsiDate = ?, ReceiptRef = ? WHERE ID = ?",
            (shamsi_date, receipt_id, item_id)
        )

        conn.commit()
        create_audit_entry(user_id, "Create", "Payments", payment_id, f"Payment {payment_number}")
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        db.close()
