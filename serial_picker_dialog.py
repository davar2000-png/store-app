# -*- coding: utf-8 -*-
"""دیالوگ انتخاب سریال/IMEی‌های موجود در انبار برای فروش یک کالای سریالی"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.sales_service import get_available_serials


class SerialPickerDialog(QDialog):
    """با exec() اجرا شود؛ بعد از تایید، self.selected_serial_ids و
    self.selected_serial_numbers پر می‌شوند (دقیقاً به تعداد quantity)"""

    def __init__(self, product_id: int, product_name: str, quantity: int):
        super().__init__()
        self.product_id = product_id
        self.quantity = quantity
        self.selected_serial_ids = []
        self.selected_serial_numbers = []
        self.setWindowTitle(f"انتخاب سریال/IMEI برای «{product_name}»")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(450, 420)
        self._build_ui()
        self.load_data()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel(
            f"باید دقیقاً {self.quantity} عدد از سریال/IMEی‌های موجود در انبار انتخاب کنید:"
        ))

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["سریال/IMEI", ""])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

        self.count_label = QLabel("")
        layout.addWidget(self.count_label)
        self.table.itemSelectionChanged.connect(self.update_count)

        btn_row = QHBoxLayout()
        ok_btn = QPushButton("تایید")
        ok_btn.clicked.connect(self.confirm)
        cancel_btn = QPushButton("انصراف")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        self.setLayout(layout)

    def load_data(self):
        self.rows = get_available_serials(self.product_id)
        self.table.setRowCount(len(self.rows))
        for i, r in enumerate(self.rows):
            self.table.setItem(i, 0, QTableWidgetItem(r["SerialNumber"] or ""))
            self.table.setItem(i, 1, QTableWidgetItem(""))
        self.update_count()

    def update_count(self):
        n = len(set(idx.row() for idx in self.table.selectedIndexes()))
        self.count_label.setText(f"انتخاب‌شده: {n} از {self.quantity} مورد لازم")

    def confirm(self):
        selected_rows = sorted(set(idx.row() for idx in self.table.selectedIndexes()))
        if len(selected_rows) != self.quantity:
            QMessageBox.warning(
                self, "خطا",
                f"باید دقیقاً {self.quantity} سریال انتخاب کنید (الان {len(selected_rows)} مورد انتخاب شده)."
            )
            return
        self.selected_serial_ids = [self.rows[r]["ID"] for r in selected_rows]
        self.selected_serial_numbers = [self.rows[r]["SerialNumber"] for r in selected_rows]
        self.accept()
