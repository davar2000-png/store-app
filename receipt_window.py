# -*- coding: utf-8 -*-
"""مدیریت دریافت وجه از مشتری: لیست اسناد دریافت + ثبت سند دریافت جدید (نقد/بانک/چک + تخصیص به فاکتور)"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QDialog, QFormLayout, QComboBox,
    QDoubleSpinBox, QMessageBox, QHeaderView, QTextEdit, QCheckBox
)
from PyQt6.QtCore import Qt
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.persian_date import today_shamsi_str
from services.financial_service import (
    get_customers, get_unpaid_sales_invoices, get_receipts, get_cash_boxes, get_bank_accounts,
    create_receipt, FinancialError
)


class AddLineDialog(QDialog):
    """افزودن یک ردیف نقد/بانک/چک به سند دریافت"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("افزودن روش دریافت")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(400, 320)
        self.result_line = None

        layout = QVBoxLayout()
        form = QFormLayout()

        self.method_combo = QComboBox()
        self.method_combo.addItem("نقد", "Cash")
        self.method_combo.addItem("بانک (کارت‌خوان/انتقال)", "Bank")
        self.method_combo.addItem("چک", "Cheque")
        self.method_combo.currentIndexChanged.connect(self._update_visibility)

        self.amount_input = QDoubleSpinBox()
        self.amount_input.setMaximum(999999999999)
        self.amount_input.setGroupSeparatorShown(True)

        self.cash_box_combo = QComboBox()
        for c in get_cash_boxes(active_only=True):
            self.cash_box_combo.addItem(c["Name"], c["ID"])

        self.bank_combo = QComboBox()
        for b in get_bank_accounts(active_only=True):
            self.bank_combo.addItem(f"{b['BankName']} - {b['AccountTitle'] or ''}", b["ID"])

        self.cheque_number_input = QLineEdit()
        self.cheque_bank_input = QLineEdit()
        self.cheque_sayad_input = QLineEdit()
        self.cheque_due_input = QLineEdit()
        self.cheque_due_input.setPlaceholderText("مثال: 1405/09/15")

        form.addRow("روش:", self.method_combo)
        form.addRow("مبلغ:", self.amount_input)
        form.addRow("صندوق:", self.cash_box_combo)
        form.addRow("حساب بانکی:", self.bank_combo)
        form.addRow("شماره چک:", self.cheque_number_input)
        form.addRow("بانک صادرکننده چک:", self.cheque_bank_input)
        form.addRow("شماره صیاد:", self.cheque_sayad_input)
        form.addRow("تاریخ سررسید چک:", self.cheque_due_input)

        layout.addLayout(form)
        ok_btn = QPushButton("افزودن")
        ok_btn.clicked.connect(self.confirm)
        layout.addWidget(ok_btn)
        self.setLayout(layout)
        self._update_visibility()

    def _update_visibility(self):
        method = self.method_combo.currentData()
        self.cash_box_combo.setVisible(method == "Cash")
        self.bank_combo.setVisible(method == "Bank")
        cheque_fields_visible = method == "Cheque"
        for w in (self.cheque_number_input, self.cheque_bank_input,
                  self.cheque_sayad_input, self.cheque_due_input):
            w.setVisible(cheque_fields_visible)

    def confirm(self):
        method = self.method_combo.currentData()
        amount = self.amount_input.value()
        if amount <= 0:
            QMessageBox.warning(self, "خطا", "مبلغ باید بزرگ‌تر از صفر باشد.")
            return

        line = {"method": method, "amount": amount}
        if method == "Cash":
            if self.cash_box_combo.count() == 0:
                QMessageBox.warning(self, "خطا", "ابتدا یک صندوق فعال بسازید.")
                return
            line["cash_box_id"] = self.cash_box_combo.currentData()
        elif method == "Bank":
            if self.bank_combo.count() == 0:
                QMessageBox.warning(self, "خطا", "ابتدا یک حساب بانکی فعال بسازید.")
                return
            line["bank_account_id"] = self.bank_combo.currentData()
        else:
            if not self.cheque_number_input.text().strip() or not self.cheque_due_input.text().strip():
                QMessageBox.warning(self, "خطا", "شماره چک و تاریخ سررسید الزامی است.")
                return
            line["cheque"] = {
                "number": self.cheque_number_input.text().strip(),
                "bank": self.cheque_bank_input.text().strip(),
                "sayad": self.cheque_sayad_input.text().strip(),
                "issue_date": today_shamsi_str(),
                "due_date": self.cheque_due_input.text().strip(),
            }

        self.result_line = line
        self.accept()


