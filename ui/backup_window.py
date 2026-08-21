# -*- coding: utf-8 -*-
"""پنجره پشتیبان‌گیری و بازیابی اطلاعات"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QMessageBox, QLineEdit, QApplication
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor
import sys, os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.backup_service import (
    create_backup, restore_backup, verify_backup_file, suggest_backup_folder, BackupError
)
from utils.persian_date import today_shamsi_str


class BackupWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("پشتیبان‌گیری و بازیابی اطلاعات")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(620, 420)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(18)

        # بخش تهیه نسخه پشتیبان
        backup_box = QVBoxLayout()
        backup_title = QLabel("💾 تهیه نسخه پشتیبان")
        backup_title.setStyleSheet("font-size: 15px; font-weight: bold;")
        backup_box.addWidget(backup_title)
        backup_desc = QLabel(
            "یک فایل کامل از تمام اطلاعات دیتابیس (اشخاص، کالا، فاکتورها، چک‌ها، اقساط،\n"
            "صندوق/بانک و تنظیمات) می‌سازد.\n"
            "توصیه می‌شود این کار را هفته‌ای حداقل یک‌بار انجام دهید و فایل را در یک\n"
            "فلش مموری یا هارد دیگر هم نگه دارید."
        )
        backup_desc.setWordWrap(True)
        backup_box.addWidget(backup_desc)

        backup_btn = QPushButton("📥 تهیه نسخه پشتیبان جدید")
        backup_btn.setFixedHeight(42)
        backup_btn.clicked.connect(self.do_backup)
        backup_box.addWidget(backup_btn)
        layout.addLayout(backup_box)

        # خط جداکننده
        sep = QLabel("─" * 60)
        sep.setStyleSheet("color: #ccc;")
        layout.addWidget(sep)

        # بخش بازیابی
        restore_box = QVBoxLayout()
        restore_title = QLabel("♻️ بازیابی کلیه اطلاعات از نسخه پشتیبان")
        restore_title.setStyleSheet("font-size: 15px; font-weight: bold;")
        restore_box.addWidget(restore_title)
        restore_desc = QLabel(
            "می‌توانید یک فایل بک‌آپ (.bak) را — چه از همین کامپیوتر و چه از کامپیوتر یا\n"
            "SQL Server دیگری — انتخاب کنید تا کل اطلاعات نرم‌افزار با آن جایگزین شود.\n"
            "این کار حتی روی یک کامپیوتر کاملاً تازه (بعد از نصب مجدد ویندوز/برنامه) هم کار می‌کند.\n\n"
            "⚠️ هشدار: با انجام این کار، تمام اطلاعات فعلی نرم‌افزار پاک و با اطلاعات\n"
            "داخل فایل پشتیبان جایگزین می‌شود و قابل بازگشت نیست."
        )
        restore_desc.setWordWrap(True)
        restore_desc.setStyleSheet("color: #b33;")
        restore_box.addWidget(restore_desc)

        restore_btn = QPushButton("📤 انتخاب فایل و بازیابی کلیه اطلاعات")
        restore_btn.setFixedHeight(42)
        restore_btn.clicked.connect(self.do_restore)
        restore_box.addWidget(restore_btn)
        layout.addLayout(restore_box)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #555;")
        layout.addWidget(self.status_label)

        layout.addStretch()
        self.setLayout(layout)

    def _suggested_dir(self, default_filename=""):
        """پوشه‌ی پیشنهادی امن (که خود SQL Server هم به آن دسترسی دارد) را برای دیالوگ برمی‌گرداند"""
        try:
            folder = suggest_backup_folder()
            return os.path.join(folder, default_filename) if default_filename else folder
        except Exception:
            return default_filename

    def _set_busy(self, busy: bool, message: str = ""):
        self.status_label.setText(message)
        QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor)) if busy \
            else QApplication.restoreOverrideCursor()
        QApplication.processEvents()

    def do_backup(self):
        default_name = f"StoreAppDB_Backup_{today_shamsi_str().replace('/', '-')}.bak"
        start_path = self._suggested_dir(default_name)
        file_path, _ = QFileDialog.getSaveFileName(
            self, "ذخیره نسخه پشتیبان", start_path, "SQL Server Backup (*.bak)"
        )
        if not file_path:
            return

        self._set_busy(True, "در حال تهیه نسخه پشتیبان...")
        try:
            create_backup(file_path)
            self._set_busy(False)
            QMessageBox.information(
                self, "موفق",
                f"نسخه پشتیبان با موفقیت در مسیر زیر ذخیره شد:\n{file_path}\n\n"
                "پیشنهاد: این فایل را در یک فلش مموری یا فضای ابری هم کپی نگه دارید."
            )
        except BackupError as e:
            self._set_busy(False)
            QMessageBox.critical(self, "خطا", str(e))

    def do_restore(self):
        start_dir = self._suggested_dir()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "انتخاب فایل پشتیبان", start_dir, "SQL Server Backup (*.bak)"
        )
        if not file_path:
            return

        self._set_busy(True, "در حال بررسی فایل پشتیبان...")
        try:
            info = verify_backup_file(file_path)
        except BackupError as e:
            self._set_busy(False)
            QMessageBox.critical(self, "خطا", str(e))
            return
        self._set_busy(False)

        confirm = QMessageBox.warning(
            self, "تأیید نهایی",
            f"این فایل متعلق به دیتابیس «{info['database_name']}» است "
            f"(تاریخ تهیه: {info['backup_date']}).\n\n"
            "با ادامه، تمام اطلاعات فعلی نرم‌افزار پاک و با کلیه اطلاعات داخل این فایل\n"
            "جایگزین می‌شود. آیا مطمئن هستید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        def on_progress(msg):
            self.status_label.setText(msg)
            QApplication.processEvents()

        self._set_busy(True, "در حال شروع بازیابی...")
        try:
            restore_backup(file_path, progress_cb=on_progress)
            self._set_busy(False, "بازیابی با موفقیت انجام شد.")
            QMessageBox.information(
                self, "موفق",
                "بازیابی کلیه اطلاعات با موفقیت انجام شد.\nبرنامه را ببندید و دوباره باز کنید."
            )
        except BackupError as e:
            self._set_busy(False, "")
            QMessageBox.critical(self, "خطا", str(e))
