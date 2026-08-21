# -*- coding: utf-8 -*-
"""
لایه اتصال به دیتابیس SQL Server.
تمام بخش‌های برنامه از طریق این فایل با دیتابیس صحبت می‌کنند.
"""

import pyodbc
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_connection_string


class Database:
    def __init__(self, database: str = None):
        self.conn_str = get_connection_string(database)
        self.conn = None

    def connect(self):
        if self.conn is None:
            self.conn = pyodbc.connect(self.conn_str, autocommit=False)
        return self.conn

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def execute(self, query: str, params: tuple = ()):
        """اجرای INSERT/UPDATE/DELETE - با commit خودکار"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        last_id = None
        try:
            cursor.execute("SELECT @@IDENTITY AS id")
            row = cursor.fetchone()
            last_id = row.id if row else None
        except Exception:
            pass
        cursor.close()
        return last_id

    def fetch_all(self, query: str, params: tuple = ()):
        """اجرای SELECT و برگرداندن همه ردیف‌ها به صورت لیستی از دیکشنری"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(query, params)
        columns = [col[0] for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        cursor.close()
        return rows

    def fetch_one(self, query: str, params: tuple = ()):
        rows = self.fetch_all(query, params)
        return rows[0] if rows else None


def test_connection():
    """تست سریع اتصال - برای بررسی درست بودن تنظیمات"""
    try:
        db = Database()
        db.connect()
        print("✅ اتصال به دیتابیس با موفقیت برقرار شد.")
        db.close()
        return True
    except Exception as e:
        print("❌ خطا در اتصال به دیتابیس:")
        print(e)
        return False


if __name__ == "__main__":
    test_connection()
