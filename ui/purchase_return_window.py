# -*- coding: utf-8 -*-
"""مدیریت برگشت از خرید: لیست فاکتورهای برگشت خرید + ثبت فاکتور برگشت جدید
(هر فاکتور برگشت همیشه بر مبنای یک فاکتور خرید مشخص ساخته می‌شود)"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QDialog, QDoubleSpinBox, QMessageBox,
    QHeaderView, QTextEdit, QAbstractItemView
)
from PyQt6.QtCore import Qt
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.persian_date import today_shamsi_str
from services.inventory_service import (
    get_purchase_invoices, get_returnable_items, get_layer_available_serials,
    get_purchase_return_invoices, get_purchase_return_invoice_items,
    create_purchase_return_invoice, InventoryError
)


class LayerSerialPickerDialog(QDialog):
    """انتخاب سریال/IMEی‌هایی که باید برگشت داده شوند (فقط از همان لایه خرید مبنا)"""

    def __init__(self, layer_id, product_name, quantity):
        super().__init__()
        self.quantity = quantity
        self.selected_serial_ids = []
        self.setWindowTitle(f"انتخاب سریال/IMEI برگشتی «{product_name}»")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(420, 420)

        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"باید دقیقاً {quantity} عدد را انتخاب کنید:"))

        self.table = QTableWidget()
        self.table.setColumnCount(1)
        self.table.setHorizontalHeaderLabels(["سریال/IMEI"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
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

        self.rows = get_layer_available_serials(layer_id)
        self.table.setRowCount(len(self.rows))
        for i, r in enumerate(self.rows):
            self.table.setItem(i, 0, QTableWidgetItem(r["SerialNumber"] or ""))
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
        self.accept()


class SelectPurchaseInvoiceDialog(QDialog):
    """انتخاب فاکتور خریدی که فاکتور برگشت بر مبنای آن ساخته می‌شود"""

    def __init__(self):
        super().__init__()
        self.selected_invoice_id = None
        self.selected_invoice_number = None
        self.setWindowTitle("انتخاب فاکتور خرید مبنا")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(620, 420)

        layout = QVBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("جستجو بر اساس شماره فاکتور یا نام فروشنده...")
        self.search_input.textChanged.connect(self.load_data)
        layout.addWidget(self.search_input)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["شماره فاکتور", "تاریخ", "فروشنده", "مبلغ فاکتور"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.doubleClicked.connect(self.confirm)
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        ok_btn = QPushButton("انتخاب")
        ok_btn.clicked.connect(self.confirm)
        cancel_btn = QPushButton("انصراف")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        self.setLayout(layout)
        self.load_data()

    def load_data(self):
        self.rows = get_purchase_invoices(self.search_input.text())
        self.table.setRowCount(len(self.rows))
        for i, r in enumerate(self.rows):
            self.table.setItem(i, 0, QTableWidgetItem(str(r["InvoiceNumber"])))
            self.table.setItem(i, 1, QTableWidgetItem(r["ShamsiDate"] or ""))
            self.table.setItem(i, 2, QTableWidgetItem(r["SupplierName"] or ""))
            self.table.setItem(i, 3, QTableWidgetItem(f"{r['PayableAmount']:,.0f}"))

    def confirm(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "یک فاکتور خرید را انتخاب کنید.")
            return
        self.selected_invoice_id = self.rows[row]["ID"]
        self.selected_invoice_number = self.rows[row]["InvoiceNumber"]
        self.accept()


class NewPurchaseReturnDialog(QDialog):
    """فرم ثبت فاکتور برگشت از خرید، مبتنی بر اقلام یک فاکتور خرید انتخاب‌شده"""

    def __init__(self, current_user, purchase_invoice_id, purchase_invoice_number):
        super().__init__()
        self.current_user = current_user
        self.purchase_invoice_id = purchase_invoice_id
        self.purchase_invoice_number = purchase_invoice_number
        self.rows = []            # خروجی get_returnable_items
        self.return_qty = {}      # index -> تعداد برگشتی وارد شده
        self.chosen_serials = {}  # index -> لیست serial_id انتخاب‌شده

        self.setWindowTitle(f"فاکتور برگشت از خرید — مبنا: فاکتور خرید شماره {purchase_invoice_number}")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(850, 540)
        self._build_ui()
        self.load_items()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"فاکتور خرید مبنا: شماره {self.purchase_invoice_number}"))

        self.date_value = today_shamsi_str()
        layout.addWidget(QLabel(f"تاریخ فاکتور برگشت: {self.date_value}"))

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["کالا", "تعداد خریداری‌شده", "قابل برگشت", "تعداد برگشتی",
             "قیمت واحد", "سریال/IMEI", "جمع"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        self.description_input = QTextEdit()
        self.description_input.setFixedHeight(50)
        self.description_input.setPlaceholderText("توضیحات (اختیاری)...")
        layout.addWidget(self.description_input)

        self.total_label = QLabel("جمع کل برگشتی: 0")
        self.total_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(self.total_label)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("💾 ثبت فاکتور برگشت")
        save_btn.clicked.connect(self.save_invoice)
        cancel_btn = QPushButton("انصراف")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        self.setLayout(layout)

    def load_items(self):
        self.rows = get_returnable_items(self.purchase_invoice_id)
        if not self.rows:
            QMessageBox.warning(
                self, "هشدار",
                "هیچ قلمی برای برگشت از این فاکتور خرید پیدا نشد (یا فاکتور خرید مربوط به مرحله‌های قدیمی‌تر است)."
            )
        self.table.setRowCount(len(self.rows))
        for i, r in enumerate(self.rows):
            self.table.setItem(i, 0, QTableWidgetItem(r["ProductName"]))
            self.table.setItem(i, 1, QTableWidgetItem(f"{r['OriginalQuantity']:g}"))
            self.table.setItem(i, 2, QTableWidgetItem(f"{r['RemainingQuantity']:g}"))

            spin = QDoubleSpinBox()
            spin.setMinimum(0)
            spin.setMaximum(float(r["RemainingQuantity"]))
            spin.setValue(0)
            spin.valueChanged.connect(lambda val, idx=i: self.on_qty_changed(idx, val))
            self.table.setCellWidget(i, 3, spin)

            self.table.setItem(i, 4, QTableWidgetItem(f"{r['UnitPrice']:,.0f}"))

            if r["HasSerial"]:
                serial_btn = QPushButton("انتخاب سریال")
                serial_btn.clicked.connect(lambda checked, idx=i: self.pick_serials(idx))
                self.table.setCellWidget(i, 5, serial_btn)
            else:
                self.table.setItem(i, 5, QTableWidgetItem("—"))

            self.table.setItem(i, 6, QTableWidgetItem("0"))

    def on_qty_changed(self, index, value):
        self.return_qty[index] = value
        if self.rows[index]["HasSerial"]:
            # با تغییر تعداد، سریال‌های قبلاً انتخاب‌شده دیگر معتبر نیستند و باید دوباره انتخاب شوند
            self.chosen_serials.pop(index, None)
        line_total = value * float(self.rows[index]["UnitPrice"])
        self.table.setItem(index, 6, QTableWidgetItem(f"{line_total:,.0f}"))
        self.update_total()

    def pick_serials(self, index):
        qty = int(self.return_qty.get(index, 0))
        if qty <= 0:
            QMessageBox.warning(self, "خطا", "ابتدا تعداد برگشتی این قلم را وارد کنید.")
            return
        row = self.rows[index]
        dlg = LayerSerialPickerDialog(row["LayerID"], row["ProductName"], qty)
        if dlg.exec():
            self.chosen_serials[index] = dlg.selected_serial_ids
            QMessageBox.information(self, "تایید", f"{qty} سریال برای «{row['ProductName']}» انتخاب شد.")

    def update_total(self):
        total = sum(
            self.return_qty.get(i, 0) * float(self.rows[i]["UnitPrice"])
            for i in range(len(self.rows))
        )
        self.total_label.setText(f"جمع کل برگشتی: {total:,.0f}")

    def save_invoice(self):
        items = []
        for i, row in enumerate(self.rows):
            qty = self.return_qty.get(i, 0)
            if qty <= 0:
                continue
            if row["HasSerial"] and len(self.chosen_serials.get(i, [])) != int(qty):
                QMessageBox.warning(
                    self, "خطا",
                    f"برای «{row['ProductName']}» باید دقیقاً {int(qty)} سریال انتخاب کنید."
                )
                return
            items.append({
                "item_id": row["ItemID"],
                "product_id": row["ProductID"],
                "product_name": row["ProductName"],
                "layer_id": row["LayerID"],
                "quantity": qty,
                "unit_price": float(row["UnitPrice"]),
                "has_serial": bool(row["HasSerial"]),
                "serial_ids": self.chosen_serials.get(i, []),
            })

        if not items:
            QMessageBox.warning(self, "خطا", "حداقل تعداد برگشتی یک قلم کالا را وارد کنید.")
            return

        try:
            invoice_id, invoice_number = create_purchase_return_invoice(
                original_invoice_id=self.purchase_invoice_id,
                shamsi_date=self.date_value,
                description=self.description_input.toPlainText().strip(),
                user_id=self.current_user["ID"],
                items=items,
            )
            QMessageBox.information(self, "موفق", f"فاکتور برگشت خرید شماره {invoice_number} با موفقیت ثبت شد.")
            self.accept()
        except InventoryError as e:
            QMessageBox.warning(self, "خطا", str(e))
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"ثبت فاکتور برگشت ناموفق بود:\n{e}")


class ViewReturnInvoiceItemsDialog(QDialog):
    """نمایش فقط‌خواندنی اقلام یک فاکتور برگشت خرید"""

    def __init__(self, invoice_id, invoice_number):
        super().__init__()
        self.setWindowTitle(f"اقلام فاکتور برگشت خرید شماره {invoice_number}")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(600, 400)
        layout = QVBoxLayout()

        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["کالا", "تعداد", "قیمت واحد", "جمع"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        rows = get_purchase_return_invoice_items(invoice_id)
        table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            table.setItem(i, 0, QTableWidgetItem(r["ProductName"]))
            table.setItem(i, 1, QTableWidgetItem(f"{r['Quantity']:g}"))
            table.setItem(i, 2, QTableWidgetItem(f"{r['UnitPrice']:,.0f}"))
            table.setItem(i, 3, QTableWidgetItem(f"{r['TotalPrice']:,.0f}"))

        layout.addWidget(table)
        close_btn = QPushButton("بستن")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        self.setLayout(layout)


class PurchaseReturnInvoicesWindow(QWidget):
    """پنجره اصلی: لیست فاکتورهای برگشت خرید + دکمه ثبت فاکتور برگشت جدید"""

    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.setWindowTitle("برگشت از خرید")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(900, 500)
        self._build_ui()
        self.load_data()

    def _build_ui(self):
        layout = QVBoxLayout()

        top_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("جستجو بر اساس شماره فاکتور یا نام فروشنده...")
        self.search_input.textChanged.connect(self.load_data)
        add_btn = QPushButton("➕ فاکتور برگشت خرید جدید")
        add_btn.clicked.connect(self.add_invoice)
        top_row.addWidget(self.search_input)
        top_row.addWidget(add_btn)
        layout.addLayout(top_row)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["شماره فاکتور برگشت", "تاریخ", "فروشنده", "مبلغ برگشتی", "فاکتور خرید مبنا", ""]
        )
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        self.setLayout(layout)

    def load_data(self):
        rows = get_purchase_return_invoices(self.search_input.text())
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(str(r["InvoiceNumber"])))
            self.table.setItem(i, 1, QTableWidgetItem(r["ShamsiDate"] or ""))
            self.table.setItem(i, 2, QTableWidgetItem(r["SupplierName"] or ""))
            self.table.setItem(i, 3, QTableWidgetItem(f"{r['PayableAmount']:,.0f}"))
            orig = r["OriginalInvoiceNumber"]
            self.table.setItem(i, 4, QTableWidgetItem(str(orig) if orig else "—"))

            view_btn = QPushButton("مشاهده اقلام")
            view_btn.clicked.connect(
                lambda checked, inv_id=r["ID"], num=r["InvoiceNumber"]: self.view_items(inv_id, num)
            )
            self.table.setCellWidget(i, 5, view_btn)

    def add_invoice(self):
        picker = SelectPurchaseInvoiceDialog()
        if not picker.exec():
            return
        dlg = NewPurchaseReturnDialog(
            self.current_user, picker.selected_invoice_id, picker.selected_invoice_number
        )
        if dlg.exec():
            self.load_data()

    def view_items(self, invoice_id, invoice_number):
        dlg = ViewReturnInvoiceItemsDialog(invoice_id, invoice_number)
        dlg.exec()
