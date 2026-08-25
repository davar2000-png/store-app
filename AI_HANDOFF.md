# AI_HANDOFF.md

> Account بعدی: این فایل را قبل از هر کاری بخوانید. به حافظه مکالمه قبلی
> اعتماد نکنید — GitHub مرجع اصلی است.

## LAST ACCOUNT
Claude (Phase 15.2 — اتصال فروش به حسابداری دوطرفه)

## CURRENT PHASE
15.2 — تکمیل‌شده (روی برنچ `phase/14-workflow-audit`)

## CURRENT BRANCH
`phase/14-workflow-audit`
(همچنان به `main` Merge نشده — این تصمیم از Phase 14.3 به بعد ادامه دارد
و توسط این اکانت هم تغییر داده نشد؛ کاربر باید Merge را وقتی صلاح دید
انجام دهد.)

## LAST COMMIT
جزئیات کامل Commit hashها در پیام نهایی همین Account به کاربر گزارش شده
(چون این Account دسترسی Push نداشت — بخش «PUSH STATUS» پایین را ببینید).
از `git log --oneline -6` روی `phase/14-workflow-audit` مطمئن شوید.

## COMPLETED (این اکانت)
- Audit کامل مطابق دستور Brief: `git log`, `git status`، خواندن کامل
  `PHASE_REGISTRY.md`/`AI_HANDOFF.md`/`ACCOUNTING_RULES.md`، بررسی کامل
  `services/sales_service.py`, `services/accounting_service.py`,
  `services/financial_service.py`, `services/inventory_service.py`، و
  اجرای کامل تست‌ها قبل از هر تغییر (Baseline: 35 passed، مطابق دقیق
  Brief).
- تأیید Baseline: کد واقعی روی GitHub دقیقاً با Brief مطابقت داشت
  (`7e0167d`، 35 تست موفق، Working Tree Clean).
- شناسایی و گزارش یک ابهام حسابداری واقعی (نه حدس‌زده): `TaxAmount`
  فیلدی فعال در فاکتور فروش/خرید است اما Chart of Accounts هیچ حساب
  بدهی برای مالیات دریافتی نداشت. حداقل رفع: یک Migration جدید
  (`010_accounting_tax_payable.sql`) که فقط حساب `2200` را اضافه می‌کند.
- Refactor کوچک و Backward-Compatible روی `services/accounting_service.py`:
  استخراج هسته ثبت سند به `_post_journal_entry_on_cursor(cursor, ...)`
  (بدون commit/rollback خودش) تا سرویس‌های تجاری بتوانند سند حسابداری را
  در همان Transaction اتمیک خودشان ثبت کنند. `post_journal_entry()`
  عمومی بدون تغییر رفتار/Signature باقی ماند؛ هر ۱۴ تست Phase 15.1 بدون
  هیچ تغییری سبز ماندند.
- `tests/test_sales_service.py` (جدید، قبل از تغییر `sales_service.py`
  نوشته شد): پوشش کامل Regression رفتار فعلی فروش (FIFO تک/چندلایه،
  کمبود موجودی، `AllowNegativeStock`، کاردکس، سریال/IMEI، اعتبارسنجی
  ورودی) + تست‌های جدید اتصال Ledger (موازنه، ردیف مالیات شرطی، مرجع
  Source، افزایش EntryNumber، Rollback کامل فاکتور در صورت خطای Ledger).
- اتصال واقعی `services/sales_service.py::create_sales_invoice()` به
  Ledger: یک سند حسابداری ترکیبی (AR/درآمد/مالیات + COGS/موجودی) در همان
  Transaction اتمیک فاکتور فروش ثبت می‌شود؛ جزئیات کامل طراحی در
  `PHASE_REGISTRY.md § Phase 15.2`.
- `py_compile` روی فایل‌های تغییرکرده و `git diff --check` تمیز.
- به‌روزرسانی `database/README.md`, `PHASE_REGISTRY.md`, `AI_HANDOFF.md`
  (همین فایل).

