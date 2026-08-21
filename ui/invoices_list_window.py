# -*- coding: utf-8 -*-
"""لیست یکپارچه فاکتورها: خرید + فروش + برگشت از خرید در یک صفحه،
با جستجوی مشترک (شماره فاکتور یا نام طرف حساب) و فیلتر بر اساس نوع فاکتور.
ثبت فاکتور جدید از هر سه نوع هم از همین صفحه در دسترس است (با استفاده از
فرم‌های همان ماژول‌های قبلی، بدون تکرار منطق)."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QComboBox, QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.invoices_service import get_all_invoices, INVOICE_TYPE_LABELS
from ui.purchase_window import NewPurchaseInvoiceDialog, ViewInvoiceItemsDialog
from ui.sales_window import NewSalesInvoiceDialog, ViewSalesInvoiceItemsDialog
from ui.purchase_return_window import (
    SelectPurchaseInvoiceDialog, NewPurchaseReturnDialog, ViewReturnInvoiceItemsDialog
)

FILTER_OPTIONS = [
    ("همه فاکتورها", "All"),
    ("فاکتور خرید", "Purchase"),
    ("فاکتور فروش", "Sales"),
    ("برگشت از خرید", "PurchaseReturn"),
]


class AllInvoicesWindow(QWidget):
    """پنجره «لیست فاکتورها»: یک‌جا لیست خرید/فروش/برگشت از خرید با جستجو و فیلتر نوع"""

    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.rows = []
        self.setWindowTitle("لیست فاکتورها")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(1000, 560)
        self._build_ui()
        self.load_data()

    def _build_ui(self):
        layout = QVBoxLayout()

        top_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("جستجو بر اساس شماره فاکتور یا نام طرف حساب...")
        self.search_input.textChanged.connect(self.load_data)
        top_row.addWidget(self.search_input)

        self.type_combo = QComboBox()
        for label, value in FILTER_OPTIONS:
            self.type_combo.addItem(label, value)
        self.type_combo.currentIndexChanged.connect(self.load_data)
        top_row.addWidget(self.type_combo)

        layout.addLayout(top_row)

        add_row = QHBoxLayout()
        add_purchase_btn = QPushButton("➕ فاکتور خرید جدید")
        add_purchase_btn.clicked.connect(self.add_purchase_invoice)
        add_sales_btn = QPushButton("➕ فاکتور فروش جدید")
        add_sales_btn.clicked.connect(self.add_sales_invoice)
        add_return_btn = QPushButton("➕ فاکتور برگشت خرید جدید")
        add_return_btn.clicked.connect(self.add_purchase_return_invoice)
        add_row.addWidget(add_purchase_btn)
        add_row.addWidget(add_sales_btn)
        add_row.addWidget(add_return_btn)
        add_row.addStretch()
        layout.addLayout(add_row)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["نوع فاکتور", "شماره فاکتور", "تاریخ", "طرف حساب", "مبلغ", "توضیحات", ""]
        )
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        self.setLayout(layout)

    def load_data(self):
        invoice_type = self.type_combo.currentData() or "All"
        self.rows = get_all_invoices(self.search_input.text(), invoice_type)
        self.table.setRowCount(len(self.rows))
        for i, r in enumerate(self.rows):
            type_label = INVOICE_TYPE_LABELS.get(r["InvoiceType"], r["InvoiceType"])
            self.table.setItem(i, 0, QTableWidgetItem(type_label))
            self.table.setItem(i, 1, QTableWidgetItem(str(r["InvoiceNumber"])))
            self.table.setItem(i, 2, QTableWidgetItem(r["ShamsiDate"] or ""))
            self.table.setItem(i, 3, QTableWidgetItem(r["PersonName"] or ""))
            self.table.setItem(i, 4, QTableWidgetItem(f"{r['PayableAmount']:,.0f}"))
            self.table.setItem(i, 5, QTableWidgetItem(r["Description"] or ""))

            view_btn = QPushButton("مشاهده اقلام")
            view_btn.clicked.connect(
                lambda checked, inv_type=r["InvoiceType"], inv_id=r["ID"], num=r["InvoiceNumber"]:
                    self.view_items(inv_type, inv_id, num)
            )
            self.table.setCellWidget(i, 6, view_btn)

    def view_items(self, invoice_type, invoice_id, invoice_number):
        if invoice_type == "Purchase":
            dlg = ViewInvoiceItemsDialog(invoice_id, invoice_number)
        elif invoice_type == "Sales":
            dlg = ViewSalesInvoiceItemsDialog(invoice_id, invoice_number)
        elif invoice_type == "PurchaseReturn":
            dlg = ViewReturnInvoiceItemsDialog(invoice_id, invoice_number)
        else:
            QMessageBox.warning(self, "خطا", "نوع فاکتور نامشخص است.")
            return
        dlg.exec()

    def add_purchase_invoice(self):
        dlg = NewPurchaseInvoiceDialog(self.current_user)
        if dlg.exec():
            self.load_data()

    def add_sales_invoice(self):
        dlg = NewSalesInvoiceDialog(self.current_user)
        if dlg.exec():
            self.load_data()

    def add_purchase_return_invoice(self):
        picker = SelectPurchaseInvoiceDialog()
        if not picker.exec():
            return
        dlg = NewPurchaseReturnDialog(
            self.current_user, picker.selected_invoice_id, picker.selected_invoice_number
        )
        if dlg.exec():
            self.load_data()
