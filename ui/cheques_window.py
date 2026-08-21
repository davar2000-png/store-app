# -*- coding: utf-8 -*-
"""مدیریت چک‌های دریافتی و پرداختی: مشاهده لیست + تغییر وضعیت (وصول/برگشت/عودت)"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QDialog, QFormLayout, QComboBox,
    QMessageBox, QHeaderView, QTabWidget, QTextEdit
)
from PyQt6.QtCore import Qt
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.persian_date import today_shamsi_str
from services.financial_service import get_cheques, change_cheque_status, get_cash_boxes, get_bank_accounts, FinancialError

STATUS_FA = {
    "InHand": "نزد ما",
    "Deposited": "نزد بانک (در انتظار وصول)",
    "Cashed": "وصول شده",
    "Bounced": "برگشت خورده",
    "Returned": "عودت شده",
}


class ChangeStatusDialog(QDialog):
    def __init__(self, cheque):
        super().__init__()
        self.cheque = cheque
        self.setWindowTitle(f"تغییر وضعیت چک شماره {cheque['ChequeNumber']}")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(420, 320)

        layout = QVBoxLayout()
        info = QLabel(
            f"نوع: {'دریافتی' if cheque['ChequeType'] == 'Received' else 'پرداختی'} | "
            f"مبلغ: {cheque['Amount']:,.0f} | طرف حساب: {cheque['PersonName']}\n"
            f"وضعیت فعلی: {STATUS_FA.get(cheque['Status'], cheque['Status'])}"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QFormLayout()
        self.status_combo = QComboBox()
        if cheque["ChequeType"] == "Received":
            options = [("Deposited", "بردن به بانک (در انتظار وصول)"),
                       ("Cashed", "وصول / نقد شد"),
                       ("Bounced", "برگشت خورد"),
                       ("Returned", "عودت به مشتری")]
        else:
            options = [("Cashed", "پاس شد (کسر از صندوق/بانک)"),
                       ("Bounced", "برگشت خورد"),
                       ("Returned", "عودت از تأمین‌کننده")]
        for value, label in options:
            self.status_combo.addItem(label, value)
        self.status_combo.currentIndexChanged.connect(self._update_visibility)

        self.cash_box_combo = QComboBox()
        self.cash_box_combo.addItem("— انتخاب نشود —", None)
        for c in get_cash_boxes(active_only=True):
            self.cash_box_combo.addItem(c["Name"], c["ID"])

        self.bank_combo = QComboBox()
        self.bank_combo.addItem("— انتخاب نشود —", None)
        for b in get_bank_accounts(active_only=True):
            self.bank_combo.addItem(f"{b['BankName']} - {b['AccountTitle'] or ''}", b["ID"])

        self.note_input = QTextEdit()
        self.note_input.setFixedHeight(50)

        form.addRow("وضعیت جدید:", self.status_combo)
        form.addRow("واریز/برداشت به صندوق:", self.cash_box_combo)
        form.addRow("یا به حساب بانکی:", self.bank_combo)
        form.addRow("یادداشت:", self.note_input)
        layout.addLayout(form)

        ok_btn = QPushButton("ثبت تغییر وضعیت")
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn)
        self.setLayout(layout)
        self._update_visibility()

    def _update_visibility(self):
        is_cashed = self.status_combo.currentData() == "Cashed"
        self.cash_box_combo.setVisible(is_cashed)
        self.bank_combo.setVisible(is_cashed)


class ChequesWindow(QWidget):
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.setWindowTitle("مدیریت چک‌ها")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(850, 500)
        self._build_ui()
        self.load_data()

    def _build_ui(self):
        layout = QVBoxLayout()

        top_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("جستجو بر اساس شماره چک، نام طرف حساب یا بانک...")
        self.search_input.textChanged.connect(self.load_data)
        top_row.addWidget(self.search_input)
        layout.addLayout(top_row)

        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self.load_data)
        self.received_table = self._make_table()
        self.issued_table = self._make_table()
        self.tabs.addTab(self._wrap(self.received_table), "📥 چک‌های دریافتی")
        self.tabs.addTab(self._wrap(self.issued_table), "📤 چک‌های پرداختی")
        layout.addWidget(self.tabs)

        self.setLayout(layout)

    def _make_table(self):
        table = QTableWidget()
        table.setColumnCount(7)
        table.setHorizontalHeaderLabels(
            ["شماره چک", "بانک", "طرف حساب", "مبلغ", "تاریخ سررسید", "وضعیت", ""]
        )
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        return table

    def _wrap(self, table):
        w = QWidget()
        l = QVBoxLayout()
        l.addWidget(table)
        w.setLayout(l)
        return w

    def load_data(self):
        cheque_type = "Received" if self.tabs.currentIndex() == 0 else "Issued"
        table = self.received_table if cheque_type == "Received" else self.issued_table
        rows = get_cheques(cheque_type, self.search_input.text())
        table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            table.setItem(i, 0, QTableWidgetItem(r["ChequeNumber"]))
            table.setItem(i, 1, QTableWidgetItem(r["BankName"] or ""))
            table.setItem(i, 2, QTableWidgetItem(r["PersonName"] or ""))
            table.setItem(i, 3, QTableWidgetItem(f"{r['Amount']:,.0f}"))
            table.setItem(i, 4, QTableWidgetItem(r["DueShamsiDate"] or ""))
            table.setItem(i, 5, QTableWidgetItem(STATUS_FA.get(r["Status"], r["Status"])))

            if r["Status"] in ("Cashed", "Bounced", "Returned"):
                btn = QPushButton("نهایی‌شده")
                btn.setEnabled(False)
            else:
                btn = QPushButton("تغییر وضعیت")
                btn.clicked.connect(lambda checked, cheque=r: self.change_status(cheque))
            table.setCellWidget(i, 6, btn)

    def change_status(self, cheque):
        dlg = ChangeStatusDialog(cheque)
        if not dlg.exec():
            return
        try:
            change_cheque_status(
                cheque_id=cheque["ID"],
                new_status=dlg.status_combo.currentData(),
                shamsi_date=today_shamsi_str(),
                user_id=self.current_user["ID"],
                cash_box_id=dlg.cash_box_combo.currentData(),
                bank_account_id=dlg.bank_combo.currentData(),
                note=dlg.note_input.toPlainText().strip(),
            )
            self.load_data()
        except FinancialError as e:
            QMessageBox.warning(self, "خطا", str(e))
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"تغییر وضعیت چک ناموفق بود:\n{e}")
