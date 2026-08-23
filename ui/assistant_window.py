# -*- coding: utf-8 -*-
"""پنجره دستیار هوش مصنوعی — چت با دسترسی خواندنی به داده‌های حسابداری"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QLabel, QCheckBox, QTabWidget, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import services.assistant_service as asst


class ChatTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()

        self.history = QTextEdit()
        self.history.setReadOnly(True)
        self.history.setStyleSheet("font-size: 13px;")
        layout.addWidget(self.history)

        # دکمه‌های سؤال پیشنهادی
        suggestions_label = QLabel("سؤال‌های نمونه (روی هرکدام بزن):")
        layout.addWidget(suggestions_label)

        suggestions_row1 = QHBoxLayout()
        suggestions_row2 = QHBoxLayout()
        for i, q in enumerate(asst.SUGGESTED_QUESTIONS):
            btn = QPushButton(q)
            btn.setStyleSheet("font-size: 11px; padding: 4px;")
            btn.clicked.connect(lambda checked, question=q: self.ask(question))
            if i < len(asst.SUGGESTED_QUESTIONS) // 2:
                suggestions_row1.addWidget(btn)
            else:
                suggestions_row2.addWidget(btn)
        layout.addLayout(suggestions_row1)
        layout.addLayout(suggestions_row2)

        input_row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("سؤال خودت را بنویس... مثلاً: فروش امروز چقدر بوده؟")
        self.input.returnPressed.connect(self.on_send)
        send_btn = QPushButton("📤 پرسیدن")
        send_btn.clicked.connect(self.on_send)
        input_row.addWidget(self.input)
        input_row.addWidget(send_btn)
        layout.addLayout(input_row)

        self.setLayout(layout)

        self.append_message(
            "دستیار",
            "سلام! من دستیار هوش مصنوعی این نرم‌افزارم. می‌تونی از داده‌های واقعی حسابداری سؤال بپرسی. "
            "یکی از سؤال‌های نمونه بالا رو بزن یا سؤال خودت رو تایپ کن."
        )

    def on_send(self):
        text = self.input.text().strip()
        if not text:
            return
        self.ask(text)
        self.input.clear()

    def ask(self, question: str):
        self.append_message("شما", question)
        answer = asst.answer_question(question)
        self.append_message("دستیار", answer)

    def append_message(self, sender: str, text: str):
        color = "#0a6" if sender == "دستیار" else "#357"
        self.history.append(f'<b style="color:{color};">{sender}:</b> {text}'.replace("\n", "<br>"))
        self.history.append("")


class SettingsTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self.load_state()

    def _build_ui(self):
        layout = QVBoxLayout()

        info = QLabel(
            "این دستیار فقط به‌صورت خواندنی (Read-Only) به اطلاعات حسابداری دسترسی دارد و "
            "هرگز چیزی را تغییر نمی‌دهد — فقط سؤالات مدیریتی را بر اساس داده‌های واقعی دیتابیس پاسخ می‌دهد.\n\n"
            "قبل از استفاده، باید این دسترسی را صریحاً تأیید کنی:"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self.enable_check = QCheckBox("به دستیار اجازه می‌دهم به‌صورت خواندنی به اطلاعات حسابداری دسترسی داشته باشد")
        self.enable_check.stateChanged.connect(self.on_toggle)
        layout.addWidget(self.enable_check)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.status_label)

        layout.addStretch()
        self.setLayout(layout)

    def load_state(self):
        enabled = asst.is_assistant_enabled()
        self.enable_check.setChecked(enabled)
        self.update_status(enabled)

    def on_toggle(self):
        enabled = self.enable_check.isChecked()
        asst.set_assistant_enabled(enabled, self.current_user["ID"])
        self.update_status(enabled)

    def update_status(self, enabled):
        if enabled:
            self.status_label.setText("✅ دستیار فعال است.")
            self.status_label.setStyleSheet("font-weight: bold; color: #0a6;")
        else:
            self.status_label.setText("❌ دستیار غیرفعال است.")
            self.status_label.setStyleSheet("font-weight: bold; color: #b33;")


class AssistantWindow(QWidget):
    def __init__(self, current_user=None):
        super().__init__()
        self.setWindowTitle("دستیار هوش مصنوعی")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(750, 600)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        tabs = QTabWidget()
        tabs.addTab(ChatTab(), "💬 گفتگو")
        tabs.addTab(SettingsTab(), "⚙️ تنظیمات دسترسی")
        layout.addWidget(tabs)
        self.setLayout(layout)
