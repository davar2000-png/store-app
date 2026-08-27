# AI_HANDOFF.md

> Account بعدی: این فایل را قبل از هر کاری بخوانید. به حافظه مکالمه قبلی
> اعتماد نکنید — GitHub مرجع اصلی است. همیشه `git log --oneline -10` و
> `git status` را خودتان اجرا کنید، حتی اگر این فایل چیز دیگری می‌گوید.

## LAST ACCOUNT
Claude Sonnet 5 (همین مکالمه — Phase 17: Merge)

## CURRENT PHASE
17 — Merge برنچ `phase/14-workflow-audit` (Phase 13.5.1 تا 16B) به `main`،
به دستور صریح کاربر پس از تصمیم قطعی: پروژهٔ قبلی (تحلیل و اتصال به
`RoboAccDB_Legacy`) کنار گذاشته شد؛ ادامهٔ کار روی `StoreAppDB` مستقل است.

## CURRENT BRANCH
`main` — merge با `git merge --no-ff origin/phase/14-workflow-audit` انجام و
commit شد، اما **هنوز Push نشده**.

## LAST COMMIT (قبل از این Merge)
`7a7ed16` — Add files via upload

## PUSH STATUS — مهم 🔴
این Account (مثل Accountهای قبلی) به Token/اعتبارنامهٔ GitHub کاربر دسترسی
مستقیم ندارد و نمی‌تواند `git push` بزند. نتیجهٔ کار به یکی از این دو شکل به
کاربر تحویل داده شده (به پیام نهایی همین مکالمه در چت مراجعه شود):
- یک ZIP/Bundle قابل دانلود از کل ریپو با تاریخچهٔ merge شده، یا
- یک Patch/Bundle از merge commit که کاربر باید با `git pull`/`git am`/
  اعمال دستی روی نسخهٔ محلی خودش از `main` اجرا کند و بعد `git push` بزند.

**کاربر باید بعد از Push، این وضعیت را با `git log --oneline -5` روی
`main` تأیید کند و برنچ `phase/14-workflow-audit` را (پس از اطمینان) حذف کند.**

## COMPLETED (این اکانت)
- بررسی کامل مخزن: `git log --all`, `git branch -a`، خواندن
  `PROJECT_STATE.md`, `AI_HANDOFF.md`, `PHASE_REGISTRY.md`
- کشف اینکه `main` واقعاً تا Phase 13.5.1 پیش رفته بود (نه Phase 12 طبق
  مستندات قدیمی) و کار بزرگ Phase 14 تا 16B فقط روی برنچ جدا مانده بود
- Merge محلی `origin/phase/14-workflow-audit` → `main` با `--no-ff`؛
  **بدون هیچ Conflict** (Automatic merge went well)
- نصب وابستگی‌های تست در Sandbox (`unixodbc`, `pyodbc`, `fastapi`, `httpx`)
  و اجرای کامل Test Suite بعد از Merge
- نتیجه: **217 passed, 0 failed** — هیچ Regression ایجاد نشد
- به‌روزرسانی `PROJECT_STATE.md` و همین فایل برای انعکاس وضعیت واقعی

## NOT COMPLETED
- Push واقعی merge commit به GitHub (این Account دسترسی ندارد)
- حذف برنچ `phase/14-workflow-audit` بعد از تأیید merge توسط کاربر
- پاکسازی کامل Git History از دو فایل Backup حساس
  (`TECHNOKALARoboAccBackUp_...`) — همچنان معلق، نیاز به تصمیم صریح
  کاربر دربارهٔ Force Push
- پاکسازی فایل‌های Patch یتیم روی ریشهٔ ریپو
  (`phase-13.1-e67cac9.patch`, `phase-13.1-final-452f9d5.patch`,
  `phase-13.2-ed70f85.patch`) — محتوایشان از قبل روی `main` اعمال شده،
  پاک کردنشان بی‌خطر است اما در این فاز عمداً دست نخورده باقی ماندند
- تست مرورگر Chrome واقعی برای Web Skeleton (طبق یادداشت خود Phase 16B)
- Phase 16C (Auth Extraction + Session Login) — شروع نشده

## FILES CHANGED (این Merge)
41 فایل، +6759/-80 خط. مهم‌ترین‌ها:
- **جدید:** `services/accounting_service.py`, `services/audit_service.py`,
  `ui/audit_viewer_window.py`,
  `database/migrations/008_audit_logs.sql` تا `014_sales_return.sql`,
  `web/` (کامل — FastAPI Skeleton)، ۸ فایل تست جدید
- **تغییریافته:** `services/sales_service.py`, `services/financial_service.py`,
  `services/inventory_service.py`, `ui/main_window.py`, `ui/sales_window.py`,
  `ui/purchase_window.py`, `ui/settings_window.py` و چند فایل کوچک دیگر

## DATABASE CHANGES
هیچ تغییری روی دیتابیس واقعی کاربر اعمال نشد (Sandbox دسترسی ندارد).
Migrationهای جدید `008` تا `014` باید به ترتیب روی `StoreAppDB` واقعی
کاربر اجرا شوند تا Chart of Accounts، Journal Entries و اتصال کامل
فروش/خرید/دریافت/پرداخت/برگشت به دفتر حسابداری دوطرفه فعال شود.
همه additive و Idempotent هستند (`IF OBJECT_ID(...) IS NULL`).

## TESTS
`python3 -m pytest -q tests` روی نسخهٔ merge‌شده در Sandbox اجرا شد:
```
217 passed, 1 warning in 0.68s
```
هشدار تنها مربوط به Deprecation در کتابخانهٔ `starlette`/`httpx` است، نه
منطق پروژه. **اتصال واقعی به SQL Server تست نشد** (Sandbox به دیتابیس
کاربر دسترسی ندارد) — دقیقاً مثل فازهای قبلی.

## KNOWN ISSUES (بدون تغییر از قبل)
1. 🔴 دو فایل Backup حساس هنوز در Git History
2. Push این Merge هنوز انجام نشده — نیاز به اقدام کاربر
3. برنچ `phase/14-workflow-audit` هنوز حذف نشده (تا تأیید نهایی کاربر)
4. Web Skeleton هنوز با Chrome واقعی تست نشده

## NEXT PHASE
18 — پیشنهاد: بعد از Push موفق توسط کاربر و تأیید `main` روی GitHub،
تصمیم بگیرید که آیا Phase 16C (Auth Extraction) ادامه یابد یا اولویت با
پاکسازی امن Git History (فایل‌های Backup حساس) باشد.
