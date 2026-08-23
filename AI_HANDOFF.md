# AI_HANDOFF.md

> Account بعدی: این فایل را قبل از هر کاری بخوانید. به حافظه مکالمه قبلی
> اعتماد نکنید — GitHub مرجع اصلی است.

## LAST ACCOUNT
Claude (Phase 15.1 — Accounting Core Foundation)

## CURRENT PHASE
15.1 — تکمیل‌شده (روی برنچ `phase/14-workflow-audit`)

## CURRENT BRANCH
`phase/14-workflow-audit`
(همچنان به `main` Merge نشده — این تصمیم از Phase 14.3 به بعد ادامه دارد
و توسط این اکانت هم تغییر داده نشد؛ کاربر باید Merge را وقتی صلاح دید
انجام دهد.)

## LAST COMMIT
`fd8c811` — feat(phase 15.1): accounting core foundation — Chart of
Accounts + double-entry Journal Entries
(روی `phase/14-workflow-audit`، Push انجام شد — این بار محیط توانست
مستقیم Push کند؛ اگر اکانت بعدی نتوانست، همان روش Patch قبلی جواب داده بود.)

## COMPLETED (این اکانت)
- Audit کامل مطابق دستور Brief: `git status`, `git log -10`, خواندن کامل
  `PHASE_REGISTRY.md`/`AI_HANDOFF.md`، بررسی `services/`, `ui/`,
  `database/migrations/*.sql`, `tests/`، و اجرای تست‌ها قبل از هر تغییر.
- تأیید Baseline: کد واقعی روی GitHub دقیقاً با Brief مطابقت داشت
  (`72e6390`, 21 تست موفق، Working Tree Clean).
- تحلیل وضعیت واقعی Accounting: هیچ Double-Entry Ledger در پروژه وجود
  نداشت (فقط Sub-Ledgerهای تک‌طرفه خوب‌ساخته — جزئیات کامل در
  `PHASE_REGISTRY.md § Phase 15.1`).
- ساخت Phase 15.1: Chart of Accounts + Journal Entries دوطرفه (Migration
  `009_accounting_core.sql` + `services/accounting_service.py`) —
  **عمداً هنوز به هیچ تراکنش تجاری وصل نشده.**
- ۱۴ تست جدید، همه سبز؛ `py_compile` و `git diff --check` تمیز.
- به‌روزرسانی `PHASE_REGISTRY.md`, `AI_HANDOFF.md` (همین فایل).

## NOT COMPLETED / آگاهانه واگذارشده به فاز بعد
این خودِ مأموریت صریح فاز بعدی است، نه یک نقص:
- **هیچ تراکنش تجاری واقعی هنوز به Ledger جدید Post نمی‌شود.** فروش،
  خرید، دریافت، پرداخت، چک و اقساط همچنان دقیقاً مثل قبل کار می‌کنند
  (بدون تغییر) و اثری روی `JournalEntries` ندارند.
- هیچ Ledger Viewer/UI ای برای دیدن اسناد حسابداری ساخته نشده.
- `phase/14-workflow-audit` هنوز به `main` Merge نشده.
- پاکسازی کامل Git History از فایل‌های Backup حساس هنوز انجام نشده (از
  Phase 12 به تعویق افتاده، نیاز به تصمیم صریح کاربر برای Force Push).

## FILES CHANGED (این اکانت)
**ایجادشده:**
`database/migrations/009_accounting_core.sql`, `services/accounting_service.py`,
`tests/test_accounting_service.py`

**تغییریافته:**
`tests/test_smoke.py` (اضافه شدن `services.accounting_service` به لیست Import)،
`database/README.md` (مستندسازی Migration 008 و 009)،
`PHASE_REGISTRY.md`, `AI_HANDOFF.md`

## DATABASE CHANGES
یک Migration جدید و امن (`009_accounting_core.sql`، الگوی
`IF OBJECT_ID(...) IS NULL` مثل بقیه Migrationها) که باید توسط کاربر روی
دیتابیس واقعی‌اش اجرا شود. هیچ جدول موجودی تغییر یا حذف نشد. Seed حساب‌ها
هم Idempotent است (`IF NOT EXISTS ... WHERE Code = ...`).

## TESTS
`python -m pytest -q tests` → **35 passed** (۲۱ قبل از این اکانت + ۱۴ جدید).
`python -m py_compile services/accounting_service.py tests/test_accounting_service.py tests/test_smoke.py` → بدون خطا.
`git diff --check` → بدون خطای Whitespace.

## NEXT PHASE — پیشنهاد مشخص برای اکانت بعدی (15.2)
اتصال اولین تراکنش تجاری واقعی به Ledger جدید. پیشنهاد: **فروش** (Sales)
چون ساده‌ترین است — بهای تمام‌شده FIFO از قبل در
`SalesInvoiceItems.CostAmount` محاسبه و ذخیره می‌شود، پس منطق سند
حسابداری آن تقریباً این شکل است (طرح اولیه، نه دستور قطعی؛ اکانت بعدی
باید خودش دقیق طراحی کند):

```
بدهکار   1100 حساب‌های دریافتنی   PayableAmount
بستانکار 4000 درآمد فروش          TotalAmount - DiscountAmount
بستانکار (مالیات، اگر مدل‌سازی شود)  TaxAmount
---
بدهکار   5000 بهای تمام‌شده کالای فروش‌رفته   SUM(CostAmount)
بستانکار 1200 موجودی کالا                    SUM(CostAmount)
```

نکات مهم برای اکانت بعدی:
- این باید در همان Transaction اتمیک `create_sales_invoice()` (یا
  بلافاصله بعد از Commit موفق آن، با استفاده از `invoice_id` واقعی به‌عنوان
  `source_id="SalesInvoices"`) فراخوانی شود، نه جدا و غیرهمگام.
- قبل از هرگونه تغییر در `sales_service.py`، حتماً تست‌های موجود (که فعلاً
  صفر است — `sales_service.py` هیچ تست ندارد) را با یک Regression Test
  پوشش بده تا مطمئن شوی وصل‌کردن Ledger چیزی را در مسیر فروش خراب نمی‌کند.
- اگر مدل مالیات/تخفیف در سطح فاکتور با ساختار Chart of Accounts فعلی
  جور در نمی‌آید، این را به‌عنوان «ابهام حسابداری» طبق قانون Brief متوقف
  کن و گزارش بده، پیش از پیاده‌سازی حدسی.
- بعد از فروش: خرید (Purchase) → دریافت/پرداخت → برگشت‌ها → چک/اقساط،
  هرکدام یک زیرفاز مستقل و قابل Commit جدا.
