# ساختار پوشه Database

## `schema/`
نسخه **نصب تازه (Fresh Install)**. فقط برای یک دیتابیس کاملاً خالی و جدید استفاده شود.
⚠️ این فایل‌ها جدول‌های هم‌نام را DROP می‌کنند — روی دیتابیس Production اجرا نشوند.

## `migrations/`
نسخه‌های **امن و غیرمخرب**، به ترتیب شماره اجرا شوند (001، 002، ...).
هرکدام قبل از هر تغییر بررسی می‌کنند که آیا جدول/ستون از قبل وجود دارد یا نه، و در صورت وجود، از آن رد می‌شوند. برای آپدیت دیتابیسی که از قبل داده واقعی دارد از همین پوشه استفاده کنید.

| فایل | محتوا |
|---|---|
| 001_initial_safe.sql | هسته: Users, UserPermissions, ActivityLog, Persons, Products, ... |
| 002_purchase_inventory.sql | خرید و انبار (FIFO، کاردکس، سریال/IMEI) |
| 003_sales.sql | فروش |
| 004_financial.sql | صندوق، بانک، چک، اقساط |
| 005_communication.sql | ارتباط با مشتری |
| 006_purchase_return.sql | برگشت از خرید |
| 007_session_recovery.sql | (Phase 12) پایه Session/Draft برای مقاومت در برابر قطع برق |
| 008_audit_logs.sql | (Phase 14) Audit Trail — `AuditLogs` |
| 009_accounting_core.sql | (Phase 15.1) Chart of Accounts + Journal Entries — **فقط زیرساخت، هنوز به هیچ تراکنش تجاری وصل نشده** (جزئیات در `PHASE_REGISTRY.md`) |
| 010_accounting_tax_payable.sql | (Phase 15.2) افزودن حساب `2200` (مالیات دریافتنی از مشتری/پرداختنی به سازمان مالیاتی) — برای موازنه سند حسابداری فروش وقتی `TaxAmount > 0` باشد (جزئیات در `PHASE_REGISTRY.md`) |

## قانون طلایی
هرگز `schema/001_fresh_install.sql` را روی دیتابیسی که کاربر واقعی و داده واقعی دارد اجرا نکنید. همیشه از `migrations/` به ترتیب شماره استفاده کنید، و همیشه قبل از اجرای هر Migration، از دیتابیس Backup بگیرید.

## ترتیب اجرا

**نصب کاملاً تازه (سیستم جدید، بدون داده):**
1. `schema/001_fresh_install.sql`
2. سپس تمام فایل‌های `migrations/002` تا `migrations/007` به ترتیب شماره

**دیتابیس موجود (Production با داده واقعی):**
1. از دیتابیس Backup بگیرید.
2. فقط `migrations/001` تا `migrations/007` را به ترتیب شماره اجرا کنید (نه `schema/001_fresh_install.sql`).
