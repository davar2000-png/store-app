# -*- coding: utf-8 -*-
"""پنجره مشاهده گزارش رویدادها (Audit Log) — فقط برای مدیر یا کاربر دارای دسترسی audit.view"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt
import sys, os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.audit_service import get_recent_logs


class AuditViewerWindow(QWidget):
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.setWindowTitle("گزارش رویدادها (Audit Log)")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(1000, 600)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout()

        filter_bar = QHBoxLayout()

        self.action_filter = QComboBox()
        self.action_filter.addItem("همه عملیات‌ها", None)
        for action in ["Create", "Update", "Delete", "Recover", "Discard", "Complete"]:
            self.action_filter.addItem(action, action)
        filter_bar.addWidget(QLabel("عملیات:"))
        filter_bar.addWidget(self.action_filter)

        self.table_filter = QLineEdit()
        self.table_filter.setPlaceholderText("نام جدول/بخش (مثلاً SalesInvoices)")
        filter_bar.addWidget(QLabel("جدول:"))
        filter_bar.addWidget(self.table_filter)

        self.user_filter = QLineEdit()
        self.user_filter.setPlaceholderText("شناسه کاربر")
        filter_bar.addWidget(QLabel("کاربر:"))
        filter_bar.addWidget(self.user_filter)

        self.days_filter = QComboBox()
        self.days_filter.addItem("۷ روز اخیر", 7)
        self.days_filter.addItem("۳۰ روز اخیر", 30)
        self.days_filter.addItem("همه", None)
        filter_bar.addWidget(QLabel("بازه:"))
        filter_bar.addWidget(self.days_filter)

        refresh_btn = QPushButton("🔄 بروزرسانی")
        refresh_btn.clicked.connect(self.refresh)
        filter_bar.addWidget(refresh_btn)

        layout.addLayout(filter_bar)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "تاریخ/زمان", "کاربر", "عملیات", "جدول/بخش",
            "شناسه رکورد", "جزئیات", "CorrelationID"
        ])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(
            5, QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.table)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def refresh(self):
        action_type = self.action_filter.currentData()
        table_name = self.table_filter.text().strip() or None

        user_id_text = self.user_filter.text().strip()
        user_id = int(user_id_text) if user_id_text.isdigit() else None

        days = self.days_filter.currentData()
        date_from = (datetime.now() - timedelta(days=days)) if days else None

        try:
            rows = get_recent_logs(
                user_id=user_id,
                action_type=action_type,
                table_name=table_name,
                date_from=date_from,
                limit=200,
            )
        except Exception as e:
            self.status_label.setText(f"خطا در دریافت گزارش: {e}")
            return

        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(str(r.get("ActionDate", ""))))
            self.table.setItem(i, 1, QTableWidgetItem(str(r.get("UserRef", ""))))
            self.table.setItem(i, 2, QTableWidgetItem(str(r.get("ActionType", ""))))
            self.table.setItem(i, 3, QTableWidgetItem(str(r.get("TableName", ""))))
            self.table.setItem(i, 4, QTableWidgetItem(str(r.get("RecordID", ""))))
            self.table.setItem(i, 5, QTableWidgetItem(str(r.get("Details", ""))))
            self.table.setItem(i, 6, QTableWidgetItem(str(r.get("CorrelationID", ""))))

        self.status_label.setText(f"{len(rows)} رکورد نمایش داده شد.")
