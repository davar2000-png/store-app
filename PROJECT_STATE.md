# PROJECT_STATE.md

> این فایل وضعیت *واقعی* پروژه را در هر لحظه نشان می‌دهد. هر Account جدید
> باید ابتدا همین فایل را بخواند، نه به حافظه مکالمه قبلی اعتماد کند.

**آخرین به‌روزرسانی:** Phase 17 (Merge phase/14-workflow-audit → main)

## Current Phase
17 — Merge کامل برنچ `phase/14-workflow-audit` (شامل Phase 13.5.1 تا 16B) به `main`

## Previous Phase
16B — Web Backend Skeleton (روی برنچ جدا، حالا merge شده)

## ⚠️ تصمیم معماری قطعی (این فاز)
تحلیل و اتصال به `RoboAccDB_Legacy` به‌طور کامل کنار گذاشته شد. پروژه با
دیتابیس مستقل `StoreAppDB` (Chart of Accounts داخلی، بدون نگاشت به
Legacy) ادامه می‌یابد. این تصمیم نهایی و توسط کاربر تأیید شده است.

## Technology
Python 3 + PyQt6 + pyodbc + SQL Server (+ FastAPI برای Web Skeleton آزمایشی)

## Current Branch
`main` — برنچ `phase/14-workflow-audit` با `--no-ff` merge شد (بدون Conflict،
Automatic merge). این Branch بعد از تأیید نهایی کاربر و Push موفق قابل حذف است.

## Last Commit (پیش از تحویل Phase 12، برای مرجع تاریخی)
`31027ba` — Delete TECHNOKALARoboAccBackUp_1405-05-23-09-50.zip

## Merge — Phase 17 جزئیات
- **منبع Merge:** `origin/phase/14-workflow-audit` (آخرین commit: `2ece6da` — docs(phase 16B))
- **مقصد:** `main` (آخرین commit قبل از merge: `7a7ed16`)
- **نوع Merge:** `git merge --no-ff` — بدون هیچ Conflict (Automatic merge went well)
- **فایل‌های تغییر/اضافه‌شده:** 41 فایل (+6759 / -80 خط) — شامل
  `services/accounting_service.py`, `services/audit_service.py`,
  migrationهای 008 تا 014 (Audit Logs + Accounting Core + اتصال کامل
  فروش/خرید/دریافت/پرداخت/برگشت به Ledger دوطرفه)، `web/` (FastAPI Skeleton)،
  و بیش از ۱۸۰ تست جدید.
- **نتیجهٔ تست پس از Merge:** `217 passed, 0 failed` (تست‌های
  Accounting/Audit/Sales/Inventory/Financial/Web Skeleton + تست‌های قدیمی
  Session/Draft/Smoke — همگی سبز)
- **این merge هنوز Push نشده** — دلیل: این Account (مانند Accountهای قبلی)
  به Token/اعتبارنامهٔ GitHub کاربر دسترسی مستقیم ندارد. جزئیات کامل نحوهٔ
  اعمال آن در `AI_HANDOFF.md` بخش «PUSH STATUS» آمده.

## Known Regression (برطرف‌شده در Phase 12)
- **Settings Module**: در Phase 11 حذف شده بود؛ در Phase 12 از Phase 10 بازیابی شد.
- **User Permissions**: کنترل دسترسی ماژول (`is_module_allowed`) در Phase 11 حذف شده بود؛ در Phase 12 بازیابی شد و برای دو ماژول جدید Phase 11 (لیست فاکتورها، برگشت از خرید) هم کلید دسترسی تعریف شد.

## Known Issue — هنوز حل‌نشده 🔴
دو فایل Backup واقعی SQL Server (`TECHNOKALARoboAccBackUp_...`) هنوز در **تاریخچه Git** (نه در نسخه فعلی) وجود دارند. کاربر تصمیم گرفت فعلاً پاکسازی کامل تاریخچه (که نیاز به Force Push دارد) را به تعویق بیندازد. جزئیات کامل در `SECURITY.md`.

## Accounting
Not implemented — طبق Scope این فاز عمداً ساخته نشد.

## Workflow
Partial — خرید/فروش کار می‌کند اما یکپارچگی کامل (Correlation ID، Workflow Timeline) هنوز پیاده نشده.

## Audit
Partial — فقط `ActivityLog` ساده وجود دارد، نه Audit کامل با CorrelationID.

## Power Failure Protection
Foundation Only — جداول `Sessions`/`Drafts` و `SessionService`/`DraftService` ساخته شدند، اما هنوز به فرم‌های واقعی UI وصل نشده‌اند. AutoSave خودکار هنوز فعال نیست.

## Backup
نیاز به محل امن خارج از GitHub. جزئیات در `BACKUP_POLICY.md`.

## Source Structure
از این فاز به بعد، کد واقعی مستقیماً در ریشه Repository است (`ui/`, `services/`, `database/`, `utils/`)؛ ZIPهای قدیمی فقط در `archive/` به‌عنوان بایگانی تاریخی نگهداری می‌شوند.

## Update — Phase 16B (Web Backend Skeleton)

> این بخش additive است و بخش‌های بالا (مربوط به Phase 12) را جایگزین نمی‌کند؛
> صرفاً وضعیت فعلی و اضافه‌شده روی همان مبنا را ثبت می‌کند.

**Branch:** `phase/14-workflow-audit`
**Base commit قبل از Phase 16B:** `2a73b9a` (Phase 15.6.5 — Sales Return Core)
**Code commit این فاز:** `3b9fccd` — `feat(web): add FastAPI chrome test skeleton`

هدف Phase 16 مجموعه‌ای از فازها برای افزودن یک Web UI موازی (Chrome) روی
همان Business Logic دسکتاپ موجود است، بدون بازنویسی `services/`. Phase 16B
فقط اسکلت HTTP را اضافه کرد:

```text
web/__init__.py
web/app.py
web/templates/base.html
web/templates/home.html
web/static/style.css
requirements-web.txt
tests/test_web_skeleton.py
```

Endpointهای فعلی: `GET /`, `GET /health`, `GET /static/style.css`.
`/health` وضعیت واقعی اتصال دیتابیس را گزارش می‌دهد (بدون Fake کردن).

**تست شده با:** FastAPI TestClient + یک اجرای واقعی `uvicorn` روی
`127.0.0.1:8000` همراه با درخواست HTTP واقعی (curl).
**تست نشده با:** مرورگر Chrome واقعی — این تأیید هنوز انجام نشده است.

`ui/`, `services/`, `database/`, `utils/`, `main.py`, `config.py`,
`requirements.txt` و migrationها در این فاز **بدون تغییر** ماندند.

نتیجه تست: `217 passed` (۲۰۷ تست قبلی + ۱۰ تست جدید Web Skeleton).

**فاز بعدی:** 16C — Auth Extraction + Session Login — **شروع نشده**، منتظر
تأیید صریح کاربر.
