# -*- coding: utf-8 -*-
"""
پشتیبان‌گیری و بازیابی کامل دیتابیس نرم‌افزار (StoreAppDB)
از دستورات بومی SQL Server (BACKUP DATABASE / RESTORE DATABASE) استفاده می‌شود.

مرحله ۹: تکمیل بازیابی برای پوشش «کلیه اطلاعات» در همه شرایط واقعی، از جمله:
  - بازیابی روی همان کامپیوتر (مسیر فایل‌های دیتابیس همان قبلی است) — قبلاً کار می‌کرد.
  - بازیابی روی یک کامپیوتر/نصب SQL Server تازه (بعد از خرابی سیستم، ویندوز جدید،
    یا کامپیوتر جدید) که در آن مسیر فیزیکی فایل‌های دیتابیس دیگر وجود ندارد —
    قبلاً با خطا مواجه می‌شد؛ حالا با WITH MOVE به‌صورت خودکار حل می‌شود.
  - بازیابی وقتی دیتابیس StoreAppDB اصلاً هنوز ساخته نشده (نصب کاملاً تازه).
  - پیام خطای فارسی و قابل‌فهم برای رایج‌ترین مشکل مبتدیان: «Access Denied» چون
    سرویس SQL Server به پوشه‌ی انتخاب‌شده (مثلاً دسکتاپ یا فلش) دسترسی نداشته.
"""

import sys
import os
import pyodbc
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_connection_string, SQL_DATABASE


class BackupError(Exception):
    pass


def _get_master_connection():
    """برای Backup/Restore باید به دیتابیس master وصل شویم، نه StoreAppDB"""
    conn_str = get_connection_string("master")
    return pyodbc.connect(conn_str, autocommit=True)


def _friendly_error(e: Exception) -> str:
    """تبدیل خطای خام SQL Server به یک پیام قابل‌فهم فارسی برای کاربر مبتدی"""
    msg = str(e)
    low = msg.lower()
    if "access is denied" in low or "operating system error 5" in low:
        return (
            "دسترسی به این پوشه برای SQL Server ممنوع است (این پوشه معمولاً باید روی "
            "همین کامپیوتر و در دسترس سرویس SQL Server باشد — نه فلش مموری یا درایو اشتراکی).\n"
            "پیشنهاد: از پوشه‌ی پیشنهادی برنامه استفاده کنید (دکمه‌ی «استفاده از پوشه پیشنهادی»)."
        )
    if "cannot open backup device" in low or "operating system error 3" in low:
        return (
            "مسیر انتخاب‌شده پیدا نشد یا در دسترس نیست. لطفاً پوشه‌ی دیگری (ترجیحاً پوشه‌ی "
            "پیشنهادی برنامه) را انتخاب کنید."
        )
    if "exclusive access" in low or "in use" in low:
        return (
            "دیتابیس در حال حاضر توسط برنامه‌ی دیگری (یا نسخه‌ی دیگری از همین برنامه) در حال "
            "استفاده است. همه‌ی پنجره‌های برنامه را ببندید و فقط از همین پنجره‌ی پشتیبان‌گیری "
            "دوباره تلاش کنید."
        )
    if "not enough space" in low or "disk" in low and "full" in low:
        return "فضای دیسک کافی برای این عملیات وجود ندارد."
    return f"خطا: {msg}"


def _database_exists(cursor, db_name: str) -> bool:
    cursor.execute("SELECT database_id FROM sys.databases WHERE name = ?", (db_name,))
    return cursor.fetchone() is not None


def get_default_data_log_folder() -> str:
    """
    مسیر پیش‌فرض ذخیره‌سازی فایل‌های دیتابیس در این نصب SQL Server را برمی‌گرداند
    (همانی که SQL Server خودش برای دیتابیس‌های جدید استفاده می‌کند).
    این تابع پایه‌ی حل مشکل «بازیابی روی کامپیوتر دیگر» است.
    """
    conn = _get_master_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT CAST(SERVERPROPERTY('InstanceDefaultDataPath') AS NVARCHAR(500))")
    row = cursor.fetchone()
    folder = row[0] if row and row[0] else None
    if not folder:
        # روش جایگزین: مسیر فایل دیتابیس master را پیدا کن
        cursor.execute(
            "SELECT physical_name FROM sys.master_files WHERE database_id = DB_ID('master') "
            "AND type = 0"
        )
        row2 = cursor.fetchone()
        if row2 and row2[0]:
            folder = os.path.dirname(row2[0]) + "\\"
        else:
            folder = "C:\\"
    cursor.close()
    conn.close()
    return folder


def suggest_backup_folder() -> str:
    """
    یک پوشه‌ی مطمئن برای ذخیره فایل بک‌آپ پیشنهاد می‌دهد که خود SQL Server هم به آن
    دسترسی کامل دارد (زیر مسیر پیش‌فرض داده‌های همان SQL Server) و در صورت نبودن، آن
    را با دستور SQL Server می‌سازد (نه با پایتون، چون این پوشه باید برای «سرویس»
    SQL Server هم قابل‌نوشتن باشد، نه فقط برای کاربر ویندوز).
    """
    try:
        base = get_default_data_log_folder().rstrip("\\") 
        folder = base + "\\StoreAppDB_Backups"
        conn = _get_master_connection()
        cursor = conn.cursor()
        cursor.execute("EXEC master.dbo.xp_create_subdir ?", (folder,))
        cursor.close()
        conn.close()
        return folder
    except Exception:
        # اگر به هر دلیلی نشد (مثلاً دسترسی محدود)، حداقل یک پیشنهاد ساده بده
        return "C:\\StoreAppDB_Backups"


