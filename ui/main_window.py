# -*- coding: utf-8 -*-
"""پنجره اصلی (داشبورد) نرم‌افزار"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGridLayout, QFrame
)
from PyQt6.QtCore import Qt
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.persian_date import today_shamsi_str
from ui.persons_window import PersonsWindow
from ui.products_window import ProductsWindow
from ui.purchase_window import PurchaseInvoicesWindow
from ui.purchase_return_window import PurchaseReturnInvoicesWindow
from ui.invoices_list_window import AllInvoicesWindow
from ui.sales_window import SalesInvoicesWindow
from ui.cashbox_bank_window import CashBoxBankWindow
from ui.receipt_window import ReceiptsWindow
from ui.payment_window import PaymentsWindow
from ui.cheques_window import ChequesWindow
from ui.installments_window import InstallmentsWindow
from ui.reports_window import ReportsWindow
from ui.communication_window import CommunicationWindow
from ui.import_window import ImportWindow
from ui.backup_window import BackupWindow
from ui.assistant_window import AssistantWindow
from ui.settings_window import SettingsWindow
from services.inventory_service import get_low_stock_products
import services.settings_service as ss


class MainWindow(QMainWindow):
    def __init__(self, current_user, session_id=None):
        super().__init__()
        self.current_user = current_user
        self.session_id = session_id  # (Phase 13.2) Session جاری، برای انتقال به فرم‌های دارای Draft/AutoSave
        self.setWindowTitle("نرم‌افزار حسابداری فروشگاه موبایل، لپ‌تاپ و کنسول بازی")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(950, 620)
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # نوار بالا: خوش‌آمد + تاریخ
        top_bar = QHBoxLayout()
        welcome = QLabel(f"خوش آمدید، {self.current_user['FullName']}")
        welcome.setStyleSheet("font-size: 15px; font-weight: bold;")
        date_label = QLabel(f"تاریخ امروز: {today_shamsi_str()}")
        top_bar.addWidget(welcome)
        top_bar.addStretch()
        top_bar.addWidget(date_label)
        main_layout.addLayout(top_bar)

        # هشدار نقطه سفارش (در صورت وجود کالای کمتر از حد مجاز)
        self.low_stock_label = QLabel("")
        self.low_stock_label.setStyleSheet(
            "color: #b30000; font-weight: bold; background-color: #ffe8e8; padding: 8px; border-radius: 4px;"
        )
        self.low_stock_label.setVisible(False)
        main_layout.addWidget(self.low_stock_label)
        self.refresh_low_stock_warning()

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        main_layout.addWidget(line)

        # شبکه دکمه‌های ماژول‌ها (مراحل بعدی تکمیل می‌شوند)
        grid = QGridLayout()
        grid.setSpacing(14)

        # هر ماژول: (متن دکمه، تابع بازکننده، کلید دسترسی یا None برای بخش‌های بدون کنترل دسترسی)
        modules = [
            ("👤 اشخاص", self.open_persons, "ModulePersons"),
            ("📦 کالاها", self.open_products, "ModuleProducts"),
            ("📋 لیست فاکتورها", self.open_all_invoices, "ModuleInvoicesList"),
            ("🛒 خرید", self.open_purchases, "ModulePurchases"),
            ("💰 فروش", self.open_sales, "ModuleSales"),
            ("↩️ برگشت از خرید", self.open_purchase_returns, "ModulePurchaseReturns"),
            ("↩️ برگشت از فروش", self.not_ready, None),
            ("📄 پیش‌فاکتور", self.not_ready, None),
            ("💵 صندوق و بانک", self.open_cashbox_bank, "ModuleCashBoxBank"),
            ("⬇️ دریافت", self.open_receipts, "ModuleReceipts"),
            ("⬆️ پرداخت", self.open_payments, "ModulePayments"),
            ("📑 چک‌ها", self.open_cheques, "ModuleCheques"),
            ("📅 اقساط", self.open_installments, "ModuleInstallments"),
            ("📊 گزارش‌ها", self.open_reports, "ModuleReports"),
            ("📱 ارتباط با مشتری", self.open_communication, "ModuleCommunication"),
            ("📥 Import از ربات", self.open_import, "ModuleImport"),
            ("🗄️ پشتیبان‌گیری", self.open_backup, "ModuleBackup"),
            ("🤖 دستیار هوش مصنوعی", self.open_assistant, "ModuleAssistant"),
            ("⚙️ تنظیمات", self.open_settings, "__AdminOnly__"),  # فقط مدیر سیستم
        ]

        row, col = 0, 0
        for text, handler, perm_key in modules:
            if perm_key == "__AdminOnly__" and not self.current_user.get("IsAdmin"):
                continue  # فقط مدیر سیستم این دکمه را می‌بیند
            if perm_key and perm_key != "__AdminOnly__" and not ss.is_module_allowed(self.current_user, perm_key):
                continue  # کاربر به این بخش دسترسی ندارد؛ دکمه اصلاً نمایش داده نمی‌شود
            btn = QPushButton(text)
            btn.setFixedSize(180, 80)
            btn.setStyleSheet("font-size: 13px;")
            btn.clicked.connect(handler)
            grid.addWidget(btn, row, col)
            col += 1
            if col > 3:
                col = 0
                row += 1

        main_layout.addLayout(grid)
        main_layout.addStretch()

        central.setLayout(main_layout)
        self.setCentralWidget(central)

    def refresh_low_stock_warning(self):
        try:
            low_stock = get_low_stock_products()
        except Exception:
            low_stock = []
        if low_stock:
            names = "، ".join(p["Name"] for p in low_stock[:5])
            more = f" و {len(low_stock) - 5} کالای دیگر" if len(low_stock) > 5 else ""
            self.low_stock_label.setText(f"⚠️ نقطه سفارش: {names}{more} به موجودی هشدار رسیده‌اند.")
            self.low_stock_label.setVisible(True)
        else:
            self.low_stock_label.setVisible(False)

    def open_persons(self):
        self.persons_win = PersonsWindow()
        self.persons_win.show()

    def open_products(self):
        self.products_win = ProductsWindow()
        self.products_win.show()

    def open_all_invoices(self):
        self.all_invoices_win = AllInvoicesWindow(self.current_user)
        self.all_invoices_win.show()

    def open_purchases(self):
        self.purchases_win = PurchaseInvoicesWindow(self.current_user, session_id=self.session_id)
        self.purchases_win.show()

    def open_sales(self):
        self.sales_win = SalesInvoicesWindow(self.current_user)
        self.sales_win.show()

    def open_purchase_returns(self):
        self.purchase_returns_win = PurchaseReturnInvoicesWindow(self.current_user)
        self.purchase_returns_win.show()

    def open_cashbox_bank(self):
        self.cashbox_bank_win = CashBoxBankWindow(self.current_user)
        self.cashbox_bank_win.show()

    def open_receipts(self):
        self.receipts_win = ReceiptsWindow(self.current_user)
        self.receipts_win.show()

    def open_payments(self):
        self.payments_win = PaymentsWindow(self.current_user)
        self.payments_win.show()

    def open_cheques(self):
        self.cheques_win = ChequesWindow(self.current_user)
        self.cheques_win.show()

    def open_installments(self):
        self.installments_win = InstallmentsWindow(self.current_user)
        self.installments_win.show()

    def open_reports(self):
        self.reports_win = ReportsWindow(self.current_user)
        self.reports_win.show()

    def open_communication(self):
        self.communication_win = CommunicationWindow(self.current_user)
        self.communication_win.show()

    def open_import(self):
        self.import_win = ImportWindow()
        self.import_win.show()

    def open_backup(self):
        self.backup_win = BackupWindow()
        self.backup_win.show()

    def open_assistant(self):
        self.assistant_win = AssistantWindow(self.current_user)
        self.assistant_win.show()

    def not_ready(self):
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "به زودی",
                                 "این بخش در مراحل بعدی ساخته می‌شود.")

    def open_settings(self):
        from PyQt6.QtWidgets import QMessageBox
        if not self.current_user.get("IsAdmin"):
            QMessageBox.warning(self, "دسترسی غیرمجاز",
                                 "فقط مدیر سیستم به بخش تنظیمات دسترسی دارد.")
            return
        self.settings_win = SettingsWindow(self.current_user)
        self.settings_win.show()