## NOT COMPLETED / آگاهانه واگذارشده به فاز بعد
این خودِ مأموریت صریح فازهای بعدی است، نه یک نقص:
- **خرید (Purchase) هنوز به Ledger وصل نیست.** پیشنهاد قبلی Phase 15.1
  همچنان معتبر است: خرید ساده‌ترین فاز بعدی است (بدهکار موجودی کالا،
  بستانکار حساب‌های پرداختنی + مالیات پرداختنی در صورت وجود؛ ساختار
  آینه‌ای همین فاز).
- **دریافت/پرداخت (Receipt/Payment) هنوز به Ledger وصل نیستند.** این‌ها
  باید کاهش AR/AP در برابر افزایش/کاهش صندوق یا بانک را ثبت کنند —
  می‌توانند به همان `_post_journal_entry_on_cursor` که این فاز اضافه کرد
  متکی باشند (به همان روش که این فاز به آن متکی شد).
- برگشت از فروش/خرید، چک، اقساط — هیچ‌کدام هنوز به Ledger وصل نیستند.
- هیچ Ledger Viewer/UI ای ساخته نشده — طبق اولویت پروژه (UI آخرین
  اولویت است).
- `phase/14-workflow-audit` هنوز به `main` Merge نشده.
- پاکسازی کامل Git History از فایل‌های Backup حساس هنوز انجام نشده (از
  Phase 12 به تعویق افتاده، نیاز به تصمیم صریح کاربر برای Force Push).

## FILES CHANGED (این اکانت)
**ایجادشده:**
`database/migrations/010_accounting_tax_payable.sql`,
`tests/test_sales_service.py`

**تغییریافته:**
`services/sales_service.py` (اتصال به Ledger — `_build_sales_journal_lines`
+ فراخوانی `_post_journal_entry_on_cursor` قبل از `conn.commit()`)،
`services/accounting_service.py` (Refactor: استخراج
`_post_journal_entry_on_cursor`؛ هیچ تغییر رفتاری در `post_journal_entry()`
عمومی)،
`database/README.md`, `PHASE_REGISTRY.md`, `AI_HANDOFF.md`

## DATABASE CHANGES
یک Migration جدید و امن (`010_accounting_tax_payable.sql`، همان الگوی
`IF NOT EXISTS ... WHERE Code = ...` بقیه Seedها) که باید توسط کاربر روی
دیتابیس واقعی‌اش اجرا شود (بعد از `009_accounting_core.sql`، قبل از
استفاده واقعی از فروش با مالیات غیرصفر — وگرنه `post_journal_entry` با
خطای «حساب با کد 2200 یافت نشد» کل فاکتور را Rollback می‌کند، طبق طراحی
عمدی این فاز). هیچ جدول موجودی تغییر یا حذف نشد.

## TESTS
`python -m pytest -q tests` → **56 passed** (۳۵ قبل از این اکانت + ۲۱ جدید،
هیچ‌کدام از ۳۵ تست قبلی تغییر نکردند).
`python -m py_compile services/sales_service.py services/accounting_service.py tests/test_sales_service.py` → بدون خطا.
`git diff --check` → بدون خطای Whitespace.

⚠️ محیط Sandbox این Account به‌صورت پیش‌فرض `libodbc.so.2` و `jdatetime`
نداشت (لازم برای Import شدن `database/db.py` و `utils/persian_date.py`)؛
با `apt-get install unixodbc unixodbc-dev` و `pip install jdatetime` رفع
شد. اگر Account بعدی با همین خطا مواجه شد، دلیلش نقص در `sales_service.py`
نیست — نقص محیط است.

## PUSH STATUS
این Account به Repository دسترسی Push نداشت (بدون Token/Credential در
Sandbox). تمام تغییرات به‌صورت Commitهای محلی روی `phase/14-workflow-audit`
(بر پایه دقیق `7e0167d`) آماده و تست‌شده‌اند، اما **Push نشده‌اند** —
کاربر باید آن‌ها را از طریق Patch/Bundle ارائه‌شده در پیام نهایی، اعمال و
Push کند (دقیقاً همان روشی که طبق یادداشت Phase 14.3 قبلاً هم جواب داده
بود).