class NewReceiptDialog(QDialog):
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.lines = []
        self.invoice_rows = []
        self.setWindowTitle("ثبت سند دریافت وجه")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(750, 620)
        self._build_ui()
        self.load_customers()

    def _build_ui(self):
        layout = QVBoxLayout()
        form = QFormLayout()
        self.customer_combo = QComboBox()
        self.customer_combo.currentIndexChanged.connect(self.load_invoices)
        self.date_label = QLabel(today_shamsi_str())
        self.description_input = QTextEdit()
        self.description_input.setFixedHeight(40)
        form.addRow("مشتری:", self.customer_combo)
        form.addRow("تاریخ:", self.date_label)
        form.addRow("توضیحات:", self.description_input)
        layout.addLayout(form)

        layout.addWidget(QLabel("روش‌های دریافت (نقد / بانک / چک):"))
        add_line_btn = QPushButton("➕ افزودن روش دریافت")
        add_line_btn.clicked.connect(self.add_line)
        layout.addWidget(add_line_btn)

        self.lines_table = QTableWidget()
        self.lines_table.setColumnCount(4)
        self.lines_table.setHorizontalHeaderLabels(["روش", "مبلغ", "جزئیات", ""])
        self.lines_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.lines_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.lines_table.setMaximumHeight(140)
        layout.addWidget(self.lines_table)

        self.total_label = QLabel("جمع کل دریافت: 0")
        self.total_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.total_label)

        layout.addWidget(QLabel("تخصیص به فاکتور(های) فروش باز این مشتری (اختیاری):"))
        self.invoices_table = QTableWidget()
        self.invoices_table.setColumnCount(4)
        self.invoices_table.setHorizontalHeaderLabels(["شماره فاکتور", "تاریخ", "مانده فاکتور", "مبلغ تخصیص"])
        self.invoices_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.invoices_table)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("💾 ثبت سند دریافت")
        save_btn.clicked.connect(self.save_receipt)
        cancel_btn = QPushButton("انصراف")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        self.setLayout(layout)

    def load_customers(self):
        customers = get_customers()
        if not customers:
            QMessageBox.warning(self, "هشدار", "هیچ شخصی به‌عنوان «مشتری» ثبت نشده است.")
        for c in customers:
            self.customer_combo.addItem(c["FullName"], c["ID"])
        self.load_invoices()

    def load_invoices(self):
        self.invoice_rows = []
        self.invoices_table.setRowCount(0)
        if self.customer_combo.count() == 0:
            return
        customer_id = self.customer_combo.currentData()
        rows = get_unpaid_sales_invoices(customer_id)
        self.invoice_rows = rows
        self.invoices_table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.invoices_table.setItem(i, 0, QTableWidgetItem(str(r["InvoiceNumber"])))
            self.invoices_table.setItem(i, 1, QTableWidgetItem(r["ShamsiDate"] or ""))
            self.invoices_table.setItem(i, 2, QTableWidgetItem(f"{r['Remaining']:,.0f}"))
            alloc_input = QDoubleSpinBox()
            alloc_input.setMaximum(float(r["Remaining"]))
            alloc_input.setGroupSeparatorShown(True)
            self.invoices_table.setCellWidget(i, 3, alloc_input)

    def add_line(self):
        dlg = AddLineDialog()
        if dlg.exec() and dlg.result_line:
            self.lines.append(dlg.result_line)
            self.refresh_lines_table()

    def refresh_lines_table(self):
        method_fa = {"Cash": "نقد", "Bank": "بانک", "Cheque": "چک"}
        self.lines_table.setRowCount(len(self.lines))
        total = 0
        for i, line in enumerate(self.lines):
            total += line["amount"]
            self.lines_table.setItem(i, 0, QTableWidgetItem(method_fa[line["method"]]))
            self.lines_table.setItem(i, 1, QTableWidgetItem(f"{line['amount']:,.0f}"))
            detail = ""
            if line["method"] == "Cheque":
                detail = f"چک شماره {line['cheque']['number']} - سررسید {line['cheque']['due_date']}"
            self.lines_table.setItem(i, 2, QTableWidgetItem(detail))
            remove_btn = QPushButton("حذف")
            remove_btn.clicked.connect(lambda checked, idx=i: self.remove_line(idx))
            self.lines_table.setCellWidget(i, 3, remove_btn)
        self.total_label.setText(f"جمع کل دریافت: {total:,.0f}")

    def remove_line(self, index):
        del self.lines[index]
        self.refresh_lines_table()

    def save_receipt(self):
        if self.customer_combo.count() == 0:
            QMessageBox.warning(self, "خطا", "ابتدا یک مشتری ثبت کنید.")
            return
        if not self.lines:
            QMessageBox.warning(self, "خطا", "حداقل یک روش دریافت اضافه کنید.")
            return

        allocations = []
        for i, r in enumerate(self.invoice_rows):
            widget = self.invoices_table.cellWidget(i, 3)
            amount = widget.value() if widget else 0
            if amount > 0:
                allocations.append({"invoice_id": r["ID"], "amount": amount})

        try:
            receipt_id, receipt_number = create_receipt(
                customer_id=self.customer_combo.currentData(),
                shamsi_date=self.date_label.text(),
                description=self.description_input.toPlainText().strip(),
                user_id=self.current_user["ID"],
                lines=self.lines,
                allocations=allocations,
            )
            QMessageBox.information(self, "موفق", f"سند دریافت شماره {receipt_number} با موفقیت ثبت شد.")
            self.accept()
        except FinancialError as e:
            QMessageBox.warning(self, "خطا", str(e))
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"ثبت سند دریافت ناموفق بود:\n{e}")


