# -*- coding: utf-8 -*-
"""
Phase 15.1 — Accounting Core Foundation (Chart of Accounts + Double-Entry Journal Entries)

این ماژول فقط «موتور» حسابداری دوطرفه است: دفتر حساب‌ها (Chart of Accounts)
و ثبت سند حسابداری موازنه‌شده (Journal Entry: چند ردیف بدهکار/بستانکار که
جمع بدهکارها با جمع بستانکارها برابر است).

عمداً به هیچ‌کدام از سرویس‌های موجود (financial_service, sales_service,
inventory_service, ...) وصل نشده و هیچ رفتار فعلی آن‌ها را تغییر نمی‌دهد.
اتصال واقعی هر تراکنش تجاری (فروش، خرید، دریافت، پرداخت، ...) به این
Ledger، به‌صورت عمدی به زیرفازهای بعدی (15.2 به بعد) واگذار شده تا هر
اتصال جداگانه قابل تست، Commit و Rollback باشد — نه یک تغییر بزرگ یک‌جا.
"""

import logging
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import Database
from services.audit_service import create_audit_entry

logger = logging.getLogger(__name__)

VALID_ACCOUNT_TYPES = {"Asset", "Liability", "Equity", "Revenue", "Expense"}
VALID_NORMAL_BALANCES = {"Debit", "Credit"}

# اختلاف‌های بسیار کوچک ناشی از گرد شدن اعشار در محاسبات پولی را نادیده می‌گیرد
BALANCE_TOLERANCE = 0.01


class AccountingError(Exception):
    """خطای قابل‌فهم برای نمایش به کاربر (نه خطای فنی دیتابیس)"""
    pass


# =========================================================
# دفتر حساب‌ها (Chart of Accounts)
# =========================================================

def get_chart_of_accounts(active_only: bool = True):
    db = Database()
    q = "SELECT ID, Code, Name, AccountType, NormalBalance, ParentRef, IsActive FROM ChartOfAccounts"
    if active_only:
        q += " WHERE IsActive = 1"
    q += " ORDER BY Code"
    rows = db.fetch_all(q)
    db.close()
    return rows


def get_account_by_code(code: str):
    db = Database()
    row = db.fetch_one(
        "SELECT ID, Code, Name, AccountType, NormalBalance, ParentRef, IsActive "
        "FROM ChartOfAccounts WHERE Code = ?",
        (code,)
    )
    db.close()
    return row


def create_account(code: str, name: str, account_type: str, normal_balance: str,
                    parent_id: int = None):
    """
    یک حساب جدید به دفتر حساب‌ها اضافه می‌کند.
    Chart of Accounts در این Phase حداقلی و Seed شده است؛ فازهای بعد که هر
    ماژول تجاری را به Ledger وصل می‌کنند، معمولاً به حساب‌های بیشتری نیاز
    خواهند داشت — این تابع همان مسیر رسمی برای اضافه‌کردن آن‌هاست.
    """
    code = (code or "").strip()
    name = (name or "").strip()
    if not code:
        raise AccountingError("کد حساب نمی‌تواند خالی باشد.")
    if not name:
        raise AccountingError("نام حساب نمی‌تواند خالی باشد.")
    if account_type not in VALID_ACCOUNT_TYPES:
        raise AccountingError(
            f"نوع حساب نامعتبر است: {account_type} "
            f"(باید یکی از {sorted(VALID_ACCOUNT_TYPES)} باشد)"
        )
    if normal_balance not in VALID_NORMAL_BALANCES:
        raise AccountingError(
            f"ماهیت حساب نامعتبر است: {normal_balance} "
            f"(باید یکی از {sorted(VALID_NORMAL_BALANCES)} باشد)"
        )

    if get_account_by_code(code) is not None:
        raise AccountingError(f"حساب با کد «{code}» از قبل وجود دارد.")

    db = Database()
    account_id = db.execute(
        """INSERT INTO ChartOfAccounts (Code, Name, AccountType, NormalBalance, ParentRef)
           VALUES (?, ?, ?, ?, ?)""",
        (code, name, account_type, normal_balance, parent_id)
    )
    db.close()
    return account_id


# =========================================================
# ثبت سند حسابداری (Journal Entry) — دوطرفه، موازنه‌شده
# =========================================================

