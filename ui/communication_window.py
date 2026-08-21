# -*- coding: utf-8 -*-
"""پنجره ارتباط با مشتری — تنظیمات پیامک/بله، قالب‌ها، ارسال دستی، یادآوری دسته‌جمعی، تاریخچه"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QComboBox, QTabWidget, QHeaderView,
    QFormLayout, QTextEdit, QMessageBox, QDialog
)
from PyQt6.QtCore import Qt
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import Database
import services.communication_service as cs


def make_table(headers):
    table = QTableWidget()
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    return table


# =========================================================
# تب تنظیمات
# =========================================================
class SettingsTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self.load_settings()

    def _build_ui(self):
        layout = QVBoxLayout()

        layout.addWidget(QLabel("📱 تنظیمات سرویس پیامک"))
        sms_form = QFormLayout()
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["Kavenegar", "Melipayamak", "Custom"])
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("کلید API (کاوه‌نگار) یا رمز عبور (ملی‌پیامک)")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("فقط برای ملی‌پیامک")
        self.sender_input = QLineEdit()
        self.custom_url_input = QLineEdit()
        self.custom_url_input.setPlaceholderText("مثال: https://example.com/send?phone={phone}&text={text}")

        sms_form.addRow("سرویس‌دهنده:", self.provider_combo)
        sms_form.addRow("کلید API / رمز عبور:", self.api_key_input)
        sms_form.addRow("نام کاربری:", self.username_input)
        sms_form.addRow("شماره خط ارسال:", self.sender_input)
        sms_form.addRow("آدرس API سفارشی (Custom):", self.custom_url_input)
        layout.addLayout(sms_form)

        layout.addWidget(QLabel("🔵 تنظیمات ربات بله"))
        baleh_form = QFormLayout()
        self.baleh_token_input = QLineEdit()
        self.baleh_token_input.setPlaceholderText("توکن ربات بله (از @BotFather در بله دریافت می‌شود)")
        baleh_form.addRow("توکن ربات:", self.baleh_token_input)
        layout.addLayout(baleh_form)

        layout.addWidget(QLabel("🏪 نام فروشگاه (برای درج در متن پیام‌ها)"))
        self.store_name_input = QLineEdit()
        layout.addWidget(self.store_name_input)

        save_btn = QPushButton("💾 ذخیره تنظیمات")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)
        layout.addStretch()

        self.setLayout(layout)

    def load_settings(self):
        s = cs.get_communication_settings()
        idx = self.provider_combo.findText(s.get("SmsProvider", "Kavenegar"))
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)
        self.api_key_input.setText(s.get("SmsApiKey", ""))
        self.username_input.setText(s.get("SmsUsername", ""))
        self.sender_input.setText(s.get("SmsSenderNumber", ""))
        self.custom_url_input.setText(s.get("SmsCustomUrlTemplate", ""))
        self.baleh_token_input.setText(s.get("BalehBotToken", ""))
        self.store_name_input.setText(s.get("StoreName", ""))

    def save_settings(self):
        cs.save_communication_settings({
            "SmsProvider": self.provider_combo.currentText(),
            "SmsApiKey": self.api_key_input.text().strip(),
            "SmsUsername": self.username_input.text().strip(),
            "SmsSenderNumber": self.sender_input.text().strip(),
            "SmsCustomUrlTemplate": self.custom_url_input.text().strip(),
            "BalehBotToken": self.baleh_token_input.text().strip(),
            "StoreName": self.store_name_input.text().strip(),
        })
        QMessageBox.information(self, "ذخیره شد", "تنظیمات با موفقیت ذخیره شد.")


# =========================================================
# تب قالب‌های پیام
# =========================================================
class TemplatesTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self.load_templates()

    def _build_ui(self):
        layout = QHBoxLayout()

        left = QVBoxLayout()
        left.addWidget(QLabel("قالب‌های پیام:"))
        self.list_table = make_table(["عنوان"])
        self.list_table.itemClicked.connect(self.on_select)
        left.addWidget(self.list_table)

        right = QVBoxLayout()
        right.addWidget(QLabel("متن قالب (از {نام}، {مبلغ}، {تاریخ}، {شماره_فاکتور}، {نام_فروشگاه} استفاده کنید):"))
        self.content_edit = QTextEdit()
        self.content_edit.setFixedHeight(150)
        right.addWidget(self.content_edit)
        save_btn = QPushButton("💾 ذخیره قالب")
        save_btn.clicked.connect(self.save_template)
        right.addWidget(save_btn)
        right.addStretch()

        layout.addLayout(left, 1)
        layout.addLayout(right, 2)
        self.setLayout(layout)
        self.templates = []
        self.selected_id = None

    def load_templates(self):
        self.templates = cs.get_templates()
        self.list_table.setRowCount(len(self.templates))
        for i, t in enumerate(self.templates):
            self.list_table.setItem(i, 0, QTableWidgetItem(t["Title"]))

    def on_select(self, item):
        row = item.row()
        t = self.templates[row]
        self.selected_id = t["ID"]
        self.content_edit.setPlainText(t["Content"])

    def save_template(self):
        if not self.selected_id:
            QMessageBox.warning(self, "توجه", "اول یک قالب را از لیست انتخاب کنید.")
            return
        t = next(x for x in self.templates if x["ID"] == self.selected_id)
        cs.save_template(self.selected_id, t["Title"], self.content_edit.toPlainText())
        QMessageBox.information(self, "ذخیره شد", "قالب با موفقیت ذخیره شد.")
        self.load_templates()


# =========================================================
# دیالوگ ارسال سریع پیام به یک شخص (از بخش اشخاص هم صدا زده می‌شود)
# =========================================================
class QuickSendDialog(QDialog):
    def __init__(self, person):
        super().__init__()
        self.person = person
        self.setWindowTitle(f"ارسال پیام به: {person.get('FullName', '')}")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedWidth(420)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()

        info = QLabel(
            f"موبایل: {self.person.get('Mobile') or '—'}   |   "
            f"چت بله: {self.person.get('BalehChatId') or '—'}"
        )
        layout.addWidget(info)

        form = QFormLayout()
        self.channel_combo = QComboBox()
        self.channel_combo.addItem("پیامک (SMS)", "SMS")
        self.channel_combo.addItem("بله (Baleh)", "Baleh")

        self.template_combo = QComboBox()
        self.templates = cs.get_templates()
        self.template_combo.addItem("متن آزاد", None)
        for t in self.templates:
            self.template_combo.addItem(t["Title"], t["TemplateKey"])
        self.template_combo.currentIndexChanged.connect(self.on_template_changed)

        form.addRow("کانال ارسال:", self.channel_combo)
        form.addRow("قالب:", self.template_combo)
        layout.addLayout(form)

        self.text_edit = QTextEdit()
        self.text_edit.setFixedHeight(120)
        layout.addWidget(self.text_edit)

        send_btn = QPushButton("📤 ارسال")
        send_btn.clicked.connect(self.send)
        layout.addWidget(send_btn)

        self.setLayout(layout)

    def on_template_changed(self):
        key = self.template_combo.currentData()
        if not key:
            self.text_edit.clear()
            return
        template = next((t for t in self.templates if t["TemplateKey"] == key), None)
        if template:
            ctx = cs.build_context(self.person)
            self.text_edit.setPlainText(cs.render_template(template["Content"], ctx))

    def send(self):
        text = self.text_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "خطا", "متن پیام خالی است.")
            return
        channel = self.channel_combo.currentData()
        template_key = self.template_combo.currentData()

        success, error = cs.send_message_to_person(
            self.person["ID"], channel, text, template_key
        )
        if success:
            QMessageBox.information(self, "موفق", "پیام با موفقیت ارسال شد.")
            self.accept()
        else:
            QMessageBox.critical(self, "خطا در ارسال", error or "خطای نامشخص")


# =========================================================
# تب ارسال دستی (انتخاب شخص از لیست)
# =========================================================
class ManualSendTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self.load_persons()

    def _build_ui(self):
        layout = QVBoxLayout()

        top_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("جستجوی شخص بر اساس نام...")
        self.search_input.textChanged.connect(self.load_persons)
        top_row.addWidget(self.search_input)
        layout.addLayout(top_row)

        self.table = make_table(["نام", "موبایل", "چت بله", ""])
        layout.addWidget(self.table)

        self.setLayout(layout)

    def load_persons(self):
        db = Database()
        like = f"%{self.search_input.text().strip()}%"
        rows = db.fetch_all(
            "SELECT * FROM Persons WHERE IsDeleted=0 AND FullName LIKE ? ORDER BY FullName",
            (like,)
        )
        db.close()
        self.persons = rows
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(r["FullName"] or ""))
            self.table.setItem(i, 1, QTableWidgetItem(r["Mobile"] or ""))
            self.table.setItem(i, 2, QTableWidgetItem(r["BalehChatId"] or ""))
            btn = QPushButton("📱 ارسال پیام")
            btn.clicked.connect(lambda checked, row=r: self.open_send(row))
            self.table.setCellWidget(i, 3, btn)

    def open_send(self, person):
        dlg = QuickSendDialog(person)
        dlg.exec()


# =========================================================
# تب یادآوری دسته‌جمعی اقساط
# =========================================================
class BulkReminderTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel(
            "با زدن دکمه زیر، برای همه‌ی اقساط پرداخت‌نشده، پیام یادآوری (یا سررسیدشده در صورت گذشتن تاریخ)\n"
            "به مشتری مربوطه ارسال می‌شود."
        ))

        row = QHBoxLayout()
        self.channel_combo = QComboBox()
        self.channel_combo.addItem("پیامک (SMS)", "SMS")
        self.channel_combo.addItem("بله (Baleh)", "Baleh")
        send_btn = QPushButton("📤 ارسال یادآوری برای همه اقساط پرداخت‌نشده")
        send_btn.clicked.connect(self.send_bulk)
        row.addWidget(QLabel("کانال:"))
        row.addWidget(self.channel_combo)
        row.addWidget(send_btn)
        layout.addLayout(row)

        self.result_table = make_table(["مشتری", "نتیجه", "خطا"])
        layout.addWidget(self.result_table)

        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.summary_label)

        layout.addStretch()
        self.setLayout(layout)

    def send_bulk(self):
        confirm = QMessageBox.question(
            self, "تأیید",
            "آیا مطمئن هستید؟ برای همه‌ی مشتریان با قسط پرداخت‌نشده پیام ارسال می‌شود.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        channel = self.channel_combo.currentData()
        result = cs.send_bulk_installment_reminders(channel)

        self.result_table.setRowCount(len(result["details"]))
        for i, d in enumerate(result["details"]):
            self.result_table.setItem(i, 0, QTableWidgetItem(d["name"]))
            self.result_table.setItem(i, 1, QTableWidgetItem("✅ ارسال شد" if d["success"] else "❌ ناموفق"))
            self.result_table.setItem(i, 2, QTableWidgetItem(d["error"] or ""))

        self.summary_label.setText(f"موفق: {result['sent']}   |   ناموفق: {result['failed']}")


# =========================================================
# تب تاریخچه پیام‌ها
# =========================================================
class HistoryTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self.load_data()

    def _build_ui(self):
        layout = QVBoxLayout()
        top_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("جستجو بر اساس نام شخص یا متن پیام...")
        self.search_input.textChanged.connect(self.load_data)
        refresh_btn = QPushButton("🔄 بروزرسانی")
        refresh_btn.clicked.connect(self.load_data)
        top_row.addWidget(self.search_input)
        top_row.addWidget(refresh_btn)
        layout.addLayout(top_row)

        self.table = make_table(["شخص", "کانال", "متن پیام", "وضعیت", "خطا", "تاریخ"])
        layout.addWidget(self.table)

        self.setLayout(layout)

    def load_data(self):
        rows = cs.get_message_log(self.search_input.text())
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            channel_fa = "پیامک" if r["Channel"] == "SMS" else "بله"
            status_fa = "✅ موفق" if r["Status"] == "Sent" else "❌ ناموفق"
            self.table.setItem(i, 0, QTableWidgetItem(r["PersonName"] or ""))
            self.table.setItem(i, 1, QTableWidgetItem(channel_fa))
            self.table.setItem(i, 2, QTableWidgetItem(r["MessageText"] or ""))
            self.table.setItem(i, 3, QTableWidgetItem(status_fa))
            self.table.setItem(i, 4, QTableWidgetItem(r["ErrorText"] or ""))
            self.table.setItem(i, 5, QTableWidgetItem(r["ShamsiDate"] or ""))


# =========================================================
# پنجره اصلی
# =========================================================
class CommunicationWindow(QWidget):
    def __init__(self, current_user=None):
        super().__init__()
        self.setWindowTitle("ارتباط با مشتری (پیامک و بله)")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(950, 600)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        tabs = QTabWidget()
        tabs.addTab(SettingsTab(), "⚙️ تنظیمات")
        tabs.addTab(TemplatesTab(), "📝 قالب‌ها")
        tabs.addTab(ManualSendTab(), "📤 ارسال دستی")
        tabs.addTab(BulkReminderTab(), "📅 یادآوری دسته‌جمعی اقساط")
        tabs.addTab(HistoryTab(), "🕘 تاریخچه")
        layout.addWidget(tabs)
        self.setLayout(layout)
