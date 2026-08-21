# DATABASE_SCHEMA.md

> مرجع تعریف کامل هر جدول، فایل‌های داخل `database/schema/` و
> `database/migrations/` است. این فایل فقط فهرست و وضعیت را نشان می‌دهد.

## جداول موجود (پیاده‌سازی‌شده)

| جدول | حوزه |
|---|---|
| Users, UserPermissions, ActivityLog | کاربران و دسترسی |
| PersonGroups, Persons, PersonGroupMap | اشخاص (مشتری/فروشنده/کارمند) |
| ProductGroups, Products, ProductSerials | کالا و سریال/IMEI |
| PurchaseInvoices, PurchaseInvoiceItems, ProductPurchaseLayers, ProductCardex | خرید و انبار (FIFO) |
| PurchaseReturnInvoices | برگشت از خرید |
| SalesInvoices, SalesInvoiceItems | فروش |
| Receipts, Payments | دریافت و پرداخت |
| CashBoxes, BankAccounts, CashBoxTransactions, BankTransactions | صندوق و بانک |
| Cheques | چک |
| InstallmentPlans | اقساط |
| MessageTemplates | ارتباط با مشتری |
| Settings | تنظیمات کلی |
| **Sessions, Drafts** *(جدید — Phase 12)* | زیرساخت پایه Power Failure Recovery |

## جداول برنامه‌ریزی‌شده (هنوز پیاده‌سازی نشده)

| جدول | وضعیت |
|---|---|
| Accounts (دفتر حساب‌ها) | NOT IMPLEMENTED |
| AccountingDocuments | NOT IMPLEMENTED |
| AccountingEntries | NOT IMPLEMENTED |

این سه جدول بخش اصلی لایه حسابداری دوطرفه هستند که در Phase 12 عمداً ساخته نشدند (خارج از Scope). طراحی هدف آن‌ها در `ACCOUNTING_RULES.md` توضیح داده شده.

## محل تعریف دقیق ستون‌ها
برای دیدن دقیق نوع داده و محدودیت هر ستون:
- جداول پایه: `database/migrations/001_initial_safe.sql`
- خرید/انبار: `database/migrations/002_purchase_inventory.sql`
- فروش: `database/migrations/003_sales.sql`
- مالی (صندوق/بانک/چک/اقساط): `database/migrations/004_financial.sql`
- ارتباطات: `database/migrations/005_communication.sql`
- برگشت از خرید: `database/migrations/006_purchase_return.sql`
- Session/Draft: `database/migrations/007_session_recovery.sql`
