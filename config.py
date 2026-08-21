# -*- coding: utf-8 -*-
"""
تنظیمات اتصال به دیتابیس.
اگر نام سرور یا دیتابیس شما فرق دارد، همینجا اصلاح کنید.
"""

# نام سرور SQL (همان چیزی که در SSMS برای Connect استفاده کردید)
SQL_SERVER = r".\SQLEXPRESS"

# نام دیتابیس جدید (همان که schema.sql می‌سازد)
SQL_DATABASE = "StoreAppDB"

# Windows Authentication (نیازی به رمز عبور نیست) - پیش‌فرض همینه
USE_WINDOWS_AUTH = True

# اگر بجای Windows Authentication از یوزر/پسورد SQL استفاده می‌کنید:
SQL_USERNAME = ""
SQL_PASSWORD = ""

# درایور ODBC نصب‌شده روی ویندوز شما (اکثر سیستم‌ها این را دارند)
ODBC_DRIVER = "{ODBC Driver 17 for SQL Server}"


def get_connection_string(database: str = None) -> str:
    """ساخت رشته اتصال به دیتابیس بر اساس تنظیمات بالا."""
    db = database or SQL_DATABASE
    if USE_WINDOWS_AUTH:
        return (
            f"DRIVER={ODBC_DRIVER};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={db};"
            f"Trusted_Connection=yes;"
            f"TrustServerCertificate=yes;"
        )
    else:
        return (
            f"DRIVER={ODBC_DRIVER};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={db};"
            f"UID={SQL_USERNAME};"
            f"PWD={SQL_PASSWORD};"
            f"TrustServerCertificate=yes;"
        )
