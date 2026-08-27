# -*- coding: utf-8 -*-
"""پنجره گزارش‌ها — فروش، خرید، سود، سود و زیان خالص، موجودی، بدهکاران/بستانکاران، چک‌ها، اقساط"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QComboBox, QTabWidget, QHeaderView,
    QGridLayout, QFrame, QMessageBox, QDialog
)
from PyQt6.QtCore import Qt
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.persian_date import today_shamsi_str
from database.db import Database
import services.reports_service as rs


def fmt(n):
    try:
        return f"{float(n):,.0f}"
    except Exception:
        return str(n or "")


def first_day_of_year_str():
    y = today_shamsi_str().split("/")[0]
    return f"{y}/01/01"


def make_table(headers):
    table = QTableWidget()
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    return table


def fill_table(table, rows, keys, formatters=None):
    formatters = formatters or {}
    table.setRowCount(len(rows))
    for i, r in enumerate(rows):
        for j, k in enumerate(keys):
            val = r.get(k, "")
            if k in formatters:
                val = formatters[k](val)
            table.setItem(i, j, QTableWidgetItem(str(val if val is not None else "")))


# =========================================================
# تب فروش
# =========================================================
class SalesReportTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self.load_customers()
        self.run_report()

    def _build_ui(self):
        layout = QVBoxLayout()
        filter_row = QHBoxLayout()

        self.from_input = QLineEdit(first_day_of_year_str())
        self.to_input = QLineEdit(today_shamsi_str())
        self.customer_combo = QComboBox()
        run_btn = QPushButton("🔍 اجرای گزارش")
        run_btn.clicked.connect(self.run_report)

        filter_row.addWidget(QLabel("از تاریخ:"))
        filter_row.addWidget(self.from_input)
        filter_row.addWidget(QLabel("تا تاریخ:"))
        filter_row.addWidget(self.to_input)
        filter_row.addWidget(QLabel("مشتری:"))
        filter_row.addWidget(self.customer_combo)
        filter_row.addWidget(run_btn)
        layout.addLayout(filter_row)

        self.table = make_table(["شماره فاکتور", "تاریخ", "مشتری", "جمع کل", "تخفیف", "قابل پرداخت", "دریافت‌شده"])
        layout.addWidget(self.table)

        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.summary_label)

        self.setLayout(layout)

    def load_customers(self):
        db = Database()
        customers = db.fetch_all("SELECT ID, FullName FROM Persons WHERE IsCustomer=1 AND IsDeleted=0 ORDER BY FullName")
        db.close()
        self.customer_combo.addItem("همه مشتریان", None)
        for c in customers:
            self.customer_combo.addItem(c["FullName"], c["ID"])

    def run_report(self):
        customer_id = self.customer_combo.currentData()
        rows, totals = rs.sales_report(self.from_input.text().strip(), self.to_input.text().strip(), customer_id)
        fill_table(
            self.table, rows,
            ["InvoiceNumber", "ShamsiDate", "CustomerName", "TotalAmount", "DiscountAmount", "PayableAmount", "PaidAmount"],
            {"TotalAmount": fmt, "DiscountAmount": fmt, "PayableAmount": fmt, "PaidAmount": fmt}
        )
        self.summary_label.setText(
            f"تعداد فاکتور: {totals['count']}   |   جمع کل: {fmt(totals['total_amount'])}   |   "
            f"تخفیف: {fmt(totals['discount'])}   |   قابل پرداخت: {fmt(totals['payable'])}   |   دریافت‌شده: {fmt(totals['paid'])}"
        )


# =========================================================
# تب خرید
# =========================================================
class PurchaseReportTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self.load_suppliers()
        self.run_report()

    def _build_ui(self):
        layout = QVBoxLayout()
        filter_row = QHBoxLayout()

        self.from_input = QLineEdit(first_day_of_year_str())
        self.to_input = QLineEdit(today_shamsi_str())
        self.supplier_combo = QComboBox()
        run_btn = QPushButton("🔍 اجرای گزارش")
        run_btn.clicked.connect(self.run_report)

        filter_row.addWidget(QLabel("از تاریخ:"))
        filter_row.addWidget(self.from_input)
        filter_row.addWidget(QLabel("تا تاریخ:"))
        filter_row.addWidget(self.to_input)
        filter_row.addWidget(QLabel("فروشنده:"))
        filter_row.addWidget(self.supplier_combo)
        filter_row.addWidget(run_btn)
        layout.addLayout(filter_row)

        self.table = make_table(["شماره فاکتور", "تاریخ", "فروشنده", "جمع کل", "تخفیف", "قابل پرداخت", "پرداخت‌شده"])
        layout.addWidget(self.table)

        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.summary_label)

        self.setLayout(layout)

    def load_suppliers(self):
        db = Database()
        suppliers = db.fetch_all("SELECT ID, FullName FROM Persons WHERE IsSeller=1 AND IsDeleted=0 ORDER BY FullName")
        db.close()
        self.supplier_combo.addItem("همه فروشندگان", None)
        for s in suppliers:
            self.supplier_combo.addItem(s["FullName"], s["ID"])

    def run_report(self):
        supplier_id = self.supplier_combo.currentData()
        rows, totals = rs.purchase_report(self.from_input.text().strip(), self.to_input.text().strip(), supplier_id)
        fill_table(
            self.table, rows,
            ["InvoiceNumber", "ShamsiDate", "SupplierName", "TotalAmount", "DiscountAmount", "PayableAmount", "PaidAmount"],
            {"TotalAmount": fmt, "DiscountAmount": fmt, "PayableAmount": fmt, "PaidAmount": fmt}
        )
        self.summary_label.setText(
            f"تعداد فاکتور: {totals['count']}   |   جمع کل: {fmt(totals['total_amount'])}   |   "
            f"قابل پرداخت: {fmt(totals['payable'])}   |   پرداخت‌شده: {fmt(totals['paid'])}"
        )


# =========================================================
# تب سود
# =========================================================
class ProfitReportTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self.run_report()

    def _build_ui(self):
        layout = QVBoxLayout()
        filter_row = QHBoxLayout()

        self.from_input = QLineEdit(first_day_of_year_str())
        self.to_input = QLineEdit(today_shamsi_str())
        self.group_combo = QComboBox()
        self.group_combo.addItem("بر اساس فاکتور", "invoice")
        self.group_combo.addItem("بر اساس کالا", "product")
        self.group_combo.addItem("بر اساس مشتری", "customer")
        run_btn = QPushButton("🔍 اجرای گزارش")
        run_btn.clicked.connect(self.run_report)

        filter_row.addWidget(QLabel("از تاریخ:"))
        filter_row.addWidget(self.from_input)
        filter_row.addWidget(QLabel("تا تاریخ:"))
        filter_row.addWidget(self.to_input)
        filter_row.addWidget(QLabel("گروه‌بندی:"))
        filter_row.addWidget(self.group_combo)
        filter_row.addWidget(run_btn)
        layout.addLayout(filter_row)

        self.table = make_table(["عنوان", "تعداد/تاریخ", "جمع فروش", "بهای تمام‌شده", "سود"])
        layout.addWidget(self.table)

        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(self.summary_label)

        self.setLayout(layout)

    def run_report(self):
        group_by = self.group_combo.currentData()
        rows, totals = rs.profit_report(self.from_input.text().strip(), self.to_input.text().strip(), group_by)

        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            if group_by == "product":
                title = r["ProductName"]
                sub = f"{fmt(r['TotalQty'])} عدد"
            elif group_by == "customer":
                title = r["CustomerName"]
                sub = ""
            else:
                title = f"فاکتور {r['InvoiceNumber']}"
                sub = f"{r['ShamsiDate']} - {r['CustomerName']}"

            self.table.setItem(i, 0, QTableWidgetItem(title or ""))
            self.table.setItem(i, 1, QTableWidgetItem(sub))
            self.table.setItem(i, 2, QTableWidgetItem(fmt(r["TotalSale"])))
            self.table.setItem(i, 3, QTableWidgetItem(fmt(r["TotalCost"])))
            self.table.setItem(i, 4, QTableWidgetItem(fmt(r["Profit"])))

        self.summary_label.setText(
            f"جمع فروش: {fmt(totals['total_sale'])}   |   جمع بهای تمام‌شده: {fmt(totals['total_cost'])}   |   "
            f"جمع سود: {fmt(totals['total_profit'])}"
        )


# =========================================================
# تب سود و زیان خالص
# =========================================================
class NetProfitLossTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self.run_report()

    def _build_ui(self):
        layout = QVBoxLayout()
        filter_row = QHBoxLayout()

        self.from_input = QLineEdit(first_day_of_year_str())
        self.to_input = QLineEdit(today_shamsi_str())
        run_btn = QPushButton("🔍 اجرای گزارش")
        run_btn.clicked.connect(self.run_report)

        filter_row.addWidget(QLabel("از تاریخ:"))
        filter_row.addWidget(self.from_input)
        filter_row.addWidget(QLabel("تا تاریخ:"))
        filter_row.addWidget(self.to_input)
        filter_row.addWidget(run_btn)
        filter_row.addStretch()
        layout.addLayout(filter_row)

        grid = QGridLayout()
        self.rows_labels = {}
        items = [
            ("revenue", "فروش (قابل‌پرداخت فاکتورها)"),
            ("sales_discount", "تخفیفات فروش"),
            ("cogs", "بهای تمام‌شده کالای فروش‌رفته"),
            ("gross_profit", "سود ناخالص"),
            ("operating_expenses", "هزینه‌های عملیاتی (در توسعه بعدی)"),
            ("net_profit", "سود خالص"),
        ]
        for row_idx, (key, label) in enumerate(items):
            lbl = QLabel(label)
            val = QLabel("0")
            val.setStyleSheet("font-weight: bold;")
            if key == "net_profit":
                lbl.setStyleSheet("font-weight: bold; font-size: 15px;")
                val.setStyleSheet("font-weight: bold; font-size: 15px; color: #0a6;")
            grid.addWidget(lbl, row_idx, 0)
            grid.addWidget(val, row_idx, 1)
            self.rows_labels[key] = val

        layout.addLayout(grid)
        layout.addStretch()
        self.setLayout(layout)

    def run_report(self):
        data = rs.net_profit_loss_report(self.from_input.text().strip(), self.to_input.text().strip())
        for key, lbl in self.rows_labels.items():
            lbl.setText(fmt(data.get(key, 0)))


# =========================================================
# تب موجودی
# =========================================================
class InventoryReportTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self.run_report()

    def _build_ui(self):
        layout = QVBoxLayout()
        filter_row = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("جستجو بر اساس نام یا کد کالا...")
        run_btn = QPushButton("🔍 اجرای گزارش")
        run_btn.clicked.connect(self.run_report)
        stagnant_btn = QPushButton("📦 کالاهای راکد")
        stagnant_btn.clicked.connect(self.show_stagnant)

        filter_row.addWidget(self.search_input)
        filter_row.addWidget(run_btn)
        filter_row.addWidget(stagnant_btn)
        layout.addLayout(filter_row)

        self.table = make_table(["کالا", "کد", "گروه", "برند", "موجودی", "ارزش ریالی", "وضعیت"])
        layout.addWidget(self.table)

        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.summary_label)

        self.setLayout(layout)

    def run_report(self):
        rows, totals = rs.inventory_report(self.search_input.text())
        fill_table(
            self.table, rows,
            ["Name", "Code", "GroupName", "Brand", "CurrentStock", "StockValue", "Status"],
            {"CurrentStock": fmt, "StockValue": fmt}
        )
        self.summary_label.setText(
            f"تعداد کالا: {totals['count']}   |   جمع موجودی تعدادی: {fmt(totals['total_qty'])}   |   "
            f"جمع ارزش ریالی: {fmt(totals['total_value'])}   |   کمبوددار: {totals['low_stock_count']}   |   "
            f"بدون موجودی: {totals['zero_stock_count']}"
        )

    def show_stagnant(self):
        rows = rs.stagnant_products_report()
        dlg = QDialog(self)
        dlg.setWindowTitle("کالاهای راکد (بدون فروش)")
        dlg.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        dlg.resize(500, 400)
        v = QVBoxLayout()
        t = make_table(["کالا", "کد", "موجودی فعلی"])
        fill_table(t, rows, ["Name", "Code", "CurrentStock"], {"CurrentStock": fmt})
        v.addWidget(QLabel(f"{len(rows)} کالا تاکنون هیچ فروشی نداشته‌اند:"))
        v.addWidget(t)
        dlg.setLayout(v)
        dlg.exec()


# =========================================================
# تب بدهکاران و بستانکاران
# =========================================================
class DebtorsCreditorsTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self.run_report()

    def _build_ui(self):
        layout = QHBoxLayout()

        left = QVBoxLayout()
        left.addWidget(QLabel("👥 بدهکاران (مشتریانی که به فروشگاه بدهکارند)"))
        self.debtors_table = make_table(["مشتری", "بدهی"])
        left.addWidget(self.debtors_table)
        self.debtors_total = QLabel("")
        self.debtors_total.setStyleSheet("font-weight: bold;")
        left.addWidget(self.debtors_total)

        right = QVBoxLayout()
        right.addWidget(QLabel("🏭 بستانکاران (تأمین‌کنندگانی که فروشگاه به آن‌ها بدهکار است)"))
        self.creditors_table = make_table(["فروشنده", "بستانکاری"])
        right.addWidget(self.creditors_table)
        self.creditors_total = QLabel("")
        self.creditors_total.setStyleSheet("font-weight: bold;")
        right.addWidget(self.creditors_total)

        refresh_btn = QPushButton("🔄 بروزرسانی")
        refresh_btn.clicked.connect(self.run_report)

        main_v = QVBoxLayout()
        main_v.addWidget(refresh_btn)
        h = QHBoxLayout()
        h.addLayout(left)
        h.addLayout(right)
        main_v.addLayout(h)
        self.setLayout(main_v)

    def run_report(self):
        debtors, total_debt = rs.debtors_report()
        fill_table(self.debtors_table, debtors, ["FullName", "Debt"], {"Debt": fmt})
        self.debtors_total.setText(f"جمع کل بدهی مشتریان: {fmt(total_debt)}")

        creditors, total_credit = rs.creditors_report()
        fill_table(self.creditors_table, creditors, ["FullName", "Credit"], {"Credit": fmt})
        self.creditors_total.setText(f"جمع کل بستانکاری فروشندگان: {fmt(total_credit)}")


# =========================================================
# تب چک‌ها
# =========================================================
class ChequesReportTab(QWidget):
    STATUS_FA = {
        "InHand": "نزد ما", "Deposited": "واگذارشده به بانک",
        "Cashed": "وصول‌شده", "Bounced": "برگشتی", "Returned": "عودت‌شده"
    }

    def __init__(self):
        super().__init__()
        self._build_ui()
        self.run_report()

    def _build_ui(self):
        layout = QVBoxLayout()
        filter_row = QHBoxLayout()

        self.type_combo = QComboBox()
        self.type_combo.addItem("همه", None)
        self.type_combo.addItem("دریافتی", "Received")
        self.type_combo.addItem("پرداختی", "Issued")

        self.status_combo = QComboBox()
        self.status_combo.addItem("همه وضعیت‌ها", None)
        for key, fa in self.STATUS_FA.items():
            self.status_combo.addItem(fa, key)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("جستجو بر اساس شماره چک یا شخص...")

        run_btn = QPushButton("🔍 اجرای گزارش")
        run_btn.clicked.connect(self.run_report)

        filter_row.addWidget(QLabel("نوع:"))
        filter_row.addWidget(self.type_combo)
        filter_row.addWidget(QLabel("وضعیت:"))
        filter_row.addWidget(self.status_combo)
        filter_row.addWidget(self.search_input)
        filter_row.addWidget(run_btn)
        layout.addLayout(filter_row)

        self.table = make_table(["نوع", "شماره چک", "بانک", "شخص", "مبلغ", "تاریخ", "سررسید", "وضعیت"])
        layout.addWidget(self.table)

        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.summary_label)

        self.setLayout(layout)

    def run_report(self):
        cheque_type = self.type_combo.currentData()
        status = self.status_combo.currentData()
        rows, total = rs.cheques_report(cheque_type, status, self.search_input.text())

        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            type_fa = "دریافتی" if r["ChequeType"] == "Received" else "پرداختی"
            status_fa = self.STATUS_FA.get(r["Status"], r["Status"])
            self.table.setItem(i, 0, QTableWidgetItem(type_fa))
            self.table.setItem(i, 1, QTableWidgetItem(r["ChequeNumber"] or ""))
            self.table.setItem(i, 2, QTableWidgetItem(r["BankName"] or ""))
            self.table.setItem(i, 3, QTableWidgetItem(r["PersonName"] or ""))
            self.table.setItem(i, 4, QTableWidgetItem(fmt(r["Amount"])))
            self.table.setItem(i, 5, QTableWidgetItem(r["ShamsiDate"] or ""))
            self.table.setItem(i, 6, QTableWidgetItem(r["DueShamsiDate"] or ""))
            self.table.setItem(i, 7, QTableWidgetItem(status_fa))

        self.summary_label.setText(f"تعداد: {len(rows)}   |   جمع مبلغ: {fmt(total)}")


# =========================================================
# تب اقساط
# =========================================================
class InstallmentsReportTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self.run_report()

    def _build_ui(self):
        layout = QVBoxLayout()
        filter_row = QHBoxLayout()

        self.status_combo = QComboBox()
        self.status_combo.addItem("همه", None)
        self.status_combo.addItem("پرداخت‌نشده", "Pending")
        self.status_combo.addItem("پرداخت‌شده", "Paid")
        run_btn = QPushButton("🔍 اجرای گزارش")
        run_btn.clicked.connect(self.run_report)

        filter_row.addWidget(QLabel("وضعیت:"))
        filter_row.addWidget(self.status_combo)
        filter_row.addWidget(run_btn)
        filter_row.addStretch()
        layout.addLayout(filter_row)

        self.table = make_table(["مشتری", "شماره قسط", "سررسید", "مبلغ", "وضعیت", "تاریخ پرداخت"])
        layout.addWidget(self.table)

        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.summary_label)

        self.setLayout(layout)

    def run_report(self):
        status = self.status_combo.currentData()
        rows, total = rs.installments_report(status)
        status_fa = {"Pending": "پرداخت‌نشده", "Paid": "پرداخت‌شده"}

        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(r["CustomerName"] or ""))
            self.table.setItem(i, 1, QTableWidgetItem(str(r["SeqNumber"])))
            self.table.setItem(i, 2, QTableWidgetItem(r["DueShamsiDate"] or ""))
            self.table.setItem(i, 3, QTableWidgetItem(fmt(r["Amount"])))
            self.table.setItem(i, 4, QTableWidgetItem(status_fa.get(r["Status"], r["Status"])))
            self.table.setItem(i, 5, QTableWidgetItem(r["PaidShamsiDate"] or ""))

        self.summary_label.setText(f"تعداد قسط: {len(rows)}   |   جمع مبلغ: {fmt(total)}")


# =========================================================
# پنجره اصلی گزارش‌ها
# =========================================================
class ReportsWindow(QWidget):
    def __init__(self, current_user=None):
        super().__init__()
        self.setWindowTitle("گزارش‌ها")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(1000, 650)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        tabs = QTabWidget()

        tabs.addTab(SalesReportTab(), "💰 فروش")
        tabs.addTab(PurchaseReportTab(), "🛒 خرید")
        tabs.addTab(ProfitReportTab(), "📈 سود")
        tabs.addTab(NetProfitLossTab(), "📊 سود و زیان خالص")
        tabs.addTab(InventoryReportTab(), "📦 موجودی")
        tabs.addTab(DebtorsCreditorsTab(), "👥 بدهکاران/بستانکاران")
        tabs.addTab(ChequesReportTab(), "📑 چک‌ها")
        tabs.addTab(InstallmentsReportTab(), "📅 اقساط")

        layout.addWidget(tabs)
        self.setLayout(layout)
