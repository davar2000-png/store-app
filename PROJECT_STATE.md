# PROJECT_STATE.md

> این فایل وضعیت *واقعی* پروژه را در هر لحظه نشان می‌دهد. هر Account جدید
> باید ابتدا همین فایل را بخواند، نه به حافظه مکالمه قبلی اعتماد کند.

**آخرین به‌روزرسانی:** Phase 12 (Stabilization)

## Current Phase
12 — Project Stabilization + GitHub Normalization

## Previous Phase
11 — دارای Regression (بخش «Known Regression» را ببینید)

## Technology
Python 3 + PyQt6 + pyodbc + SQL Server

## Current Branch
`main` (هیچ Branch جداگانه‌ای برای Phase 12 ساخته نشد — طبق تصمیم کاربر، تمرکز روی محتوا بود نه ساختار Branch؛ این را در فاز بعد می‌توان اصلاح کرد)

## Last Commit (پیش از تحویل Phase 12)
`31027ba` — Delete TECHNOKALARoboAccBackUp_1405-05-23-09-50.zip

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