def create_backup(file_path: str):
    """
    یک نسخه پشتیبان کامل از StoreAppDB (تمام جداول، یعنی کلیه اطلاعات نرم‌افزار)
    در مسیر مشخص‌شده می‌سازد.
    """
    try:
        conn = _get_master_connection()
        cursor = conn.cursor()
        query = """
            BACKUP DATABASE [{db}]
            TO DISK = ?
            WITH FORMAT, INIT, NAME = 'StoreAppDB-Full-Backup';
        """.format(db=SQL_DATABASE)
        cursor.execute(query, (file_path,))
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        raise BackupError(_friendly_error(e))


def create_pre_restore_backup() -> str:
    folder = suggest_backup_folder()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(folder, f"StoreAppDB_PreRestore_{timestamp}.bak")
    create_backup(file_path)
    return file_path


def restore_backup(file_path: str, progress_cb=None):
    """
    دیتابیس StoreAppDB را از فایل پشتیبان مشخص‌شده به‌طور کامل بازیابی می‌کند —
    شامل تمام اشخاص، کالاها، فاکتورها، چک‌ها، اقساط، صندوق/بانک و تنظیمات.

    این نسخه (مرحله ۹) برخلاف قبل، محدود به «همان کامپیوتر» نیست:
      - اگر StoreAppDB از قبل وجود داشته باشد: قبل از Restore به SINGLE_USER می‌رود.
      - اگر StoreAppDB اصلاً وجود نداشته باشد (نصب تازه): مستقیم Restore انجام می‌شود.
      - فایل‌های فیزیکی دیتابیس همیشه با WITH MOVE به پوشه‌ی پیش‌فرض همین SQL Server
        منتقل می‌شوند، پس فرقی نمی‌کند بک‌آپ روی همین کامپیوتر گرفته شده یا کامپیوتر/
        نصب دیگری از SQL Server — بازیابی در هر دو حالت کار می‌کند.
    """
    def _progress(msg):
        if progress_cb:
            try:
                progress_cb(msg)
            except Exception:
                pass

    try:
        conn = _get_master_connection()
        cursor = conn.cursor()

        _progress("در حال خواندن اطلاعات فایل پشتیبان...")
        cursor.execute("RESTORE FILELISTONLY FROM DISK = ?", (file_path,))
        columns = [c[0] for c in cursor.description]
        file_rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        if not file_rows:
            raise BackupError("فایل پشتیبان معتبر نیست یا خالی است.")

        target_folder = get_default_data_log_folder().rstrip("\\")

        move_clauses = []
        for f in file_rows:
            logical_name = f.get("LogicalName")
            physical_name = f.get("PhysicalName") or ""
            ext = os.path.splitext(physical_name)[1] or (
                ".ldf" if (f.get("Type") == "L") else ".mdf"
            )
            new_physical = f"{target_folder}\\{SQL_DATABASE}_{logical_name}{ext}"
            move_clauses.append(f"MOVE '{logical_name}' TO '{new_physical}'")

        db_exists = _database_exists(cursor, SQL_DATABASE)

        if db_exists:
            _progress("در حال تهیه نسخه پشتیبان اضطراری قبل از بازیابی...")
            create_pre_restore_backup()
            _progress("نسخه پشتیبان اضطراری با موفقیت ذخیره شد.")
            _progress("در حال قطع اتصال سایر کاربران برای بازیابی امن...")
            cursor.execute(f"""
                ALTER DATABASE [{SQL_DATABASE}]
                SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
            """)

        _progress("در حال بازیابی کلیه اطلاعات از فایل پشتیبان (ممکن است چند دقیقه طول بکشد)...")
        move_sql = ", ".join(move_clauses)
        restore_query = f"""
            RESTORE DATABASE [{SQL_DATABASE}]
            FROM DISK = ?
            WITH REPLACE, {move_sql};
        """
        cursor.execute(restore_query, (file_path,))

        _progress("در حال بازگرداندن دیتابیس به حالت عادی (چند کاربره)...")
        cursor.execute(f"ALTER DATABASE [{SQL_DATABASE}] SET MULTI_USER;")

        cursor.close()
        conn.close()
        _progress("بازیابی کامل شد.")
        return True
    except Exception as e:
        # تلاش برای بازگرداندن دیتابیس به حالت چند-کاربره در صورت خطا (اگر وجود داشت)
        try:
            conn2 = _get_master_connection()
            cursor2 = conn2.cursor()
            if _database_exists(cursor2, SQL_DATABASE):
                cursor2.execute(f"ALTER DATABASE [{SQL_DATABASE}] SET MULTI_USER;")
            cursor2.close()
            conn2.close()
        except Exception:
            pass
        raise BackupError(_friendly_error(e))


def verify_backup_file(file_path: str) -> dict:
    """بررسی می‌کند فایل بک‌آپ معتبر است و متعلق به کدام دیتابیس بوده (پیش از Restore)"""
    try:
        conn = _get_master_connection()
        cursor = conn.cursor()
        cursor.execute("RESTORE HEADERONLY FROM DISK = ?", (file_path,))
        columns = [c[0] for c in cursor.description]
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if not row:
            raise BackupError("فایل بک‌آپ معتبر نیست یا خالی است.")
        data = dict(zip(columns, row))
        return {
            "database_name": data.get("DatabaseName"),
            "backup_date": data.get("BackupStartDate"),
        }
    except pyodbc.Error as e:
        raise BackupError(_friendly_error(e))
