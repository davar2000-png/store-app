# -*- coding: utf-8 -*-
"""مدیریت اشخاص: نمایش لیست، افزودن، ویرایش، حذف نرم"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QDialog, QFormLayout, QCheckBox,
    QMessageBox, QHeaderView
)
from PyQt6.QtCore import Qt
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import Database
from utils.persian_date import today_shamsi_str


class PersonDialog(QDialog):
    """فرم افزودن / ویرایش شخص"""

    def __init__(self, person=None):
        super().__init__()
        self.person = person
        self.setWindowTitle("ویرایش شخص" if person else "افزودن شخص جدید")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedWidth(420)
        self._build_ui()

    def _build_ui(self):
        layout = QFormLayout()

        self.name_input = QLineEdit()
        self.mobile_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.national_code_input = QLineEdit()
        self.address_input = QLineEdit()
        self.baleh_chat_id_input = QLineEdit()
        self.is_customer = QCheckBox("مشتری")
        self.is_seller = QCheckBox("فروشنده")
        self.is_employee = QCheckBox("کارمند")

        if self.person:
            self.name_input.setText(self.person.get("FullName") or "")
            self.mobile_input.setText(self.person.get("Mobile") or "")
            self.phone_input.setText(self.person.get("Phone") or "")
            self.national_code_input.setText(self.person.get("NationalCode") or "")
            self.address_input.setText(self.person.get("Address") or "")
            self.baleh_chat_id_input.setText(self.person.get("BalehChatId") or "")
            self.is_customer.setChecked(bool(self.person.get("IsCustomer")))
            self.is_seller.setChecked(bool(self.person.get("IsSeller")))
            self.is_employee.setChecked(bool(self.person.get("IsEmployee")))

        layout.addRow("نام / نام شرکت:", self.name_input)
        layout.addRow("موبایل:", self.mobile_input)
        layout.addRow("تلفن:", self.phone_input)
        layout.addRow("کد ملی:", self.national_code_input)
        layout.addRow("آدرس:", self.address_input)
        layout.addRow("شناسه چت بله (Chat ID):", self.baleh_chat_id_input)
        layout.addRow(self.is_customer)
        layout.addRow(self.is_seller)
        layout.addRow(self.is_employee)

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
            QMessageBox.warning(self, "خطا", "نام نمی‌تواند خالی باشد.")
            return

        db = Database()
        try:
            if self.person:
                db.execute(
                    """UPDATE Persons SET FullName=?, Mobile=?, Phone=?, NationalCode=?,
                       Address=?, BalehChatId=?, IsCustomer=?, IsSeller=?, IsEmployee=?, UpdatedAt=GETDATE()
                       WHERE ID=?""",
                    (self.name_input.text().strip(), self.mobile_input.text().strip(),
                     self.phone_input.text().strip(), self.national_code_input.text().strip(),
                     self.address_input.text().strip(), self.baleh_chat_id_input.text().strip(),
                     int(self.is_customer.isChecked()),
                     int(self.is_seller.isChecked()), int(self.is_employee.isChecked()),
                     self.person["ID"])
                )
            else:
                db.execute(
                    """INSERT INTO Persons
                       (FullName, Mobile, Phone, NationalCode, Address, BalehChatId,
                        IsCustomer, IsSeller, IsEmployee, CreatedShamsiDate)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (self.name_input.text().strip(), self.mobile_input.text().strip(),
                     self.phone_input.text().strip(), self.national_code_input.text().strip(),
                     self.address_input.text().strip(), self.baleh_chat_id_input.text().strip(),
                     int(self.is_customer.isChecked()),
                     int(self.is_seller.isChecked()), int(self.is_employee.isChecked()),
                     today_shamsi_str())
                )
            db.close()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"ذخیره‌سازی ناموفق بود:\n{e}")


class PersonsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("مدیریت اشخاص")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(800, 500)
        self._build_ui()
        self.load_data()

    def _build_ui(self):
        layout = QVBoxLayout()

        top_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("جستجو بر اساس نام، موبایل یا کد ملی...")
        self.search_input.textChanged.connect(self.load_data)
        add_btn = QPushButton("➕ افزودن شخص")
        add_btn.clicked.connect(self.add_person)
        top_row.addWidget(self.search_input)
        top_row.addWidget(add_btn)
        layout.addLayout(top_row)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["نام", "موبایل", "تلفن", "کد ملی", "نوع", "", ""]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        self.setLayout(layout)

    def load_data(self):
        db = Database()
        search = f"%{self.search_input.text().strip()}%"
        rows = db.fetch_all(
            """SELECT * FROM Persons
               WHERE IsDeleted = 0 AND
                     (FullName LIKE ? OR Mobile LIKE ? OR NationalCode LIKE ?)
               ORDER BY FullName""",
            (search, search, search)
        )
        db.close()

        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            types = []
            if r["IsCustomer"]:
                types.append("مشتری")
            if r["IsSeller"]:
                types.append("فروشنده")
            if r["IsEmployee"]:
                types.append("کارمند")

            self.table.setItem(i, 0, QTableWidgetItem(r["FullName"] or ""))
            self.table.setItem(i, 1, QTableWidgetItem(r["Mobile"] or ""))
            self.table.setItem(i, 2, QTableWidgetItem(r["Phone"] or ""))
            self.table.setItem(i, 3, QTableWidgetItem(r["NationalCode"] or ""))
            self.table.setItem(i, 4, QTableWidgetItem("، ".join(types)))

            edit_btn = QPushButton("ویرایش")
            edit_btn.clicked.connect(lambda checked, row=r: self.edit_person(row))
            self.table.setCellWidget(i, 5, edit_btn)

            msg_btn = QPushButton("📱 پیام")
            msg_btn.clicked.connect(lambda checked, row=r: self.send_message(row))
            self.table.setCellWidget(i, 6, msg_btn)

    def send_message(self, person):
        from ui.communication_window import QuickSendDialog
        dlg = QuickSendDialog(person)
        dlg.exec()

    def add_person(self):
        dlg = PersonDialog()
        if dlg.exec():
            self.load_data()

    def edit_person(self, person):
        dlg = PersonDialog(person)
        if dlg.exec():
            self.load_data()