class ReceiptsWindow(QWidget):
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.setWindowTitle("دریافت وجه از مشتری")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(800, 480)
        self._build_ui()
        self.load_data()

    def _build_ui(self):
        layout = QVBoxLayout()
        top_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("جستجو بر اساس شماره سند یا نام مشتری...")
        self.search_input.textChanged.connect(self.load_data)
        add_btn = QPushButton("➕ سند دریافت جدید")
        add_btn.clicked.connect(self.add_receipt)
        top_row.addWidget(self.search_input)
        top_row.addWidget(add_btn)
        layout.addLayout(top_row)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["شماره سند", "تاریخ", "مشتری", "مبلغ کل", "توضیحات"])
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)
        self.setLayout(layout)

    def load_data(self):
        rows = get_receipts(self.search_input.text())
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(str(r["ReceiptNumber"])))
            self.table.setItem(i, 1, QTableWidgetItem(r["ShamsiDate"] or ""))
            self.table.setItem(i, 2, QTableWidgetItem(r["PersonName"] or ""))
            self.table.setItem(i, 3, QTableWidgetItem(f"{r['TotalAmount']:,.0f}"))
            self.table.setItem(i, 4, QTableWidgetItem(r["Description"] or ""))

    def add_receipt(self):
        dlg = NewReceiptDialog(self.current_user)
        if dlg.exec():
            self.load_data()
