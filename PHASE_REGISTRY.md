# PHASE_REGISTRY.md

| Phase | عنوان | وضعیت | یادداشت |
|---|---|---|---|
| 1–9 | توسعه اولیه (هسته، خرید/انبار، فروش، مالی، ارتباطات، ...) | Completed | فقط به‌صورت ZIP در `archive/` موجود است |
| 10 | تنظیمات و مدیریت کاربران/دسترسی | Completed but superseded by Phase 11 | ماژول Settings و Permission ساخته شد اما در Phase 11 حذف شد |
| 11 | لیست فاکتورها، برگشت از خرید | Completed with known Regression | Settings و Permission ماژول ۱۰ را کامل حذف کرد |
| 12 | Stabilization + GitHub Normalization + Power Failure Foundation | **Completed (Partial Scope)** | جزئیات پایین |

## Phase 12 — جزئیات

**تکمیل‌شده:**
- بازیابی Settings + User Permissions (رفع Regression Phase 11)
- انتقال Source Code واقعی به ریشه Repository (خروج از حالت ZIP-محور)
- تفکیک `schema.sql` به `schema/` (Fresh Install) و `migrations/` (امن/غیرمخرب)
- ساخت تمام فایل‌های مستندات الزامی
- ساخت زیرساخت پایه Session/Draft برای مقاومت در برابر قطع برق
- `.gitignore` + شناسایی و (تا حدی) رفع خطر Backup حساس

**تکمیل‌نشده / منتقل‌شده به فاز بعد:**
- پاکسازی کامل تاریخچه Git از فایل‌های Backup حساس (نیاز به Force Push دارد؛ کاربر فعلاً به تعویق انداخت)
- اتصال AutoSave/Draft به فرم‌های واقعی UI
- Crash Detection واقعی در `main.py` (فقط API آماده است)
- ساخت Branch جداگانه `phase/12-stabilization`
- Accounting Engine (عمداً خارج از Scope این فاز)

## Phase 13.5.1 — Backup Hardening

**Commit:**
- `f3aff04` — fix: improve pre restore backup path handling

**تکمیل‌شده:**
- اضافه شدن `create_pre_restore_backup()` در `services/backup_service.py`
- ایجاد Backup اضطراری قبل از Restore دیتابیس موجود
- اتصال Pre-Restore Backup به مسیر `restore_backup()`
- اصلاح ساخت مسیر فایل Backup با `os.path.join`
- تست موفق:
  - `python -m pytest -q tests`
  - Result: 16 passed

**یادداشت:**
- فایل `services/backup/legacy_backup_service.py` بررسی شد.
- هیچ import فعالی از آن پیدا نشد؛ فعلاً حذف نشده و به‌عنوان کد قدیمی باقی می‌ماند.

## Verification Update — Session Recovery Review

Verified:
- Crash Detection is wired in `main.py`
  - `find_crashed_sessions()`
  - `mark_as_crashed()`

- Session propagation verified:
  - `MainWindow` passes `session_id` to Purchase and Sales windows.
  - `SalesInvoicesWindow` receives and keeps `session_id`.

Previous concerns about missing wiring are resolved.

## Verification Update — AutoSave UI Wiring

Verified:
- Purchase window AutoSave connected.
  - QTimer interval: 60000 ms
  - timeout -> autosave()
  - autosave() -> draft_service.save_draft()

- Sales window AutoSave connected.
  - QTimer interval: 60000 ms
  - timeout -> autosave()
  - autosave() -> draft_service.save_draft()

Power Failure Protection status:
- Session Recovery: Verified
- Crash Detection: Verified
- Draft Save: Verified
- Draft Restore: Verified
- UI AutoSave: Verified
