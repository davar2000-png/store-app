# -*- coding: utf-8 -*-
"""پنجره ورود به سیستم"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import Database
from utils.security import verify_password


class LoginWindow(QWidget):
    def __init__(self, on_success):
        super().__init__()
        self.on_success = on_success
        self.setWindowTitle("ورود به سیستم - نرم‌افزار حسابداری فروشگاه")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedSize(380, 260)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(14)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("ورود به نرم‌افزار حسابداری")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("نام کاربری")
        layout.addWidget(self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("رمز عبور")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)

        self.login_btn = QPushButton("ورود")
        self.login_btn.setFixedHeight(38)
        self.login_btn.clicked.connect(self.try_login)
        layout.addWidget(self.login_btn)

        self.password_input.returnPressed.connect(self.try_login)

        self.setLayout(layout)

    def try_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            QMessageBox.warning(self, "خطا", "لطفاً نام کاربری و رمز عبور را وارد کنید.")
            return

        try:
            db = Database()
            user = db.fetch_one(
                "SELECT * FROM Users WHERE Username = ? AND IsActive = 1", (username,)
            )
            db.close()
        except Exception as e:
            QMessageBox.critical(self, "خطای اتصال",
                                  f"اتصال به دیتابیس برقرار نشد:\n{e}")
            return

        if not user:
            QMessageBox.warning(self, "خطا", "نام کاربری یافت نشد یا غیرفعال است.")
            return

        if not verify_password(password, user["PasswordHash"], user["PasswordSalt"]):
            QMessageBox.warning(self, "خطا", "رمز عبور اشتباه است.")
            return

        self.on_success(user)
        self.close()
