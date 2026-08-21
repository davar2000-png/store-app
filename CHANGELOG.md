# CHANGELOG.md

## Phase 12 — Stabilization + GitHub Normalization

### Fixed
- بازیابی ماژول Settings (`services/settings_service.py`, `ui/settings_window.py`) که در Phase 11 حذف شده بود
- بازیابی کنترل دسترسی ماژول‌ها (`is_module_allowed`) در `ui/main_window.py` که در Phase 11 حذف شده بود؛ برای دو ماژول جدید Phase 11 (لیست فاکتورها، برگشت از خرید) هم کلید دسترسی تعریف شد
- تفکیک `database/schema.sql` (مخرب، DROP TABLE) به دو مفهوم مجزا: `database/schema/` (فقط نصب تازه) و `database/migrations/` (امن و غیرمخرب برای دیتابیس موجود)

### Added
- زیرساخت پایه Power Failure Protection: جداول `Sessions`/`Drafts` + `services/session_service.py` + `services/draft_service.py` (فقط Foundation، هنوز به UI وصل نشده)
- `.gitignore` (جلوگیری از ورود دوباره فایل‌های Backup/محیط به Repository)
- ۱۱ فایل مستندات پروژه (`PROJECT_STATE.md`, `PHASE_REGISTRY.md`, `AI_HANDOFF.md`, `ARCHITECTURE.md`, `DATABASE_SCHEMA.md`, `ACCOUNTING_RULES.md`, `SECURITY.md`, `BACKUP_POLICY.md`, `UI_DESIGN_SYSTEM.md`, `CHANGELOG.md`, `POWER_FAILURE_RECOVERY.md`)
- `tests/test_smoke.py` — تست پایه Import/Syntax

### Changed
- Source Code واقعی پروژه از حالت ZIP-محور به فایل مستقیم در ریشه Repository منتقل شد؛ ZIPهای قدیمی به `archive/` جابه‌جا شدند

### Security
- شناسایی دو فایل Backup واقعی SQL Server در Git History؛ حذف کامل از History (نیازمند Force Push) به تصمیم کاربر موکول شد — جزئیات در `SECURITY.md`

### Known Issues
- پاکسازی کامل Git History هنوز انجام نشده
- AutoSave/Draft Recovery هنوز به فرم‌های واقعی وصل نشده
