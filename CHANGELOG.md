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

## Phase 16B — Web Backend Skeleton

### Added
- `web/app.py`: اپلیکیشن FastAPI با `GET /`, `GET /health`,
  static mount در `/static`
- `web/templates/base.html`, `web/templates/home.html`: قالب Jinja2،
  RTL/فارسی
- `web/static/style.css`: استایل حداقلی، بدون framework
- `requirements-web.txt`: `fastapi==0.141.1`, `uvicorn==0.52.4`,
  `jinja2==3.1.6`
- `tests/test_web_skeleton.py`: ۱۰ تست جدید (home 200/HTML/RTL/title,
  health 200/status/database field, static css, 404)

### Verified
- FastAPI TestClient: 10/10 passed
- Full regression suite: 217 passed (۲۰۷ قبلی + ۱۰ جدید)
- اجرای واقعی `uvicorn` روی `127.0.0.1:8000` + تست با `curl`
  (HTTP smoke test واقعی، نه فقط TestClient)

### Not Verified
- تست با مرورگر Chrome واقعی — هنوز انجام نشده

### Unchanged
- `ui/`, `services/`, `database/`, `utils/`, `main.py`, `config.py`,
  `requirements.txt`, هیچ migration ای
