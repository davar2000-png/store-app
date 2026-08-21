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
