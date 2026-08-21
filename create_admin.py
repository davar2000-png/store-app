# -*- coding: utf-8 -*-
"""
این اسکریپت را فقط یک‌بار، بعد از ساخت دیتابیس (اجرای schema.sql) اجرا کنید
تا اولین کاربر مدیر ساخته شود.
"""

from database.db import Database
from utils.security import hash_password

def create_admin():
    print("=== ساخت کاربر مدیر ===")
    username = input("نام کاربری (مثلاً admin): ").strip()
    full_name = input("نام و نام‌خانوادگی: ").strip()
    password = input("رمز عبور: ").strip()

    hashed, salt = hash_password(password)

    db = Database()
    existing = db.fetch_one("SELECT * FROM Users WHERE Username = ?", (username,))
    if existing:
        print("❌ این نام کاربری قبلاً ثبت شده است.")
        db.close()
        return

    db.execute(
        """INSERT INTO Users (Username, PasswordHash, PasswordSalt, FullName, IsAdmin, IsActive)
           VALUES (?, ?, ?, ?, 1, 1)""",
        (username, hashed, salt, full_name)
    )
    db.close()
    print(f"✅ کاربر مدیر «{full_name}» با نام کاربری «{username}» ساخته شد.")
    print("حالا می‌توانید با همین اطلاعات وارد نرم‌افزار (main.py) شوید.")


if __name__ == "__main__":
    create_admin()
