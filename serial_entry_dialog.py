# -*- coding: utf-8 -*-
"""دیالوگ وارد کردن سریال/IMEI برای هر واحد از یک کالای سریالی (موبایل/لپ‌تاپ/کنسول)"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QLabel, QScrollArea, QWidget, QMessageBox
)
from PyQt6.QtCore import Qt


class SerialEntryDialog(QDialog):
    """با exec() اجرا شود؛ بعد از تایید، self.serials لیستی از رشته‌هاست"""

    def __init__(self, product_name: str, quantity: int):
        super().__init__()
        self.quantity = quantity
        self.serials = []
        self.setWindowTitle(f"وارد کردن سریال/IMEI برای «{product_name}»")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedWidth(420)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"تعداد {self.quantity} عدد — لطفاً سریال/IMEI هر واحد را وارد کنید:"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        inner_layout = QVBoxLayout()

        self.inputs = []
        for i in range(self.quantity):
            row = QHBoxLayout()
            row.addWidget(QLabel(f"واحد {i + 1}:"))
            inp = QLineEdit()
            inp.setPlaceholderText("سریال یا IMEI...")
            row.addWidget(inp)
            self.inputs.append(inp)
            inner_layout.addLayout(row)

        inner.setLayout(inner_layout)
        scroll.setWidget(inner)
        layout.addWidget(scroll)

        btn_row = QHBoxLayout()
        ok_btn = QPushButton("تایید")
        ok_btn.clicked.connect(self.confirm)
        cancel_btn = QPushButton("انصراف")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        self.setLayout(layout)

    def confirm(self):
        values = [inp.text().strip() for inp in self.inputs]
        if any(not v for v in values):
            QMessageBox.warning(self, "خطا", "همه فیلدهای سریال/IMEI باید پر شوند.")
            return
        if len(set(values)) != len(values):
            QMessageBox.warning(self, "خطا", "سریال/IMEI‌های وارد شده نباید تکراری باشند.")
            return
        self.serials = values
        self.accept()
