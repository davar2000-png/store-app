# -*- coding: utf-8 -*-
"""پنجره تنظیمات نرم‌افزار — تنظیمات عمومی، مدیریت کاربران، دسترسی به بخش‌ها (فقط مدیر سیستم)"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QCheckBox, QComboBox, QTabWidget,
    QHeaderView, QFormLayout, QMessageBox, QDialog
)
from PyQt6.QtCore import Qt
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import services.settings_service as ss


def make_table(headers):
    table = QTableWidget()
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    return table


# =========================================================
# تب تنظیمات عمومی
# =========================================================
class GeneralTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self.load_settings()

    def _build_ui(self):
        layout = QVBoxLayout()

        layout.addWidget(QLabel("🏪 اطلاعات فروشگاه (در چاپ فاکتور و متن پیام‌ها استفاده می‌شود)"))
        store_form = QFormLayout()
        self.store_name_input = QLineEdit()
        self.store_address_input = QLineEdit()
        self.store_phone_input = QLineEdit()
        store_form.addRow("نام فروشگاه:", self.store_name_input)
        store_form.addRow("آدرس:", self.store_address_input)
        store_form.addRow("تلفن:", self.store_phone_input)
        layout.addLayout(store_form)

        layout.addWidget(QLabel("📦 تنظیمات فروش و انبار"))
        sales_form = QFormLayout()
        self.allow_negative_stock = QCheckBox("اجازه فروش با موجودی منفی (کالا حتی اگر موجود نباشد، قابل فروش باشد)")
        self.default_profit_input = QLineEdit()
        self.default_profit_input.setPlaceholderText("مثلاً 20")
        sales_form.addRow(self.allow_negative_stock)
        sales_form.addRow("درصد سود پیش‌فرض هنگام محاسبه قیمت فروش کالای جدید:", self.default_profit_input)
        layout.addLayout(sales_form)

        save_btn = QPushButton("💾 ذخیره تنظیمات")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)
        layout.addStretch()

        self.setLayout(layout)

    def load_settings(self):
        s = ss.get_general_settings()
        self.store_name_input.setText(s.get("StoreName", ""))
        self.store_address_input.setText(s.get("StoreAddress", ""))
        self.store_phone_input.setText(s.get("StorePhone", ""))
        self.allow_negative_stock.setChecked(s.get("AllowNegativeStock", "0") == "1")
        self.default_profit_input.setText(s.get("DefaultProfitPercent", "20"))

    def save_settings(self):
        profit_text = self.default_profit_input.text().strip() or "0"
        try:
            float(profit_text)
        except ValueError:
            QMessageBox.warning(self, "خطا", "درصد سود باید یک عدد باشد.")
            return

        ss.save_general_settings({
            "StoreName": self.store_name_input.text().strip(),
            "StoreAddress": self.store_address_input.text().strip(),
            "StorePhone": self.store_phone_input.text().strip(),
            "AllowNegativeStock": "1" if self.allow_negative_stock.isChecked() else "0",
            "DefaultProfitPercent": profit_text,
        })
        QMessageBox.information(self, "ذخیره شد", "تنظیمات عمومی با موفقیت ذخیره شد.")


# =========================================================
# دیالوگ افزودن / ویرایش کاربر
# =========================================================
class UserDialog(QDialog):
    def __init__(self, user=None, is_self=False):
        super().__init__()
        self.user = user
        self.is_self = is_self  # آیا کاربر در حال ویرایش، همان کاربر لاگین‌کرده است؟
        self.setWindowTitle("ویرایش کاربر" if user else "افزودن کاربر جدید")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedWidth(400)
        self._build_ui()

    def _build_ui(self):
        layout = QFormLayout()

        self.username_input = QLineEdit()
        self.fullname_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.is_admin = QCheckBox("مدیر سیستم (دسترسی کامل به همه بخش‌ها و تنظیمات)")
        self.is_active = QCheckBox("فعال")
        self.is_active.setChecked(True)

        if self.user:
            self.username_input.setText(self.user.get("Username") or "")
            self.username_input.setEnabled(False)  # نام کاربری بعد از ساخت قابل تغییر نیست
            self.fullname_input.setText(self.user.get("FullName") or "")
            self.password_input.setPlaceholderText("خالی بگذارید یعنی بدون تغییر")
            self.is_admin.setChecked(bool(self.user.get("IsAdmin")))
            self.is_active.setChecked(bool(self.user.get("IsActive")))
        else:
            self.password_input.setPlaceholderText("رمز عبور کاربر جدید")

        layout.addRow("نام کاربری:", self.username_input)
        layout.addRow("نام و نام‌خانوادگی:", self.fullname_input)
        layout.addRow("رمز عبور:" if not self.user else "رمز عبور جدید:", self.password_input)
        layout.addRow(self.is_admin)
        layout.addRow(self.is_active)

        save_btn = QPushButton("💾 ذخیره")
        save_btn.clicked.connect(self.save)
        layout.addRow(save_btn)

        self.setLayout(layout)

    def save(self):
        username = self.username_input.text().strip()
        full_name = self.fullname_input.text().strip()
        password = self.password_input.text()

        if not username or not full_name:
            QMessageBox.warning(self, "خطا", "نام کاربری و نام کامل الزامی است.")
            return

        if self.is_self and (not self.is_admin.isChecked() or not self.is_active.isChecked()):
            QMessageBox.warning(
                self, "خطا",
                "نمی‌توانید دسترسی مدیر یا وضعیت فعال بودن حساب خودتان را از خودتان بگیرید،\n"
                "چون بعد از آن دیگر کسی نمی‌تواند این تنظیم را برایتان برگرداند."
            )
            return

        try:
            if self.user:
                ss.update_user(
                    self.user["ID"], full_name,
                    self.is_admin.isChecked(), self.is_active.isChecked()
                )
                if password:
                    ss.reset_user_password(self.user["ID"], password)
            else:
                if not password:
                    QMessageBox.warning(self, "خطا", "برای کاربر جدید، رمز عبور الزامی است.")
                    return
                ss.create_user(username, full_name, password, self.is_admin.isChecked())
        except ValueError as e:
            QMessageBox.warning(self, "خطا", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"ذخیره‌سازی ناموفق بود:\n{e}")
            return

        self.accept()


# =========================================================
# تب مدیریت کاربران
# =========================================================
class UsersTab(QWidget):
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self._build_ui()
        self.load_users()

    def _build_ui(self):
        layout = QVBoxLayout()

        top_row = QHBoxLayout()
        add_btn = QPushButton("➕ افزودن کاربر جدید")
        add_btn.clicked.connect(self.add_user)
        refresh_btn = QPushButton("🔄 بروزرسانی")
        refresh_btn.clicked.connect(self.load_users)
        top_row.addWidget(add_btn)
        top_row.addWidget(refresh_btn)
        top_row.addStretch()
        layout.addLayout(top_row)

        self.table = make_table(["نام و نام‌خانوادگی", "نام کاربری", "مدیر سیستم؟", "وضعیت", "آخرین ورود", ""])
        layout.addWidget(self.table)

        self.setLayout(layout)
        self.users = []

    def load_users(self):
        self.users = ss.list_users()
        self.table.setRowCount(len(self.users))
        for i, u in enumerate(self.users):
            self.table.setItem(i, 0, QTableWidgetItem(u["FullName"] or ""))
            self.table.setItem(i, 1, QTableWidgetItem(u["Username"] or ""))
            self.table.setItem(i, 2, QTableWidgetItem("✅ بله" if u["IsAdmin"] else "خیر"))
            self.table.setItem(i, 3, QTableWidgetItem("فعال" if u["IsActive"] else "❌ غیرفعال"))
            last_login = str(u["LastLogin"])[:16] if u["LastLogin"] else "—"
            self.table.setItem(i, 4, QTableWidgetItem(last_login))
            edit_btn = QPushButton("✏️ ویرایش")
            edit_btn.clicked.connect(lambda checked, row=u: self.edit_user(row))
            self.table.setCellWidget(i, 5, edit_btn)

    def add_user(self):
        dlg = UserDialog()
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_users()

    def edit_user(self, user):
        dlg = UserDialog(user, is_self=(user["ID"] == self.current_user["ID"]))
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_users()


# =========================================================
# تب دسترسی کاربران به بخش‌ها
# =========================================================
class PermissionsTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self.load_users()

    def _build_ui(self):
        layout = QVBoxLayout()

        info = QLabel(
            "دسترسی هر کاربر (غیر از مدیر سیستم) به بخش‌های نرم‌افزار را اینجا مشخص کنید.\n"
            "مدیر سیستم همیشه به همه بخش‌ها دسترسی کامل دارد. اگر تیک بخشی برداشته شود،\n"
            "دکمه‌ی آن بخش برای آن کاربر در صفحه اصلی دیده نمی‌شود."
        )
        layout.addWidget(info)

        row = QHBoxLayout()
        row.addWidget(QLabel("کاربر:"))
        self.user_combo = QComboBox()
        self.user_combo.currentIndexChanged.connect(self.load_permissions)
        row.addWidget(self.user_combo, 1)
        layout.addLayout(row)

        self.checkboxes = {}
        checks_layout = QVBoxLayout()
        for key, label in ss.MODULE_PERMISSIONS:
            cb = QCheckBox(label)
            self.checkboxes[key] = cb
            checks_layout.addWidget(cb)
        layout.addLayout(checks_layout)

        save_btn = QPushButton("💾 ذخیره دسترسی‌های این کاربر")
        save_btn.clicked.connect(self.save_permissions)
        layout.addWidget(save_btn)
        layout.addStretch()

        self.setLayout(layout)

    def load_users(self):
        self.users = [u for u in ss.list_users() if not u["IsAdmin"]]
        self.user_combo.clear()
        if not self.users:
            self.user_combo.addItem("— هیچ کاربر غیرمدیری وجود ندارد —", None)
            for cb in self.checkboxes.values():
                cb.setEnabled(False)
            return
        for u in self.users:
            self.user_combo.addItem(f"{u['FullName']} ({u['Username']})", u["ID"])

    def load_permissions(self):
        user_id = self.user_combo.currentData()
        if not user_id:
            return
        saved = ss.get_user_permissions(user_id)
        for key, cb in self.checkboxes.items():
            # اگر برای این کاربر تنظیمی ثبت نشده باشد، پیش‌فرض «مجاز» (تیک‌خورده) نمایش داده می‌شود
            cb.setChecked(saved.get(key, True))
            cb.setEnabled(True)

    def save_permissions(self):
        user_id = self.user_combo.currentData()
        if not user_id:
            QMessageBox.warning(self, "توجه", "هیچ کاربری برای تنظیم دسترسی انتخاب نشده است.")
            return
        permissions = {key: cb.isChecked() for key, cb in self.checkboxes.items()}
        ss.save_user_permissions(user_id, permissions)
        QMessageBox.information(self, "ذخیره شد", "دسترسی‌های این کاربر با موفقیت ذخیره شد.")


# =========================================================
# پنجره اصلی تنظیمات
# =========================================================
class SettingsWindow(QWidget):
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.setWindowTitle("⚙️ تنظیمات نرم‌افزار")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(650, 560)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        tabs = QTabWidget()
        tabs.addTab(GeneralTab(), "🏪 تنظیمات عمومی")
        tabs.addTab(UsersTab(self.current_user), "👥 مدیریت کاربران")
        tabs.addTab(PermissionsTab(), "🔐 دسترسی به بخش‌ها")
        layout.addWidget(tabs)
        self.setLayout(layout)
