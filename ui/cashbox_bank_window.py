# -*- coding: utf-8 -*-
"""مدیریت صندوق‌ها و حساب‌های بانکی + واریز/برداشت دستی + مشاهده گردش حساب"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QDialog, QFormLayout, QLineEdit, QDoubleSpinBox,
    QMessageBox, QHeaderView, QTabWidget, QComboBox
)
from PyQt6.QtCore import Qt
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.persian_date import today_shamsi_str
from services.financial_service import (
    get_cash_boxes, get_bank_accounts, create_cash_box, create_bank_account,
    get_cash_box_transactions, get_bank_transactions,
    manual_cash_box_transaction, manual_bank_transaction, FinancialError
)


class NewCashBoxDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("صندوق جدید")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        f = QFormLayout()
        self.name_input = QLineEdit()
        self.balance_input = QDoubleSpinBox()
        self.balance_input.setMaximum(999999999999)
        self.balance_input.setGroupSeparatorShown(True)
        f.addRow("نام صندوق:", self.name_input)
        f.addRow("موجودی اولیه:", self.balance_input)
        save_btn = QPushButton("💾 ثبت")
        save_btn.clicked.connect(self.save)
        f.addRow(save_btn)
        self.setLayout(f)

    def save(self):
        try:
            create_cash_box(self.name_input.text(), self.balance_input.value())
            self.accept()
        except FinancialError as e:
            QMessageBox.warning(self, "خطا", str(e))


class NewBankAccountDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("حساب بانکی جدید")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(400, 300)
        f = QFormLayout()
        self.bank_input = QLineEdit()
        self.title_input = QLineEdit()
        self.number_input = QLineEdit()
        self.sheba_input = QLineEdit()
        self.card_input = QLineEdit()
        self.balance_input = QDoubleSpinBox()
        self.balance_input.setMaximum(999999999999)
        self.balance_input.setGroupSeparatorShown(True)
        f.addRow("نام بانک:", self.bank_input)
        f.addRow("عنوان حساب:", self.title_input)
        f.addRow("شماره حساب:", self.number_input)
        f.addRow("شماره شبا:", self.sheba_input)
        f.addRow("شماره کارت:", self.card_input)
        f.addRow("موجودی اولیه:", self.balance_input)
        save_btn = QPushButton("💾 ثبت")
        save_btn.clicked.connect(self.save)
        f.addRow(save_btn)
        self.setLayout(f)

    def save(self):
        try:
            create_bank_account(
                self.bank_input.text(), self.title_input.text(), self.number_input.text(),
                self.sheba_input.text(), self.card_input.text(), self.balance_input.value()
            )
            self.accept()
        except FinancialError as e:
            QMessageBox.warning(self, "خطا", str(e))


class ManualTransactionDialog(QDialog):
    """واریز/برداشت دستی به صندوق یا حساب بانکی"""

    def __init__(self, kind: str):
        super().__init__()
        self.kind = kind  # "cash" or "bank"
        self.setWindowTitle("ثبت واریز/برداشت دستی")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        f = QFormLayout()
        self.type_combo = QComboBox()
        if kind == "cash":
            self.type_combo.addItem("واریز به صندوق", "In")
            self.type_combo.addItem("برداشت از صندوق", "Out")
        else:
            self.type_combo.addItem("واریز به حساب", "Deposit")
            self.type_combo.addItem("برداشت از حساب", "Withdraw")
        self.amount_input = QDoubleSpinBox()
        self.amount_input.setMaximum(999999999999)
        self.amount_input.setGroupSeparatorShown(True)
        self.desc_input = QLineEdit()
        f.addRow("نوع تراکنش:", self.type_combo)
        f.addRow("مبلغ:", self.amount_input)
        f.addRow("توضیحات:", self.desc_input)
        ok_btn = QPushButton("تایید")
        ok_btn.clicked.connect(self.accept)
        f.addRow(ok_btn)
        self.setLayout(f)


class CashBoxBankWindow(QWidget):
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.setWindowTitle("صندوق و بانک")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(800, 500)
        self._build_ui()
        self.load_data()

    def _build_ui(self):
        layout = QVBoxLayout()
        self.tabs = QTabWidget()

        # --- تب صندوق‌ها ---
        cash_tab = QWidget()
        cash_layout = QVBoxLayout()
        cash_top = QHBoxLayout()
        add_cash_btn = QPushButton("➕ صندوق جدید")
        add_cash_btn.clicked.connect(self.add_cash_box)
        cash_top.addStretch()
        cash_top.addWidget(add_cash_btn)
        cash_layout.addLayout(cash_top)

        self.cash_table = QTableWidget()
        self.cash_table.setColumnCount(5)
        self.cash_table.setHorizontalHeaderLabels(["نام صندوق", "موجودی اولیه", "موجودی فعلی", "", ""])
        self.cash_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.cash_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        cash_layout.addWidget(self.cash_table)
        cash_tab.setLayout(cash_layout)

        # --- تب بانک ---
        bank_tab = QWidget()
        bank_layout = QVBoxLayout()
        bank_top = QHBoxLayout()
        add_bank_btn = QPushButton("➕ حساب بانکی جدید")
        add_bank_btn.clicked.connect(self.add_bank_account)
        bank_top.addStretch()
        bank_top.addWidget(add_bank_btn)
        bank_layout.addLayout(bank_top)

        self.bank_table = QTableWidget()
        self.bank_table.setColumnCount(5)
        self.bank_table.setHorizontalHeaderLabels(["بانک / عنوان حساب", "شماره حساب", "موجودی فعلی", "", ""])
        self.bank_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.bank_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        bank_layout.addWidget(self.bank_table)
        bank_tab.setLayout(bank_layout)

        self.tabs.addTab(cash_tab, "💵 صندوق‌ها")
        self.tabs.addTab(bank_tab, "🏦 حساب‌های بانکی")
        layout.addWidget(self.tabs)
        self.setLayout(layout)

    def load_data(self):
        cash_boxes = get_cash_boxes()
        self.cash_table.setRowCount(len(cash_boxes))
        for i, c in enumerate(cash_boxes):
            self.cash_table.setItem(i, 0, QTableWidgetItem(c["Name"]))
            self.cash_table.setItem(i, 1, QTableWidgetItem(f"{c['InitialBalance']:,.0f}"))
            self.cash_table.setItem(i, 2, QTableWidgetItem(f"{c['CurrentBalance']:,.0f}"))
            tx_btn = QPushButton("واریز/برداشت")
            tx_btn.clicked.connect(lambda checked, cid=c["ID"]: self.manual_tx("cash", cid))
            self.cash_table.setCellWidget(i, 3, tx_btn)
            hist_btn = QPushButton("گردش حساب")
            hist_btn.clicked.connect(lambda checked, cid=c["ID"], name=c["Name"]: self.show_history("cash", cid, name))
            self.cash_table.setCellWidget(i, 4, hist_btn)

        banks = get_bank_accounts()
        self.bank_table.setRowCount(len(banks))
        for i, b in enumerate(banks):
            title = f"{b['BankName']} - {b['AccountTitle'] or ''}"
            self.bank_table.setItem(i, 0, QTableWidgetItem(title))
            self.bank_table.setItem(i, 1, QTableWidgetItem(b["AccountNumber"] or ""))
            self.bank_table.setItem(i, 2, QTableWidgetItem(f"{b['CurrentBalance']:,.0f}"))
            tx_btn = QPushButton("واریز/برداشت")
            tx_btn.clicked.connect(lambda checked, bid=b["ID"]: self.manual_tx("bank", bid))
            self.bank_table.setCellWidget(i, 3, tx_btn)
            hist_btn = QPushButton("گردش حساب")
            hist_btn.clicked.connect(lambda checked, bid=b["ID"], name=title: self.show_history("bank", bid, name))
            self.bank_table.setCellWidget(i, 4, hist_btn)

    def add_cash_box(self):
        dlg = NewCashBoxDialog()
        if dlg.exec():
            self.load_data()

    def add_bank_account(self):
        dlg = NewBankAccountDialog()
        if dlg.exec():
            self.load_data()

    def manual_tx(self, kind, ref_id):
        dlg = ManualTransactionDialog(kind)
        if not dlg.exec():
            return
        try:
            if kind == "cash":
                manual_cash_box_transaction(
                    ref_id, dlg.type_combo.currentData(), dlg.amount_input.value(),
                    today_shamsi_str(), dlg.desc_input.text(), self.current_user["ID"]
                )
            else:
                manual_bank_transaction(
                    ref_id, dlg.type_combo.currentData(), dlg.amount_input.value(),
                    today_shamsi_str(), dlg.desc_input.text(), self.current_user["ID"]
                )
            self.load_data()
        except FinancialError as e:
            QMessageBox.warning(self, "خطا", str(e))
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"ثبت تراکنش ناموفق بود:\n{e}")

    def show_history(self, kind, ref_id, name):
        rows = get_cash_box_transactions(ref_id) if kind == "cash" else get_bank_transactions(ref_id)
        dlg = QDialog(self)
        dlg.setWindowTitle(f"گردش حساب: {name}")
        dlg.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        dlg.resize(650, 400)
        layout = QVBoxLayout()
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(["نوع", "مبلغ", "موجودی بعد از تراکنش", "مرجع", "تاریخ", "توضیحات"])
        table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setRowCount(len(rows))
        type_fa = {"In": "واریز", "Out": "برداشت", "Deposit": "واریز", "Withdraw": "برداشت"}
        for i, r in enumerate(rows):
            table.setItem(i, 0, QTableWidgetItem(type_fa.get(r["TransactionType"], r["TransactionType"])))
            table.setItem(i, 1, QTableWidgetItem(f"{r['Amount']:,.0f}"))
            table.setItem(i, 2, QTableWidgetItem(f"{r['BalanceAfter']:,.0f}"))
            table.setItem(i, 3, QTableWidgetItem(r["RefTable"] or ""))
            table.setItem(i, 4, QTableWidgetItem(r["ShamsiDate"] or ""))
            table.setItem(i, 5, QTableWidgetItem(r["Description"] or ""))
        layout.addWidget(table)
        close_btn = QPushButton("بستن")
        close_btn.clicked.connect(dlg.accept)
        layout.addWidget(close_btn)
        dlg.setLayout(layout)
        dlg.exec()
