# UI_DESIGN_SYSTEM.md

> نسخه اولیه — فقط مستندسازی وضعیت فعلی UI. طراحی مجدد کامل (Redesign)
> خارج از Scope Phase 12 است و باید در یک فاز اختصاصی انجام شود.

## Typography
فونت پیش‌فرض PyQt6 (سیستم‌عامل) استفاده می‌شود. اندازه دکمه‌های اصلی داشبورد: `font-size: 13px`.

## RTL
تمام پنجره‌ها با `setLayoutDirection(Qt.LayoutDirection.RightToLeft)` راست‌به‌چپ تنظیم می‌شوند — این الگو در تمام فایل‌های `ui/*.py` رعایت شده و باید در فرم‌های جدید هم تکرار شود.

## Spacing
- `main_layout.setContentsMargins(20, 20, 20, 20)`
- `main_layout.setSpacing(16)` برای فاصله بین بخش‌های اصلی
- `grid.setSpacing(14)` برای فاصله بین دکمه‌های ماژول در داشبورد

## Buttons
دکمه‌های ماژول داشبورد: اندازه ثابت `180×80`. آیکون + متن فارسی در یک دکمه (مثلاً «👤 اشخاص»).

## Forms
فرم‌ها معمولاً از `QLineEdit`, `QDoubleSpinBox`, `QComboBox` استفاده می‌کنند؛ الگوی واحدی برای Validation یا پیام خطا هنوز مستند نشده — این باید در فاز UI Redesign مشخص شود.

## Tables
فهرست‌ها (مثل لیست فاکتورها) از `QTableWidget` با `QHeaderView` استفاده می‌کنند.

## Dialogs
پیام‌های تأیید/خطا با `QMessageBox` (warning/information) نمایش داده می‌شوند — الگوی فعلی ساده و یکنواخت است.

## Navigation
داشبورد اصلی (`main_window.py`) یک صفحه Grid از دکمه‌های ماژول است؛ هر دکمه یک پنجره جدید (`QWidget`/`QDialog`) باز می‌کند. Navigation سلسله‌مراتبی یا Sidebar وجود ندارد — موضوعی برای بررسی در UI Redesign آینده.

## کارهای باقی‌مانده برای فاز UI Redesign
- تعریف پالت رنگ رسمی برند تکنوکالا
- یکسان‌سازی الگوی پیام خطا/موفقیت در تمام فرم‌ها
- بررسی Responsive بودن یا نبودن پنجره‌ها در رزولوشن‌های مختلف
