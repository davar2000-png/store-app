# PHASE_REGISTRY.md

| Phase | عنوان | وضعیت | یادداشت |
|---|---|---|---|
| 1–9 | توسعه اولیه (هسته، خرید/انبار، فروش، مالی، ارتباطات، ...) | Completed | فقط به‌صورت ZIP در `archive/` موجود است |
| 10 | تنظیمات و مدیریت کاربران/دسترسی | Completed but superseded by Phase 11 | ماژول Settings و Permission ساخته شد اما در Phase 11 حذف شد |
| 11 | لیست فاکتورها، برگشت از خرید | Completed with known Regression | Settings و Permission ماژول ۱۰ را کامل حذف کرد |
| 12 | Stabilization + GitHub Normalization + Power Failure Foundation | **Completed (Partial Scope)** | جزئیات پایین |
| 13 / 13.5.1 | AutoSave/Draft Recovery در UI واقعی + Backup Hardening | Completed | 16 تست موفق |
| 14 | Audit Trail (Actor, Permission Changes, Password Changes, Audit Viewer, `audit.view` Permission با Fail-Closed) | Completed | Commit `66b5632` |
| 14.3 | Audit Reliability Hardening (رفع Bug بلعیدن بی‌صدای خطای نوشتن Audit) | Completed | جزئیات پایین |

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

## Phase 14.3 — Audit Reliability Hardening

**Commit:** `334a10c` (روی برنچ `phase/14-workflow-audit`, هنوز Push نشده — دلیل در `AI_HANDOFF.md`)

**مشکل شناسایی‌شده (Bug واقعی، نه صرفاً بهبود):**
`services/audit_service.py::create_audit_entry()` هر خطای نوشتن در `AuditLogs`
را با `except Exception: pass` کاملاً بی‌صدا می‌بلعید. یعنی اگر INSERT به هر
دلیلی (قطع DB، Schema Drift، قفل جدول و ...) شکست می‌خورد:
- Caller (`financial_service`, `settings_service`, `inventory_service`,
  `sales_service`, `draft_service`) هیچ‌وقت متوجه نمی‌شد — تابع همیشه یک
  دیکشنری «موفق به‌نظررسنده» برمی‌گرداند.
- هیچ خط Log ای هم ثبت نمی‌شد.

برای یک سیستم که کل هدفش قابلیت اثبات/ردیابی تراکنش‌های مالی و تغییرات
Permission است، شکست خاموش این‌جا مستقیماً با اولویت اول پروژه («پایداری و
صحت حسابداری») و اولویت دوم («امنیت و Permission») در تضاد است.

**تصمیم طراحی:**
Exception همچنان به بیرون Propagate نمی‌شود — شکست نوشتن Audit نباید یک
فروش/خرید/تسویه واقعی را متوقف یا Rollback کند؛ Audit ضمیمهٔ تراکنش است، نه
پیش‌نیاز آن. اما دیگر بی‌صدا نیست:
- خطا با `logging.getLogger(__name__).error(...)` (شامل `exc_info`) ثبت می‌شود.
- دیکشنری بازگشتی یک کلید جدید `audit_write_failed: bool` دارد تا در آینده
  Callerها (یا یک هشدار در UI) بتوانند در صورت نیاز واکنش نشان دهند.
- `db.close()` به `finally` منتقل شد تا در مسیر خطا هم Connection درست بسته شود.

**تست:**
`tests/test_audit_service.py` اضافه شد (مسیر موفق، مسیر شکست DB، عدم Propagate
شدن Exception، `log_action` alias، ترتیب نزولی `get_recent_logs`).
`tests/_fake_database.py` برای پشتیبانی از `INSERT`/`SELECT` روی `AuditLogs`
گسترش یافت.

نتیجه: `python -m pytest -q tests` → **21 passed** (۱۶ قبلی + ۵ جدید).

**عمداً در این Phase انجام نشد (خارج از Scope حداقلی):**
- `AuditViewerWindow` خودش چک Permission داخلی ندارد و فقط به Gate شدن در
  `MainWindow` تکیه می‌کند — این با الگوی بقیه پنجره‌های حساس پروژه
  (`SettingsWindow`, `BackupWindow`) یکسان است، پس یک Regression یا
  ناهم‌خوانی معماری نیست؛ تغییرش یک بازطراحی معماری سراسری می‌شود که طبق
  قانون «از تغییرات نمایشی/بازطراحی غیرضروری خودداری کن» خارج از Scope
  حداقلی این Phase گذاشته شد.

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
