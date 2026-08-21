# -*- coding: utf-8 -*-
"""مدیریت اقساط: ساخت طرح قسط‌بندی برای فاکتور فروش نسیه + پرداخت هر قسط"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QDialog, QFormLayout, QComboBox,
    QDoubleSpinBox, QSpinBox, QMessageBox, QHeaderView, QTextEdit
)
from PyQt6.QtCore import Qt
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.persian_date import today_shamsi_str
from services.financial_service import (
    get_customers, get_unpaid_sales_invoices, get_installment_plans, get_installment_items,
    create_installment_plan, generate_equal_installments, mark_installment_paid,
    get_cash_boxes, get_bank_accounts, FinancialError
)


class NewInstallmentPlanDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.invoice_rows = []
        self.installments = []
        self.setWindowTitle("طرح اقساط جدید")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(650, 550)
        self._build_ui()
        self.load_customers()

    def _build_ui(self):
        layout = QVBoxLayout()
        form = QFormLayout()

        self.customer_combo = QComboBox()
        self.customer_combo.currentIndexChanged.connect(self.load_invoices)
        self.invoice_combo = QComboBox()
        self.invoice_combo.currentIndexChanged.connect(self._update_total)

        self.count_input = QSpinBox()
        self.count_input.setMinimum(1)
        self.count_input.setMaximum(60)
        self.count_input.setValue(3)

        self.start_date_input = QLineEdit(today_shamsi_str())
        self.months_apart_input = QSpinBox()
        self.months_apart_input.setMinimum(1)
        self.months_apart_input.setMaximum(12)
        self.months_apart_input.setValue(1)

        self.total_label = QLabel("مبلغ باقیمانده فاکتور: 0")
        self.description_input = QTextEdit()
        self.description_input.setFixedHeight(40)

        form.addRow("مشتری:", self.customer_combo)
        form.addRow("فاکتور فروش (نسیه):", self.invoice_combo)
        form.addRow(self.total_label)
        form.addRow("تعداد اقساط:", self.count_input)
        form.addRow("تاریخ شروع:", self.start_date_input)
        form.addRow("فاصله هر قسط (ماه):", self.months_apart_input)
        form.addRow("توضیحات:", self.description_input)
        layout.addLayout(form)

        gen_btn = QPushButton("📅 تولید خودکار اقساط مساوی")
        gen_btn.clicked.connect(self.generate_installments)
        layout.addWidget(gen_btn)

        self.items_table = QTableWidget()
        self.items_table.setColumnCount(2)
        self.items_table.setHorizontalHeaderLabels(["تاریخ سررسید", "مبلغ قسط"])
        self.items_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.items_table)
        layout.addWidget(QLabel("می‌توانید مبلغ یا تاریخ هر قسط را با دوبار کلیک ویرایش کنید."))

        btn_row = QHBoxLayout()
        save_btn = QPushButton("💾 ثبت طرح اقساط")
        save_btn.clicked.connect(self.save_plan)
        cancel_btn = QPushButton("انصراف")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        self.setLayout(layout)

    def load_customers(self):
        customers = get_customers()
        if not customers:
            QMessageBox.warning(self, "هشدار", "هیچ مشتری‌ای ثبت نشده است.")
        for c in customers:
            self.customer_combo.addItem(c["FullName"], c["ID"])
        self.load_invoices()

    def load_invoices(self):
        self.invoice_combo.clear()
        self.invoice_rows = []
        if self.customer_combo.count() == 0:
            return
        rows = get_unpaid_sales_invoices(self.customer_combo.currentData())
        self.invoice_rows = rows
        for r in rows:
            self.invoice_combo.addItem(
                f"فاکتور {r['InvoiceNumber']} - مانده {r['Remaining']:,.0f}", r["ID"]
            )
        self._update_total()

    def _update_total(self):
        remaining = 0
        idx = self.invoice_combo.currentIndex()
        if 0 <= idx < len(self.invoice_rows):
            remaining = float(self.invoice_rows[idx]["Remaining"])
        self.total_label.setText(f"مبلغ باقیمانده فاکتور: {remaining:,.0f}")

    def generate_installments(self):
        idx = self.invoice_combo.currentIndex()
        if not (0 <= idx < len(self.invoice_rows)):
            QMessageBox.warning(self, "خطا", "ابتدا یک فاکتور فروش انتخاب کنید.")
            return
        remaining = float(self.invoice_rows[idx]["Remaining"])
        try:
            items = generate_equal_installments(
                remaining, self.count_input.value(),
                self.start_date_input.text().strip(), self.months_apart_input.value()
            )
        except FinancialError as e:
            QMessageBox.warning(self, "خطا", str(e))
            return
        self.installments = items
        self.items_table.setRowCount(len(items))
        for i, item in enumerate(items):
            self.items_table.setItem(i, 0, QTableWidgetItem(item["due_date"]))
            self.items_table.setItem(i, 1, QTableWidgetItem(f"{item['amount']:.0f}"))

    def save_plan(self):
        idx = self.invoice_combo.currentIndex()
        if not (0 <= idx < len(self.invoice_rows)):
            QMessageBox.warning(self, "خطا", "ابتدا یک فاکتور فروش انتخاب کنید.")
            return
        if self.items_table.rowCount() == 0:
            QMessageBox.warning(self, "خطا", "ابتدا اقساط را تولید یا وارد کنید.")
            return

        installments = []
        for i in range(self.items_table.rowCount()):
            due = self.items_table.item(i, 0).text().strip()
            try:
                amount = float(self.items_table.item(i, 1).text().replace(",", ""))
            except (ValueError, AttributeError):
                QMessageBox.warning(self, "خطا", f"مبلغ ردیف {i+1} نامعتبر است.")
                return
            installments.append({"due_date": due, "amount": amount})

        invoice = self.invoice_rows[idx]
        try:
            create_installment_plan(
                customer_id=self.customer_combo.currentData(),
                sales_invoice_id=invoice["ID"],
                shamsi_date=today_shamsi_str(),
                description=self.description_input.toPlainText().strip(),
                user_id=self.parent_user_id,
                installments=installments,
            )
            QMessageBox.information(self, "موفق", "طرح اقساط با موفقیت ثبت شد.")
            self.accept()
        except FinancialError as e:
            QMessageBox.warning(self, "خطا", str(e))
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"ثبت طرح اقساط ناموفق بود:\n{e}")


class PayInstallmentDialog(QDialog):
    def __init__(self, item):
        super().__init__()
        self.item = item
        self.setWindowTitle(f"پرداخت قسط شماره {item['SeqNumber']}")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout = QVBoxLayout()
        info = QLabel(f"مبلغ قسط: {item['Amount']:,.0f} | سررسید: {item['DueShamsiDate']}")
        layout.addWidget(info)

        form = QFormLayout()
        self.method_combo = QComboBox()
        self.method_combo.addItem("نقد", "Cash")
        self.method_combo.addItem("بانک", "Bank")
        self.method_combo.currentIndexChanged.connect(self._update_visibility)

        self.cash_box_combo = QComboBox()
        for c in get_cash_boxes(active_only=True):
            self.cash_box_combo.addItem(c["Name"], c["ID"])

        self.bank_combo = QComboBox()
        for b in get_bank_accounts(active_only=True):
            self.bank_combo.addItem(f"{b['BankName']} - {b['AccountTitle'] or ''}", b["ID"])

        form.addRow("روش پرداخت:", self.method_combo)
        form.addRow("صندوق:", self.cash_box_combo)
        form.addRow("حساب بانکی:", self.bank_combo)
        layout.addLayout(form)

        ok_btn = QPushButton("ثبت پرداخت قسط")
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn)
        self.setLayout(layout)
        self._update_visibility()

    def _update_visibility(self):
        method = self.method_combo.currentData()
        self.cash_box_combo.setVisible(method == "Cash")
        self.bank_combo.setVisible(method == "Bank")


class InstallmentItemsDialog(QDialog):
    def __init__(self, plan_id, current_user):
        super().__init__()
        self.plan_id = plan_id
        self.current_user = current_user
        self.setWindowTitle("اقساط این طرح")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(600, 400)
        layout = QVBoxLayout()
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["قسط", "سررسید", "مبلغ", "وضعیت", ""])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)
        close_btn = QPushButton("بستن")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        self.setLayout(layout)
        self.load_items()

    def load_items(self):
        rows = get_installment_items(self.plan_id)
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(str(r["SeqNumber"])))
            self.table.setItem(i, 1, QTableWidgetItem(r["DueShamsiDate"]))
            self.table.setItem(i, 2, QTableWidgetItem(f"{r['Amount']:,.0f}"))
            status_fa = "پرداخت‌شده" if r["Status"] == "Paid" else "پرداخت‌نشده"
            self.table.setItem(i, 3, QTableWidgetItem(status_fa))

            if r["Status"] == "Paid":
                btn = QPushButton("پرداخت‌شده")
                btn.setEnabled(False)
            else:
                btn = QPushButton("ثبت پرداخت")
                btn.clicked.connect(lambda checked, item=r: self.pay_item(item))
            self.table.setCellWidget(i, 4, btn)

    def pay_item(self, item):
        dlg = PayInstallmentDialog(item)
        if not dlg.exec():
            return
        method = dlg.method_combo.currentData()
        cash_box_id = dlg.cash_box_combo.currentData() if method == "Cash" else None
        bank_account_id = dlg.bank_combo.currentData() if method == "Bank" else None
        if method == "Cash" and not cash_box_id:
            QMessageBox.warning(self, "خطا", "ابتدا یک صندوق فعال بسازید.")
            return
        if method == "Bank" and not bank_account_id:
            QMessageBox.warning(self, "خطا", "ابتدا یک حساب بانکی فعال بسازید.")
            return
        try:
            mark_installment_paid(
                item_id=item["ID"], method=method, shamsi_date=today_shamsi_str(),
                user_id=self.current_user["ID"], cash_box_id=cash_box_id, bank_account_id=bank_account_id
            )
            self.load_items()
        except FinancialError as e:
            QMessageBox.warning(self, "خطا", str(e))
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"ثبت پرداخت قسط ناموفق بود:\n{e}")


class InstallmentsWindow(QWidget):
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.setWindowTitle("مدیریت اقساط")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(800, 480)
        self._build_ui()
        self.load_data()

    def _build_ui(self):
        layout = QVBoxLayout()
        top_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("جستجو بر اساس نام مشتری...")
        self.search_input.textChanged.connect(self.load_data)
        add_btn = QPushButton("➕ طرح اقساط جدید")
        add_btn.clicked.connect(self.add_plan)
        top_row.addWidget(self.search_input)
        top_row.addWidget(add_btn)
        layout.addLayout(top_row)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["تاریخ ثبت", "مشتری", "شماره فاکتور", "مبلغ کل", "تعداد اقساط", "پرداخت‌شده", ""]
        )
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)
        self.setLayout(layout)

    def load_data(self):
        rows = get_installment_plans(self.search_input.text())
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(r["ShamsiDate"] or ""))
            self.table.setItem(i, 1, QTableWidgetItem(r["PersonName"] or ""))
            self.table.setItem(i, 2, QTableWidgetItem(str(r["InvoiceNumber"])))
            self.table.setItem(i, 3, QTableWidgetItem(f"{r['TotalAmount']:,.0f}"))
            self.table.setItem(i, 4, QTableWidgetItem(str(r["InstallmentCount"])))
            self.table.setItem(i, 5, QTableWidgetItem(f"{r['PaidCount']} از {r['InstallmentCount']}"))
            view_btn = QPushButton("مشاهده اقساط")
            view_btn.clicked.connect(lambda checked, plan_id=r["ID"]: self.view_items(plan_id))
            self.table.setCellWidget(i, 6, view_btn)

    def add_plan(self):
        dlg = NewInstallmentPlanDialog()
        dlg.parent_user_id = self.current_user["ID"]
        if dlg.exec():
            self.load_data()

    def view_items(self, plan_id):
        dlg = InstallmentItemsDialog(plan_id, self.current_user)
        dlg.exec()
