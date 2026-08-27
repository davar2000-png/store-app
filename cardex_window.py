# -*- coding: utf-8 -*-
"""نمایش کاردکس (تاریخچه کامل ورود/خروج) یک کالا"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QPushButton, QHeaderView
)
from PyQt6.QtCore import Qt
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.inventory_service import get_product_cardex

MOVEMENT_LABELS = {
    "Buy": "خرید",
    "Sell": "فروش",
    "BuyReturn": "برگشت از خرید",
    "SellReturn": "برگشت از فروش",
    "Initial": "موجودی اولیه",
    "Adjustment": "اصلاح موجودی",
}


class CardexWindow(QWidget):
    def __init__(self, product_id, product_name):
        super().__init__()
        self.product_id = product_id
        self.setWindowTitle(f"کاردکس کالا: {product_name}")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(800, 500)
        self._build_ui(product_name)
        self.load_data()

    def _build_ui(self, product_name):
        layout = QVBoxLayout()

        title = QLabel(f"📋 کاردکس کالا: {product_name}")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["تاریخ", "نوع حرکت", "ورود", "خروج", "قیمت واحد", "موجودی بعد از حرکت", "توضیحات"]
        )
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        close_btn = QPushButton("بستن")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        self.setLayout(layout)

    def load_data(self):
        rows = get_product_cardex(self.product_id)
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(r["ShamsiDate"] or ""))
            self.table.setItem(i, 1, QTableWidgetItem(MOVEMENT_LABELS.get(r["MovementType"], r["MovementType"])))
            self.table.setItem(i, 2, QTableWidgetItem(f"{r['InQuantity']:,.0f}" if r["InQuantity"] else ""))
            self.table.setItem(i, 3, QTableWidgetItem(f"{r['OutQuantity']:,.0f}" if r["OutQuantity"] else ""))
            self.table.setItem(i, 4, QTableWidgetItem(f"{r['UnitPrice']:,.0f}"))
            self.table.setItem(i, 5, QTableWidgetItem(f"{r['BalanceQuantity']:,.0f}"))
            self.table.setItem(i, 6, QTableWidgetItem(r["Description"] or ""))
