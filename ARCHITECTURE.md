# ARCHITECTURE.md

## نمای کلی
StoreApp یک اپلیکیشن دسکتاپ Python + PyQt6 با معماری لایه‌ای ساده است.

```
main.py                 نقطه شروع برنامه
config.py                تنظیمات اتصال دیتابیس
create_admin.py           ابزار کمکی ساخت کاربر ادمین اولیه

ui/                      لایه رابط کاربری (پنجره‌ها، PyQt6)
services/                لایه منطق کسب‌وکار (Business Logic)
database/                لایه دسترسی به داده (db.py) + اسکریپت‌های SQL
utils/                   ابزارهای مشترک (تاریخ شمسی، هش پسورد، ...)
tests/                   تست‌ها (از Phase 12 به بعد)
archive/                 بایگانی ZIPهای تاریخی فازهای قبلی (فقط مرجع، نه Source of Truth)
```

## قانون لایه‌بندی
- `ui/` فقط با `services/` صحبت می‌کند، مستقیم با `database/` کار نمی‌کند.
- `services/` منطق کسب‌وکار و Query های SQL را نگه می‌دارد؛ از `database/db.py` برای اجرای Query استفاده می‌کند.
- `utils/` کاملاً مستقل و بدون وابستگی به `ui`/`services` است.

## لایه‌های موجود (Phase 12)
| لایه | وضعیت |
|---|---|
| Persons / Products / Inventory (FIFO) | پیاده‌سازی‌شده |
| Purchase / Sale / Purchase Return | پیاده‌سازی‌شده (بدون یکپارچگی کامل Workflow) |
| Cash / Bank / Cheque / Installments | پیاده‌سازی‌شده |
| Settings / User Permissions | پیاده‌سازی‌شده (Phase 12 دوباره فعال شد) |
| Session / Draft (Power Failure Foundation) | فقط زیرساخت پایه؛ به UI وصل نشده |
| **Accounting Layer (Double Entry)** | **PLANNED — هنوز پیاده‌سازی نشده** |
| Correlation ID / Workflow Timeline | **PLANNED — هنوز پیاده‌سازی نشده** |

## چرا Accounting Layer هنوز نیست
طبق تصمیم صریح Master Prompt Phase 12، ساخت Accounting Engine کامل عمداً از Scope این فاز خارج نگه داشته شده تا تمرکز روی پایدارسازی و امنیت باشد. طراحی پیشنهادی آن در `ACCOUNTING_RULES.md` آمده اما چیزی از آن ساخته نشده.
