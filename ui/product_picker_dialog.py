# -*- coding: utf-8 -*-
"""دیالوگ جستجو و انتخاب کالا - برای استفاده در فاکتور خرید و فروش"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.inventory_service import search_products


class ProductPickerDialog(QDialog):
    """با exec() اجرا شود؛ بعد از تایید، self.selected_product پر می‌شود"""

    def __init__(self):
        super().__init__()
        self.selected_product = None
        self.setWindowTitle("انتخاب کالا")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(650, 420)
        self._build_ui()
        self.load_data()

    def _build_ui(self):
        layout = QVBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("جستجو بر اساس نام، کد یا برند...")
        self.search_input.textChanged.connect(self.load_data)
        layout.addWidget(self.search_input)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["نام کالا", "کد", "برند/مدل", "موجودی فعلی", "سریالی؟"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.doubleClicked.connect(self.confirm_selection)
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        select_btn = QPushButton("انتخاب")
        select_btn.clicked.connect(self.confirm_selection)
        cancel_btn = QPushButton("انصراف")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(select_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        self.setLayout(layout)

    def load_data(self):
        self.rows = search_products(self.search_input.text())
        self.table.setRowCount(len(self.rows))
        for i, r in enumerate(self.rows):
            self.table.setItem(i, 0, QTableWidgetItem(r["Name"] or ""))
            self.table.setItem(i, 1, QTableWidgetItem(r["Code"] or ""))
            brand_model = " / ".join(filter(None, [r.get("Brand"), r.get("Model")]))
            self.table.setItem(i, 2, QTableWidgetItem(brand_model))
            self.table.setItem(i, 3, QTableWidgetItem(f"{float(r['CurrentStock'] or 0):,.0f}"))
            self.table.setItem(i, 4, QTableWidgetItem("بله" if r["HasSerial"] else "خیر"))

    def confirm_selection(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "یک کالا را از لیست انتخاب کنید.")
            return
        self.selected_product = self.rows[row]
        self.accept()
