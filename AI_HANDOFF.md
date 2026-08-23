# AI_HANDOFF.md

> Account بعدی: این فایل را قبل از هر کاری بخوانید. به حافظه مکالمه قبلی
> اعتماد نکنید — GitHub مرجع اصلی است.

## LAST ACCOUNT
Claude (Phase 14.3 — Audit Reliability Hardening)

## CURRENT PHASE
14.3 — تکمیل‌شده (روی برنچ `phase/14-workflow-audit`)

## CURRENT BRANCH
`phase/14-workflow-audit`
(نکته: `main` هنوز فقط تا انتهای Phase 13.5.1 جلو رفته — `phase/14-workflow-audit`
هنوز به `main` Merge نشده. این تصمیم قبلی کاربر/اکانت قبل بوده، این اکانت آن
را تغییر نداد.)

## LAST COMMIT
`334a10c` — fix(phase 14.3): stop silently swallowing AuditLogs write failures
(روی `phase/14-workflow-audit`، **هنوز به origin Push نشده**)

### چرا Push نشده
این محیط Sandbox به هیچ Token/اعتبارنامه GitHub کاربر دسترسی ندارد (دقیقاً
همان محدودیتی که در نسخه قبلی این فایل هم ثبت شده بود). Commit به‌صورت محلی
روی همین Checkout ساخته شده و تست شده؛ خروجی به‌صورت Patch/Diff در اختیار
کاربر قرار گرفته تا با یک `git push` عادی (نه Force) روی
`phase/14-workflow-audit` اعمال شود.

## COMPLETED (این اکانت)
- Audit کامل Repository: `git status`, `git log`, ساختار پروژه، خواندن
  `PHASE_REGISTRY.md` / `PROJECT_STATE.md` / کد واقعی `services/audit_service.py`,
  `services/settings_service.py`, `ui/main_window.py`, `ui/audit_viewer_window.py`.
- تأیید Baseline: در لحظه شروع، `main` clean بود و `phase/14-workflow-audit`
  دقیقاً روی `66b5632` (طبق ادعای Handoff) — تطابق کامل.
- نصب وابستگی‌های محیط تست (`pyodbc`, `unixodbc`, `jdatetime`) — فقط برای
  اجرای تست در همین Sandbox، هیچ تغییری در `requirements.txt` نبود چون از
  قبل درست بود.
- شناسایی و رفع Bug واقعی: بلعیدن بی‌صدای خطای نوشتن `AuditLogs` در
  `create_audit_entry()` — جزئیات کامل در `PHASE_REGISTRY.md § Phase 14.3`.
- ۵ تست جدید برای `audit_service` + گسترش `FakeDatabase`.
- به‌روزرسانی `PHASE_REGISTRY.md`, `AI_HANDOFF.md` (همین فایل).

## NOT COMPLETED / تصمیم آگاهانه برای واگذاری به فاز بعد
- `phase/14-workflow-audit` هنوز به `main` Merge نشده.
- Workflow یکپارچه (Correlation ID سرتاسری بین خرید→انبار→فروش→مالی) طبق
  `PROJECT_STATE.md` هنوز Partial است — این خودِ Phase 14 آن را حل نکرد
  (Phase 14 فقط روی Audit/Permission تمرکز داشت)، و طبق اولویت پروژه
  («Workflow» رتبه ۴ از ۵) بعد از تثبیت لایه حسابداری باید انجام شود.
- **Accounting Engine دوطرفه واقعی هنوز پیاده‌سازی نشده** — این طبق
  `PHASE_REGISTRY.md` عمداً همیشه خارج از Scope فازهای قبلی نگه داشته شده،
  چون طبق اولویت اول پروژه («پایداری و صحت حسابداری») باید یک Phase
  مستقل و کاملاً متمرکز باشد، نه یک زیرکار داخل فاز دیگر.
- پاکسازی کامل Git History از فایل‌های Backup حساس هنوز انجام نشده (نیاز
  به تصمیم صریح کاربر برای Force Push دارد؛ از Phase 12 به تعویق افتاده).
- `AuditViewerWindow` فاقد چک Permission داخلی است (فقط به Gate شدن در
  `MainWindow` تکیه دارد) — عمداً در این Phase تغییر داده نشد چون با الگوی
  فعلی کل پروژه یکسان است، نه یک Regression مختص Phase 14.

## FILES CHANGED (این اکانت)
**تغییریافته:**
`services/audit_service.py`, `tests/_fake_database.py`, `PHASE_REGISTRY.md`, `AI_HANDOFF.md`

**ایجادشده:**
`tests/test_audit_service.py`

## DATABASE CHANGES
هیچ Migration جدیدی لازم نبود — Bug صرفاً در کد Python بود، نه Schema.
جدول `AuditLogs` (از Phase 14، `database/migrations/008_audit_logs.sql`) بدون تغییر باقی ماند.

## TESTS
`python -m pytest -q tests` → **21 passed** (۱۶ قبل از این اکانت + ۵ جدید).
`python -m py_compile services/audit_service.py tests/_fake_database.py tests/test_audit_service.py` → بدون خطا.

## KNOWN ISSUES (باقی‌مانده، اولویت‌بندی‌شده طبق اولویت پروژه)
1. 🟡 Accounting Engine دوطرفه واقعی وجود ندارد — طبق اولویت اول پروژه، این
   باید موضوع اصلی یکی از فازهای بعدی مستقل باشد.
2. 🟡 `phase/14-workflow-audit` هنوز Merge نشده به `main`.
3. 🟡 Workflow Correlation سرتاسری بین ماژول‌ها (خرید/فروش/انبار/مالی) کامل نیست.
4. 🔴 دو فایل Backup حساس هنوز در Git History (نه در نسخه فعلی) — از Phase 12.

## NEXT PHASE — پیشنهاد برای اکانت بعدی
15 — پیشنهاد مشخص طبق اولویت پروژه (حسابداری > امنیت > Database > Workflow > UX):
   الف) ابتدا `phase/14-workflow-audit` (شامل همین Commit Phase 14.3) را پس از
        بازبینی نهایی کاربر به `main` Merge کن.
   ب) سپس شروع Phase حسابداری دوطرفه: طراحی جدول `LedgerEntries`/`ChartOfAccounts`
      و اتصال آن به تراکنش‌های موجود (فروش، خرید، دریافت، پرداخت، چک) — این
      باید یک Phase مستقل با تست‌های اختصاصی باشد، نه یک تغییر جانبی.
   این پیشنهاد نهایی نیست؛ اکانت بعدی باید ابتدا خودش `git log` و وضعیت
   واقعی `main` در آن لحظه را بررسی کند، نه فقط به این فایل اعتماد کند.
