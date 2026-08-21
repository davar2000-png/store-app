# -*- coding: utf-8 -*-
"""پنجره Import اطلاعات از نرم‌افزار ربات — با نگاشت ستون قابل‌تنظیم"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QTabWidget, QHeaderView,
    QFormLayout, QMessageBox, QCheckBox, QScrollArea
)
from PyQt6.QtCore import Qt
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import services.robat_import_service as ris


def make_preview_table():
    table = QTableWidget()
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    table.setMaximumHeight(180)
    return table


class ImportTabBase(QWidget):
    """
    کلاس پایه برای هر تب Import.
    target_fields: لیستی از (کلید, برچسب فارسی, اجباری؟)
    """
    target_fields = []
    title_text = ""

    def __init__(self):
        super().__init__()
        self.source_columns = []
        self._build_ui()
        self.load_databases()

    def _build_ui(self):
        layout = QVBoxLayout()

        if self.title_text:
            desc = QLabel(self.title_text)
            desc.setWordWrap(True)
            layout.addWidget(desc)

        top_row = QHBoxLayout()
        self.db_combo = QComboBox()
        self.db_combo.currentIndexChanged.connect(self.load_tables)
        self.table_combo = QComboBox()
        self.table_combo.currentIndexChanged.connect(self.load_columns)
        load_btn = QPushButton("🔍 نمایش پیش‌نمایش و ستون‌ها")
        load_btn.clicked.connect(self.load_preview_and_columns)

        top_row.addWidget(QLabel("دیتابیس ربات:"))
        top_row.addWidget(self.db_combo)
        top_row.addWidget(QLabel("جدول:"))
        top_row.addWidget(self.table_combo)
        top_row.addWidget(load_btn)
        layout.addLayout(top_row)

        layout.addWidget(QLabel("پیش‌نمایش ۱۵ ردیف اول:"))
        self.preview_table = make_preview_table()
        layout.addWidget(self.preview_table)

        layout.addWidget(QLabel("نگاشت ستون‌ها (مشخص کن هر فیلد جدید از کدام ستون ربات بیاید):"))
        self.mapping_form = QFormLayout()
        self.mapping_combos = {}
        for key, label, required in self.target_fields:
            combo = QComboBox()
            combo.addItem("— انتخاب نشود —", None)
            self.mapping_combos[key] = combo
            label_text = f"{label} {'(اجباری)' if required else ''}"
            self.mapping_form.addRow(label_text, combo)
        layout.addLayout(self.mapping_form)

        run_btn = QPushButton("▶️ اجرای Import")
        run_btn.setFixedHeight(40)
        run_btn.clicked.connect(self.run_import)
        layout.addWidget(run_btn)

        self.result_label = QLabel("")
        self.result_label.setWordWrap(True)
        layout.addWidget(self.result_label)

        layout.addStretch()
        self.setLayout(layout)

    def load_databases(self):
        try:
            dbs = ris.get_robat_databases()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خواندن لیست دیتابیس‌ها ناموفق بود:\n{e}")
            return
        self.db_combo.clear()
        for d in dbs:
            self.db_combo.addItem(d)
        # اگر دیتابیسی به اسم مشابه RoboAcc پیدا شد، پیش‌فرض انتخابش کن
        for i in range(self.db_combo.count()):
            if "robo" in self.db_combo.itemText(i).lower():
                self.db_combo.setCurrentIndex(i)
                break

    def load_tables(self):
        db_name = self.db_combo.currentText()
        if not db_name:
            return
        try:
            tables = ris.get_tables(db_name)
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خواندن لیست جدول‌ها ناموفق بود:\n{e}")
            return
        self.table_combo.clear()
        for t in tables:
            self.table_combo.addItem(t)

    def load_columns(self):
        pass  # فقط با دکمه «نمایش پیش‌نمایش» بارگذاری می‌شود تا درخواست اضافه به دیتابیس نزنیم

    def load_preview_and_columns(self):
        db_name = self.db_combo.currentText()
        table_name = self.table_combo.currentText()
        if not db_name or not table_name:
            QMessageBox.warning(self, "توجه", "دیتابیس و جدول را انتخاب کن.")
            return

        try:
            self.source_columns = ris.get_columns(db_name, table_name)
            rows = ris.preview_table(db_name, table_name, 15)
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خواندن اطلاعات جدول ناموفق بود:\n{e}")
            return

        # پر کردن جدول پیش‌نمایش
        self.preview_table.setColumnCount(len(self.source_columns))
        self.preview_table.setHorizontalHeaderLabels(self.source_columns)
        self.preview_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, col in enumerate(self.source_columns):
                val = row.get(col, "")
                self.preview_table.setItem(i, j, QTableWidgetItem(str(val) if val is not None else ""))

        # پر کردن کمبوهای نگاشت
        for key, combo in self.mapping_combos.items():
            combo.clear()
            combo.addItem("— انتخاب نشود —", None)
            for col in self.source_columns:
                combo.addItem(col, col)
            # حدس خودکار: اگر اسم ستون شبیه اسم فیلد بود، پیش‌فرض انتخابش کن
            self._auto_guess(key, combo)

    def _auto_guess(self, key, combo):
        guesses = {
            "FullName": ["name", "fullname", "customername", "title"],
            "Mobile": ["mobile", "cell"],
            "Phone": ["phone", "tel"],
            "NationalCode": ["nationalcode", "meli"],
            "Address": ["address"],
            "Name": ["name", "productname", "title"],
            "Code": ["code", "productcode"],
            "Brand": ["brand"],
            "Model": ["model"],
            "PurchasePrice": ["purchaseprice", "buyprice", "costprice"],
            "SalePrice": ["saleprice", "sellprice"],
            "ProductCode": ["code", "productcode"],
            "ProductName": ["name", "productname"],
            "Quantity": ["quantity", "qty", "stock", "count", "remain"],
            "UnitCost": ["price", "cost", "purchaseprice"],
        }
        candidates = guesses.get(key, [])
        for i in range(combo.count()):
            col_name = (combo.itemText(i) or "").lower()
            if any(c in col_name for c in candidates):
                combo.setCurrentIndex(i)
                return

    def get_mapping(self):
        return {key: combo.currentData() for key, combo in self.mapping_combos.items()}

    def run_import(self):
        raise NotImplementedError


class PersonsImportTab(ImportTabBase):
    title_text = "اشخاص (مشتریان/فروشندگان) را از جدول Customers یا مشابه آن در دیتابیس ربات وارد کن."
    target_fields = [
        ("FullName", "نام", True),
        ("Mobile", "موبایل", False),
        ("Phone", "تلفن", False),
        ("NationalCode", "کد ملی", False),
        ("Address", "آدرس", False),
    ]

    def _build_ui(self):
        super()._build_ui()
        self.customer_check = QCheckBox("همه به‌عنوان «مشتری» ثبت شوند")
        self.customer_check.setChecked(True)
        self.seller_check = QCheckBox("همه به‌عنوان «فروشنده» هم ثبت شوند")
        self.layout().insertWidget(self.layout().count() - 2, self.customer_check)
        self.layout().insertWidget(self.layout().count() - 2, self.seller_check)

    def run_import(self):
        db_name = self.db_combo.currentText()
        table_name = self.table_combo.currentText()
        mapping = self.get_mapping()
        if not mapping.get("FullName"):
            QMessageBox.warning(self, "خطا", "ستون «نام» باید نگاشت شود.")
            return

        try:
            result = ris.import_persons(
                db_name, table_name, mapping,
                default_is_customer=self.customer_check.isChecked(),
                default_is_seller=self.seller_check.isChecked()
            )
        except Exception as e:
            QMessageBox.critical(self, "خطا", str(e))
            return

        msg = f"✅ {result['imported']} شخص وارد شد.   ⏭️ {result['skipped']} مورد تکراری/خالی رد شد."
        if result["errors"]:
            msg += f"\n⚠️ {len(result['errors'])} خطا:\n" + "\n".join(result["errors"][:10])
        self.result_label.setText(msg)


class ProductsImportTab(ImportTabBase):
    title_text = "کالاها را از جدول Products (یا مشابه آن) در دیتابیس ربات وارد کن."
    target_fields = [
        ("Name", "نام کالا", True),
        ("Code", "کد کالا", False),
        ("Brand", "برند", False),
        ("Model", "مدل", False),
        ("PurchasePrice", "قیمت خرید", False),
        ("SalePrice", "قیمت فروش", False),
    ]

    def run_import(self):
        db_name = self.db_combo.currentText()
        table_name = self.table_combo.currentText()
        mapping = self.get_mapping()
        if not mapping.get("Name"):
            QMessageBox.warning(self, "خطا", "ستون «نام کالا» باید نگاشت شود.")
            return

        try:
            result = ris.import_products(db_name, table_name, mapping)
        except Exception as e:
            QMessageBox.critical(self, "خطا", str(e))
            return

        msg = f"✅ {result['imported']} کالا وارد شد.   ⏭️ {result['skipped']} مورد تکراری/خالی رد شد."
        if result["errors"]:
            msg += f"\n⚠️ {len(result['errors'])} خطا:\n" + "\n".join(result["errors"][:10])
        self.result_label.setText(msg)


class OpeningStockImportTab(ImportTabBase):
    title_text = (
        "موجودی فعلی هر کالا را وارد کن (بعد از Import کالاها انجام بده). "
        "برای هر کالا با تعداد بیشتر از صفر، یک «موجودی ابتدای دوره» با بهای واقعی ساخته می‌شود."
    )
    target_fields = [
        ("ProductCode", "کد کالا (برای تطبیق)", False),
        ("ProductName", "نام کالا (برای تطبیق)", False),
        ("Quantity", "تعداد موجودی", True),
        ("UnitCost", "بهای واحد", False),
    ]

    def run_import(self):
        db_name = self.db_combo.currentText()
        table_name = self.table_combo.currentText()
        mapping = self.get_mapping()
        if not mapping.get("Quantity"):
            QMessageBox.warning(self, "خطا", "ستون «تعداد موجودی» باید نگاشت شود.")
            return
        if not mapping.get("ProductCode") and not mapping.get("ProductName"):
            QMessageBox.warning(self, "خطا", "حداقل یکی از «کد کالا» یا «نام کالا» باید نگاشت شود.")
            return

        confirm = QMessageBox.question(
            self, "تأیید",
            "این کار یک فاکتور خرید سیستمی (موجودی ابتدای دوره) می‌سازد. ادامه می‌دهید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            result = ris.import_opening_stock(db_name, table_name, mapping)
        except Exception as e:
            QMessageBox.critical(self, "خطا", str(e))
            return

        msg = f"✅ موجودی {result['imported']} کالا ثبت شد.   ⏭️ {result['skipped']} مورد رد شد."
        if result["errors"]:
            msg += f"\n⚠️ {len(result['errors'])} خطا:\n" + "\n".join(result["errors"][:10])
        self.result_label.setText(msg)


class ImportWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Import اطلاعات از نرم‌افزار ربات")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(950, 650)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()

        note = QLabel(
            "💡 پیش‌نیاز: دیتابیس نرم‌افزار ربات باید قبلاً روی همین SQL Server، با Restore، در دسترس باشد.\n"
            "ترتیب پیشنهادی: ۱) اشخاص  ۲) کالاها  ۳) موجودی اولیه"
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        tabs = QTabWidget()
        tabs.addTab(PersonsImportTab(), "👤 اشخاص")
        tabs.addTab(ProductsImportTab(), "📦 کالاها")
        tabs.addTab(OpeningStockImportTab(), "📊 موجودی اولیه")
        layout.addWidget(tabs)

        self.setLayout(layout)
