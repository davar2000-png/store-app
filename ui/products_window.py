# -*- coding: utf-8 -*-
"""مدیریت کالاها: نمایش لیست، افزودن، ویرایش، موجودی و هشدار نقطه سفارش"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QDialog, QFormLayout, QCheckBox,
    QMessageBox, QHeaderView, QDoubleSpinBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import Database


class ProductDialog(QDialog):
    def __init__(self, product=None):
        super().__init__()
        self.product = product
        self.setWindowTitle("ویرایش کالا" if product else "افزودن کالای جدید")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedWidth(420)
        self._build_ui()

    def _build_ui(self):
        layout = QFormLayout()

        self.name_input = QLineEdit()
        self.code_input = QLineEdit()
        self.brand_input = QLineEdit()
        self.model_input = QLineEdit()
        self.purchase_price = QDoubleSpinBox()
        self.purchase_price.setMaximum(999999999)
        self.purchase_price.setGroupSeparatorShown(True)
        self.sale_price = QDoubleSpinBox()
        self.sale_price.setMaximum(999999999)
        self.sale_price.setGroupSeparatorShown(True)
        self.order_point = QDoubleSpinBox()
        self.order_point.setMaximum(999999)
        self.order_point.setGroupSeparatorShown(True)
        self.has_serial = QCheckBox("کالای سریالی است (موبایل/لپ‌تاپ/کنسول)")

        if self.product:
            self.name_input.setText(self.product.get("Name") or "")
            self.code_input.setText(self.product.get("Code") or "")
            self.brand_input.setText(self.product.get("Brand") or "")
            self.model_input.setText(self.product.get("Model") or "")
            self.purchase_price.setValue(float(self.product.get("PurchasePrice") or 0))
            self.sale_price.setValue(float(self.product.get("SalePrice") or 0))
            self.order_point.setValue(float(self.product.get("OrderPoint") or 0))
            self.has_serial.setChecked(bool(self.product.get("HasSerial")))

        layout.addRow("نام کالا:", self.name_input)
        layout.addRow("کد کالا:", self.code_input)
        layout.addRow("برند:", self.brand_input)
        layout.addRow("مدل:", self.model_input)
        layout.addRow("قیمت خرید:", self.purchase_price)
        layout.addRow("قیمت فروش:", self.sale_price)
        layout.addRow("نقطه سفارش (حداقل موجودی هشدار):", self.order_point)
        layout.addRow(self.has_serial)

        if self.product:
            note = QLabel(
                f"موجودی فعلی: {float(self.product.get('CurrentStock') or 0):,.0f}\n"
                "(موجودی فقط از طریق فاکتور خرید/فروش تغییر می‌کند)"
            )
            note.setStyleSheet("color: gray;")
            layout.addRow(note)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("ذخیره")
        save_btn.clicked.connect(self.save)
        cancel_btn = QPushButton("انصراف")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        layout.addRow(btn_row)

        self.setLayout(layout)

    def save(self):
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "خطا", "نام کالا نمی‌تواند خالی باشد.")
            return

        db = Database()
        try:
            if self.product:
                db.execute(
                    """UPDATE Products SET Name=?, Code=?, Brand=?, Model=?,
                       PurchasePrice=?, SalePrice=?, OrderPoint=?, HasSerial=?, UpdatedAt=GETDATE()
                       WHERE ID=?""",
                    (self.name_input.text().strip(), self.code_input.text().strip(),
                     self.brand_input.text().strip(), self.model_input.text().strip(),
                     self.purchase_price.value(), self.sale_price.value(),
                     self.order_point.value(), int(self.has_serial.isChecked()), self.product["ID"])
                )
            else:
                db.execute(
                    """INSERT INTO Products
                       (Name, Code, Brand, Model, PurchasePrice, SalePrice, OrderPoint, HasSerial)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (self.name_input.text().strip(), self.code_input.text().strip(),
                     self.brand_input.text().strip(), self.model_input.text().strip(),
                     self.purchase_price.value(), self.sale_price.value(),
                     self.order_point.value(), int(self.has_serial.isChecked()))
                )
            db.close()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"ذخیره‌سازی ناموفق بود:\n{e}")


class ProductsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("مدیریت کالاها")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(1000, 550)
        self._build_ui()
        self.load_data()

    def _build_ui(self):
        layout = QVBoxLayout()

        top_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("جستجو بر اساس نام، کد یا برند...")
        self.search_input.textChanged.connect(self.load_data)
        add_btn = QPushButton("➕ افزودن کالا")
        add_btn.clicked.connect(self.add_product)
        top_row.addWidget(self.search_input)
        top_row.addWidget(add_btn)
        layout.addLayout(top_row)

        self.warning_label = QLabel("")
        self.warning_label.setStyleSheet("color: #b30000; font-weight: bold;")
        layout.addWidget(self.warning_label)

        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(
            ["نام کالا", "کد", "برند", "مدل", "موجودی", "نقطه سفارش",
             "قیمت خرید", "قیمت فروش", ""]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        self.setLayout(layout)

    def load_data(self):
        db = Database()
        search = f"%{self.search_input.text().strip()}%"
        rows = db.fetch_all(
            """SELECT * FROM Products
               WHERE IsDeleted = 0 AND
                     (Name LIKE ? OR Code LIKE ? OR Brand LIKE ?)
               ORDER BY Name""",
            (search, search, search)
        )
        db.close()

        low_stock_count = 0
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            current_stock = float(r.get("CurrentStock") or 0)
            order_point = float(r.get("OrderPoint") or 0)
            is_low = order_point > 0 and current_stock <= order_point
            if is_low:
                low_stock_count += 1

            self.table.setItem(i, 0, QTableWidgetItem(r["Name"] or ""))
            self.table.setItem(i, 1, QTableWidgetItem(r["Code"] or ""))
            self.table.setItem(i, 2, QTableWidgetItem(r["Brand"] or ""))
            self.table.setItem(i, 3, QTableWidgetItem(r["Model"] or ""))
            self.table.setItem(i, 4, QTableWidgetItem(f"{current_stock:,.0f}"))
            self.table.setItem(i, 5, QTableWidgetItem(f"{order_point:,.0f}"))
            self.table.setItem(i, 6, QTableWidgetItem(f"{r['PurchasePrice']:,.0f}"))
            self.table.setItem(i, 7, QTableWidgetItem(f"{r['SalePrice']:,.0f}"))

            if is_low:
                for col in range(8):
                    item = self.table.item(i, col)
                    if item:
                        item.setBackground(QColor("#ffd6d6"))

            btn_row = QWidget()
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(0, 0, 0, 0)
            edit_btn = QPushButton("ویرایش")
            edit_btn.clicked.connect(lambda checked, row=r: self.edit_product(row))
            cardex_btn = QPushButton("کاردکس")
            cardex_btn.clicked.connect(lambda checked, row=r: self.open_cardex(row))
            btn_layout.addWidget(edit_btn)
            btn_layout.addWidget(cardex_btn)
            btn_row.setLayout(btn_layout)
            self.table.setCellWidget(i, 8, btn_row)

        if low_stock_count > 0:
            self.warning_label.setText(f"⚠️ {low_stock_count} کالا به نقطه سفارش رسیده یا کمتر از آن است.")
        else:
            self.warning_label.setText("")

    def add_product(self):
        dlg = ProductDialog()
        if dlg.exec():
            self.load_data()

    def edit_product(self, product):
        dlg = ProductDialog(product)
        if dlg.exec():
            self.load_data()

    def open_cardex(self, product):
        from ui.cardex_window import CardexWindow
        self.cardex_win = CardexWindow(product["ID"], product["Name"])
        self.cardex_win.show()