def _validate_journal_lines(lines):
    """
    اعتبارسنجی خالص Python بدون نیاز به دیتابیس (برای تست‌پذیری مستقل).
    lines: لیستی از دیکشنری‌ها با کلیدهای account_code (یا account_id)، debit، credit.
    خطا در صورت نامعتبر بودن؛ در غیر این صورت هیچ‌چیز برنمی‌گرداند.
    """
    if not lines or len(lines) < 2:
        raise AccountingError("سند حسابداری باید حداقل دو ردیف (یک بدهکار و یک بستانکار) داشته باشد.")

    total_debit = 0.0
    total_credit = 0.0

    for i, line in enumerate(lines, start=1):
        if not line.get("account_code") and not line.get("account_id"):
            raise AccountingError(f"ردیف {i}: باید account_code یا account_id مشخص شود.")

        debit = float(line.get("debit") or 0)
        credit = float(line.get("credit") or 0)

        if debit < 0 or credit < 0:
            raise AccountingError(f"ردیف {i}: مبلغ بدهکار/بستانکار نمی‌تواند منفی باشد.")
        if debit > 0 and credit > 0:
            raise AccountingError(f"ردیف {i}: یک ردیف نمی‌تواند هم‌زمان بدهکار و بستانکار داشته باشد.")
        if debit == 0 and credit == 0:
            raise AccountingError(f"ردیف {i}: باید مبلغ بدهکار یا بستانکار غیر صفر داشته باشد.")

        total_debit += debit
        total_credit += credit

    if abs(total_debit - total_credit) > BALANCE_TOLERANCE:
        raise AccountingError(
            f"سند حسابداری موازنه ندارد: جمع بدهکار {total_debit:,.2f} "
            f"با جمع بستانکار {total_credit:,.2f} برابر نیست."
        )

    return total_debit


def post_journal_entry(shamsi_date: str, description: str, lines: list, user_id: int,
                        source_table: str = None, source_id: int = None,
                        correlation_id: str = None):
    """
    یک سند حسابداری موازنه‌شده ثبت می‌کند (سربرگ + همه ردیف‌ها به‌صورت اتمیک:
    یا کامل ثبت می‌شود یا هیچ‌چیز).

    lines: لیستی از دیکشنری با کلیدهای:
        account_code (یا account_id), debit (اختیاری), credit (اختیاری),
        description (اختیاری، برای هر ردیف)

    source_table/source_id: ارجاع اختیاری به سند مبدأ تجاری (مثلاً
    ("SalesInvoices", 123)) — برای فازهای بعد که این را به تراکنش‌های
    واقعی وصل می‌کنند. اختیاری است چون این Phase هنوز چیزی را وصل نمی‌کند.

    برمی‌گرداند: (journal_entry_id, entry_number)
    """
    _validate_journal_lines(lines)

    db = Database()
    conn = db.connect()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT ISNULL(MAX(EntryNumber), 0) + 1 AS NextNum FROM JournalEntries")
        entry_number = int(cursor.fetchone()[0])

        cursor.execute(
            """INSERT INTO JournalEntries
               (EntryNumber, ShamsiDate, Description, SourceTable, SourceID, CorrelationID, UserRef)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (entry_number, shamsi_date, description or "", source_table, source_id,
             correlation_id, user_id)
        )
        cursor.execute("SELECT @@IDENTITY AS id")
        entry_id = int(cursor.fetchone()[0])

        for line in lines:
            account_code = line.get("account_code")
            account_id = line.get("account_id")

            if account_id is None:
                cursor.execute("SELECT ID, IsActive FROM ChartOfAccounts WHERE Code = ?", (account_code,))
                row = cursor.fetchone()
                if not row:
                    raise AccountingError(f"حساب با کد «{account_code}» یافت نشد.")
                account_id, is_active = int(row[0]), row[1]
            else:
                cursor.execute("SELECT ID, IsActive FROM ChartOfAccounts WHERE ID = ?", (account_id,))
                row = cursor.fetchone()
                if not row:
                    raise AccountingError(f"حساب با شناسه «{account_id}» یافت نشد.")
                is_active = row[1]

            if not is_active:
                raise AccountingError(f"حساب انتخاب‌شده غیرفعال است (Code/ID: {account_code or account_id}).")

            cursor.execute(
                """INSERT INTO JournalEntryLines (JournalEntryRef, AccountRef, Debit, Credit, Description)
                   VALUES (?, ?, ?, ?, ?)""",
                (entry_id, account_id, float(line.get("debit") or 0),
                 float(line.get("credit") or 0), line.get("description") or "")
            )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        db.close()

    create_audit_entry(user_id, "Create", "JournalEntries", entry_id,
                        f"Journal entry {entry_number}: {description or ''}")

    return entry_id, entry_number


def get_journal_entries(limit: int = 200):
    db = Database()
    rows = db.fetch_all(
        """SELECT TOP {} ID, EntryNumber, ShamsiDate, Description, SourceTable, SourceID,
                  CorrelationID, UserRef, CreatedAt
           FROM JournalEntries
           WHERE IsDeleted = 0
           ORDER BY ID DESC""".format(int(limit))
    )
    db.close()
    return rows


def get_journal_entry_lines(journal_entry_id: int):
    db = Database()
    rows = db.fetch_all(
        """SELECT jel.ID, jel.AccountRef, coa.Code AS AccountCode, coa.Name AS AccountName,
                  jel.Debit, jel.Credit, jel.Description
           FROM JournalEntryLines jel
           JOIN ChartOfAccounts coa ON coa.ID = jel.AccountRef
           WHERE jel.JournalEntryRef = ?
           ORDER BY jel.ID""",
        (journal_entry_id,)
    )
    db.close()
    return rows
