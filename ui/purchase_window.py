# -*- coding: utf-8 -*-
"""مدیریت خرید: لیست فاکتورهای خرید + ثبت فاکتور خرید جدید (با FIFO و سریال/IMEI)"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QDialog, QFormLayout, QComboBox,
    QDoubleSpinBox, QMessageBox, QHeaderView, QTextEdit
)
from PyQt6.QtCore import Qt, QTimer
import sys, os, logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.persian_date import today_shamsi_str
from services.inventory_service import (
    get_suppliers, get_purchase_invoices, get_invoice_items,
    create_purchase_invoice, InventoryError
)
from services import draft_service
from ui.product_picker_dialog import ProductPickerDialog
from ui.serial_entry_dialog import SerialEntryDialog

logger = logging.getLogger(__name__)


class NewPurchaseInvoiceDialog(QDialog):
    """فرم ثبت فاکتور خرید جدید"""

    DRAFT_FORM_TYPE = "PurchaseInvoice"  # (Phase 13.2) نوع Draft برای این فرم

    def __init__(self, current_user, session_id=None):
        super().__init__()
        self.current_user = current_user
        self.session_id = session_id  # (Phase 13.2) برای مرتبط‌کردن Draft به Session جاری
        self.items = []   # هر عنصر: دیکشنری با اطلاعات کالا و سریال‌ها
        self.draft_id = None  # (Phase 13.2) شناسه Draft فعال این فرم (در صورت وجود)
        self.setWindowTitle("ثبت فاکتور خرید جدید")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(750, 560)
        self._build_ui()
        self.load_suppliers()

        # (Phase 13.2) بررسی وجود Draft قبلی و پرسش از کاربر برای بازیابی
        self._check_for_existing_draft()

        # (Phase 13.2) شروع AutoSave دوره‌ای (تقریباً هر ۶۰ ثانیه)، بدون قفل‌کردن UI
        self.autosave_timer = QTimer(self)
        self.autosave_timer.setInterval(60000)
        self.autosave_timer.timeout.connect(self.autosave)
        self.autosave_timer.start()
        # با بسته‌شدن دیالوگ (از هر مسیری: تایید/انصراف/دکمه X) تایمر متوقف شود
        self.finished.connect(lambda _result=None: self.autosave_timer.stop())

    def _build_ui(self):
        layout = QVBoxLayout()

        form = QFormLayout()
        self.supplier_combo = QComboBox()
        self.date_label = QLabel(today_shamsi_str())
        self.discount_input = QDoubleSpinBox()
        self.discount_input.setMaximum(999999999)
        self.discount_input.setGroupSeparatorShown(True)
        self.tax_input = QDoubleSpinBox()
        self.tax_input.setMaximum(999999999)
        self.tax_input.setGroupSeparatorShown(True)
        self.description_input = QTextEdit()
        self.description_input.setFixedHeight(50)

        form.addRow("فروشنده/تأمین‌کننده:", self.supplier_combo)
        form.addRow("تاریخ فاکتور:", self.date_label)
        form.addRow("تخفیف کل فاکتور:", self.discount_input)
        form.addRow("مالیات:", self.tax_input)
        form.addRow("توضیحات:", self.description_input)
        layout.addLayout(form)

        add_item_btn = QPushButton("➕ افزودن قلم کالا")
        add_item_btn.clicked.connect(self.add_item)
        layout.addWidget(add_item_btn)

        self.items_table = QTableWidget()
        self.items_table.setColumnCount(6)
        self.items_table.setHorizontalHeaderLabels(
            ["کالا", "تعداد", "قیمت واحد", "تخفیف", "جمع", ""]
        )
        self.items_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.items_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.items_table)

        self.total_label = QLabel("جمع کل: 0")
        self.total_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(self.total_label)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("💾 ثبت فاکتور")
        save_btn.clicked.connect(self.save_invoice)
        cancel_btn = QPushButton("انصراف")
        cancel_btn.clicked.connect(self.reject)
        # (Phase 13.2) فقط وقتی یک Draft فعال/بازیابی‌شده وجود دارد نمایش داده می‌شود
        self.discard_draft_btn = QPushButton("🗑️ دور ریختن پیش‌نویس")
        self.discard_draft_btn.clicked.connect(self.discard_recovered_draft)
        self.discard_draft_btn.setVisible(False)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(self.discard_draft_btn)
        layout.addLayout(btn_row)

        self.setLayout(layout)

    def load_suppliers(self):
        suppliers = get_suppliers()
        if not suppliers:
            QMessageBox.warning(
                self, "هشدار",
                "هیچ شخصی به‌عنوان «فروشنده» ثبت نشده است.\n"
                "ابتدا از بخش «اشخاص» یک تأمین‌کننده اضافه کنید و گزینه «فروشنده» را برایش تیک بزنید."
            )
        for s in suppliers:
            self.supplier_combo.addItem(s["FullName"], s["ID"])

    def add_item(self):
        picker = ProductPickerDialog()
        if not picker.exec():
            return
        product = picker.selected_product

        qty_dialog = QDialog(self)
        qty_dialog.setWindowTitle("تعداد و قیمت خرید")
        qty_dialog.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        f = QFormLayout()
        qty_input = QDoubleSpinBox()
        qty_input.setMinimum(1)
        qty_input.setMaximum(999999)
        qty_input.setValue(1)
        price_input = QDoubleSpinBox()
        price_input.setMaximum(999999999)
        price_input.setGroupSeparatorShown(True)
        price_input.setValue(float(product.get("PurchasePrice") or 0))
        discount_input = QDoubleSpinBox()
        discount_input.setMaximum(999999999)
        discount_input.setGroupSeparatorShown(True)
        f.addRow(f"کالا: {product['Name']}", QLabel(""))
        f.addRow("تعداد:", qty_input)
        f.addRow("قیمت خرید واحد:", price_input)
        f.addRow("تخفیف این قلم:", discount_input)
        ok_btn = QPushButton("تایید")
        f.addRow(ok_btn)
        qty_dialog.setLayout(f)

        result = {}

        def confirm():
            result["qty"] = qty_input.value()
            result["price"] = price_input.value()
            result["discount"] = discount_input.value()
            qty_dialog.accept()

        ok_btn.clicked.connect(confirm)
        if not qty_dialog.exec():
            return

        qty = int(result["qty"])
        price = result["price"]
        discount = result["discount"]

        serials = None
        if product["HasSerial"]:
            serial_dlg = SerialEntryDialog(product["Name"], qty)
            if not serial_dlg.exec():
                return
            serials = serial_dlg.serials

        self.items.append({
            "product_id": product["ID"],
            "product_name": product["Name"],
            "has_serial": bool(product["HasSerial"]),
            "quantity": qty,
            "unit_price": price,
            "discount": discount,
            "serials": serials,
        })
        self.refresh_items_table()

    def refresh_items_table(self):
        self.items_table.setRowCount(len(self.items))
        total = 0
        for i, item in enumerate(self.items):
            line_total = item["quantity"] * item["unit_price"] - item["discount"]
            total += line_total
            self.items_table.setItem(i, 0, QTableWidgetItem(item["product_name"]))
            self.items_table.setItem(i, 1, QTableWidgetItem(str(item["quantity"])))
            self.items_table.setItem(i, 2, QTableWidgetItem(f"{item['unit_price']:,.0f}"))
            self.items_table.setItem(i, 3, QTableWidgetItem(f"{item['discount']:,.0f}"))
            self.items_table.setItem(i, 4, QTableWidgetItem(f"{line_total:,.0f}"))

            remove_btn = QPushButton("حذف")
            remove_btn.clicked.connect(lambda checked, idx=i: self.remove_item(idx))
            self.items_table.setCellWidget(i, 5, remove_btn)

        self.total_label.setText(f"جمع کل: {total:,.0f}")

    def remove_item(self, index):
        del self.items[index]
        self.refresh_items_table()

    # ---------------- Draft / AutoSave (Phase 13.2) ----------------

    def _collect_draft_data(self):
        """داده خام و کاملاً Serializable فرم را برای ذخیره در Draft برمی‌گرداند."""
        return {
            "supplier_id": self.supplier_combo.currentData(),
            "discount": self.discount_input.value(),
            "tax": self.tax_input.value(),
            "description": self.description_input.toPlainText(),
            "items": self.items,
        }

    def _is_form_empty(self):
        """اگر فرم هنوز هیچ داده معناداری ندارد، از ساخت Draft خالی صرف‌نظر می‌شود."""
        return (
            not self.items
            and not self.description_input.toPlainText().strip()
            and self.discount_input.value() == 0
            and self.tax_input.value() == 0
        )

    def _check_for_existing_draft(self):
        """هنگام باز شدن فرم، Draft فعال قبلی (در صورت وجود) را پیدا و از کاربر می‌پرسد."""
        try:
            drafts = draft_service.get_active_drafts(
                self.current_user["ID"], form_type=self.DRAFT_FORM_TYPE
            )
        except Exception:
            logger.exception("خطا در بررسی پیش‌نویس‌های موجود فاکتور خرید")
            return

        if not drafts:
            return

        draft = drafts[0]  # جدیدترین Draft فعال
        reply = QMessageBox.question(
            self,
            "بازیابی پیش‌نویس",
            "یک پیش‌نویس ذخیره‌شده از فاکتور خرید قبلی پیدا شد. آیا می‌خواهید آن را بازیابی کنید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self._restore_draft(draft)
            except Exception:
                logger.exception("خطا در بازیابی پیش‌نویس فاکتور خرید")
        # اگر کاربر «خیر» را انتخاب کند، فرم خالی می‌ماند و Draft حذف نمی‌شود.

    def _restore_draft(self, draft):
        """فرم را از داده ذخیره‌شده یک Draft بازسازی می‌کند."""
        data = draft.get("Data") or {}

        supplier_id = data.get("supplier_id")
        if supplier_id is not None:
            idx = self.supplier_combo.findData(supplier_id)
            if idx >= 0:
                self.supplier_combo.setCurrentIndex(idx)

        self.discount_input.setValue(data.get("discount") or 0)
        self.tax_input.setValue(data.get("tax") or 0)
        self.description_input.setPlainText(data.get("description") or "")

        items = data.get("items")
        if isinstance(items, list):
            self.items = items
        self.refresh_items_table()

        self.draft_id = draft.get("ID")
        self.discard_draft_btn.setVisible(bool(self.draft_id))

    def autosave(self):
        """هر تقریباً ۶۰ ثانیه فراخوانی می‌شود. هرگز نباید فاکتور خرید بسازد یا برنامه را متوقف کند."""
        try:
            if self._is_form_empty():
                return
            data = self._collect_draft_data()
            self.draft_id = draft_service.save_draft(
                user_id=self.current_user["ID"],
                form_type=self.DRAFT_FORM_TYPE,
                data=data,
                session_id=self.session_id,
                draft_id=self.draft_id,
            )
            if self.draft_id:
                self.discard_draft_btn.setVisible(True)
        except Exception:
            # طبق بخش ۵ الزامات AutoSave: خطای AutoSave هرگز نباید برنامه را Crash کند
            logger.exception("خطا در AutoSave پیش‌نویس فاکتور خرید")

    def discard_recovered_draft(self):
        """با تصمیم صریح کاربر، Draft فعلی را برای همیشه دور می‌ریزد و فرم را پاک می‌کند."""
        if not self.draft_id:
            return
        reply = QMessageBox.question(
            self,
            "دور ریختن پیش‌نویس",
            "آیا مطمئن هستید می‌خواهید این پیش‌نویس را برای همیشه دور بریزید؟\nفرم فعلی پاک خواهد شد.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            draft_service.discard_draft(self.draft_id, self.current_user["ID"])
        except Exception:
            logger.exception("خطا در دور ریختن پیش‌نویس فاکتور خرید")

        self.draft_id = None
        self.discard_draft_btn.setVisible(False)
        self.items = []
        self.refresh_items_table()
        self.discount_input.setValue(0)
        self.tax_input.setValue(0)
        self.description_input.clear()

    def save_invoice(self):
        if self.supplier_combo.count() == 0:
            QMessageBox.warning(self, "خطا", "ابتدا یک فروشنده/تأمین‌کننده ثبت کنید.")
            return
        if not self.items:
            QMessageBox.warning(self, "خطا", "حداقل یک قلم کالا اضافه کنید.")
            return

        try:
            invoice_id, invoice_number = create_purchase_invoice(
                supplier_id=self.supplier_combo.currentData(),
                shamsi_date=self.date_label.text(),
                discount_amount=self.discount_input.value(),
                tax_amount=self.tax_input.value(),
                description=self.description_input.toPlainText().strip(),
                user_id=self.current_user["ID"],
                items=self.items,
            )
            # (Phase 13.2) فاکتور با موفقیت ثبت شد؛ Draft مربوطه (در صورت وجود) بسته می‌شود
            if self.draft_id:
                try:
                    draft_service.complete_draft(self.draft_id, self.current_user["ID"])
                except Exception:
                    logger.exception("خطا در نهایی‌کردن Draft بعد از ثبت فاکتور خرید")
                finally:
                    self.draft_id = None

            QMessageBox.information(self, "موفق", f"فاکتور خرید شماره {invoice_number} با موفقیت ثبت شد.")
            self.accept()
        except InventoryError as e:
            QMessageBox.warning(self, "خطا", str(e))
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"ثبت فاکتور ناموفق بود:\n{e}")


class ViewInvoiceItemsDialog(QDialog):
    """نمایش فقط‌خواندنی اقلام یک فاکتور خرید"""

    def __init__(self, invoice_id, invoice_number):
        super().__init__()
        self.setWindowTitle(f"اقلام فاکتور خرید شماره {invoice_number}")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(600, 400)
        layout = QVBoxLayout()

        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["کالا", "تعداد", "قیمت واحد", "تخفیف", "جمع"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        rows = get_invoice_items(invoice_id)
        table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            table.setItem(i, 0, QTableWidgetItem(r["ProductName"]))
            table.setItem(i, 1, QTableWidgetItem(str(r["Quantity"])))
            table.setItem(i, 2, QTableWidgetItem(f"{r['UnitPrice']:,.0f}"))
            table.setItem(i, 3, QTableWidgetItem(f"{r['DiscountAmount']:,.0f}"))
            table.setItem(i, 4, QTableWidgetItem(f"{r['TotalPrice']:,.0f}"))

        layout.addWidget(table)
        close_btn = QPushButton("بستن")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        self.setLayout(layout)


class PurchaseInvoicesWindow(QWidget):
    def __init__(self, current_user, session_id=None):
        super().__init__()
        self.current_user = current_user
        self.session_id = session_id  # (Phase 13.2) برای انتقال به فرم فاکتور خرید جدید
        self.setWindowTitle("مدیریت خرید")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(850, 500)
        self._build_ui()
        self.load_data()

    def _build_ui(self):
        layout = QVBoxLayout()

        top_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("جستجو بر اساس شماره فاکتور یا نام فروشنده...")
        self.search_input.textChanged.connect(self.load_data)
        add_btn = QPushButton("➕ فاکتور خرید جدید")
        add_btn.clicked.connect(self.add_invoice)
        top_row.addWidget(self.search_input)
        top_row.addWidget(add_btn)
        layout.addLayout(top_row)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["شماره فاکتور", "تاریخ", "فروشنده", "مبلغ قابل پرداخت", "توضیحات", ""]
        )
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        self.setLayout(layout)

    def load_data(self):
        rows = get_purchase_invoices(self.search_input.text())
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(str(r["InvoiceNumber"])))
            self.table.setItem(i, 1, QTableWidgetItem(r["ShamsiDate"] or ""))
            self.table.setItem(i, 2, QTableWidgetItem(r["SupplierName"] or ""))
            self.table.setItem(i, 3, QTableWidgetItem(f"{r['PayableAmount']:,.0f}"))
            self.table.setItem(i, 4, QTableWidgetItem(r["Description"] or ""))

            view_btn = QPushButton("مشاهده اقلام")
            view_btn.clicked.connect(
                lambda checked, inv_id=r["ID"], num=r["InvoiceNumber"]: self.view_items(inv_id, num)
            )
            self.table.setCellWidget(i, 5, view_btn)

    def add_invoice(self):
        dlg = NewPurchaseInvoiceDialog(self.current_user, session_id=self.session_id)
        if dlg.exec():
            self.load_data()

    def view_items(self, invoice_id, invoice_number):
        dlg = ViewInvoiceItemsDialog(invoice_id, invoice_number)
        dlg.exec()