## NEXT PHASE — پیشنهاد مشخص برای اکانت بعدی (15.3)
اتصال **خرید (Purchase)** به Ledger — آینه دقیق همین فاز:
```
بدهکار   1200 موجودی کالا            = SUM(qty*price - discount اقلام)
بدهکار   2200 مالیات (اگر مدل شود؛ برای خرید معمولاً «مالیات قابل کسر»
              است نه بدهی — این را حتماً با دقت طراحی کن، مستقیماً کپی
              رفتار فروش نکن چون جهت حسابداری آن معکوس است)
بستانکار 2000 حساب‌های پرداختنی      = PayableAmount
```
نکات مهم برای اکانت بعدی:
- از همان `services.accounting_service._post_journal_entry_on_cursor`
  استفاده کن، دقیقاً مثل این فاز — سیستم حسابداری موازی نساز.
- قبل از تغییر `inventory_service.py::create_purchase_invoice`، حتماً یک
  فایل Regression مثل `tests/test_sales_service.py` برای آن بنویس (فعلاً
  صفر تست دارد).
- به AR/COGS خرید حساسیت خاص نشان بده — بر خلاف فروش، خرید COGS ندارد
  (کالا وارد انبار می‌شود، از انبار خارج نمی‌شود)؛ سند خرید فقط یک زوج
  بدهکار/بستانکار ساده‌تر لازم دارد (موجودی در برابر پرداختنی)، نه دو
  زوج مثل فروش. این را حدس نزن — اگر ابهامی در جهت مالیات خرید (بدهکار
  یا بستانکار) دیدی، طبق قانون Brief متوقف کن و گزارش بده.

---

## Phase 16B — Web Backend Skeleton (Handoff Update)

**Base commit:** `2a73b9a` (Phase 15.6.5 — Sales Return Core)
**Code commit:** `3b9fccd` — `feat(web): add FastAPI chrome test skeleton`
**Branch:** `phase/14-workflow-audit`

فایل‌های اضافه‌شده (append-only، هیچ فایل موجودی تغییر نکرد):
```text
web/__init__.py
web/app.py
web/templates/base.html
web/templates/home.html
web/static/style.css
requirements-web.txt
tests/test_web_skeleton.py
```

## TESTS
`python -m pytest tests/ -q` → **217 passed** (۲۰۷ قبل از این فاز + ۱۰ جدید
Web Skeleton، هیچ‌کدام از تست‌های قبلی تغییر نکردند).

سرور علاوه بر TestClient با `uvicorn` واقعی روی `127.0.0.1:8000` اجرا و با
`curl` تست شد (`GET /` → 200, `GET /health` → 200, `GET /static/style.css`
→ 200, `GET /nonexistent-route` → 404). **این محیط sandbox درایور ODBC/SQL
Server واقعی ندارد**، پس `/health` صادقانه `not_connected` گزارش می‌دهد —
این رفتار مورد انتظار است، نه یک باگ.

**تأیید Chrome واقعی هنوز انجام نشده است.** این با HTTP smoke test فرق
دارد و نباید به‌جای آن جا زده شود.

## PUSH STATUS
این commit روی `phase/14-workflow-audit` (بر پایه `2a73b9a`) محلی ساخته شد؛
وضعیت Push دقیق در گزارش نهایی همین Session ثبت می‌شود.

## NEXT PHASE — پیشنهاد برای Account/Session بعدی (16C)
Auth Extraction + Session Login:
- ابتدا `services/auth_service.py` را از منطق موجود در
  `ui/login_window.py` استخراج کن (که مستقیماً `database.db.Database` و
  `utils.security.verify_password` را مصرف می‌کند) — این استخراج باید
  additive باشد و رفتار Desktop را عوض نکند.
- سپس یک session-based login برای وب روی همان `services/auth_service.py`
  بساز، نه یک پیاده‌سازی موازی.
- طبق قانون Brief، **این فاز فقط بعد از تأیید صریح کاربر شروع شود.**
