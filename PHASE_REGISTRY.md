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
| 15.1 | Accounting Core Foundation (Chart of Accounts + Journal Entries دوطرفه، هنوز وصل‌نشده) | Completed | جزئیات پایین |
| 15.2 | اتصال فروش به حسابداری دوطرفه (اولین تراکنش تجاری واقعی متصل به Ledger) | Completed | جزئیات پایین |

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

## Phase 15.1 — Accounting Core Foundation

**Commit:** `fd8c811` (روی برنچ `phase/14-workflow-audit`)

**تحلیل وضعیت واقعی قبل از شروع (طبق دستور Brief):**
بررسی کامل `database/migrations/*.sql` و `services/financial_service.py`,
`services/sales_service.py`, `services/inventory_service.py` نشان داد:
- **هیچ Chart of Accounts یا Journal Entry دوطرفه‌ای در کل پروژه وجود ندارد.**
- آنچه از قبل وجود دارد، مجموعه‌ای از Sub-Ledgerهای تک‌طرفه ولی خوب‌ساخته
  است: `CashBoxTransactions`/`BankTransactions` با `BalanceAfter` در حال
  رشد، `SalesInvoices`/`PurchaseInvoices.PaidAmount` برای بدهکار/بستانکار
  اشخاص، و بهای تمام‌شده FIFO که از قبل به‌ازای هر ردیف فروش محاسبه و در
  `SalesInvoiceItems.CostAmount` ذخیره می‌شود.
- هیچ‌کدام از این‌ها به یک Ledger موازنه‌شده (بدهکار=بستانکار) Post
  نمی‌شوند.
- این نتیجه‌گیری با یادداشت قدیمی `PHASE_REGISTRY.md § Phase 12`
  («Accounting Engine — عمداً خارج از Scope») هم‌خوانی داشت.

**تصمیم Scope (طبق دستور «زیرمرحله مستقل، نه همه‌چیز یک‌جا»):**
این فاز فقط **موتور** حسابداری دوطرفه را می‌سازد؛ به‌صورت عمدی به هیچ
تراکنش تجاری موجود وصل نمی‌شود. اتصال واقعی (فروش، خرید، دریافت، پرداخت،
...) در فازهای 15.2 به بعد انجام می‌شود تا هر اتصال جداگانه قابل تست و
Rollback باشد.

**ساخته‌شده:**
- `database/migrations/009_accounting_core.sql`: `ChartOfAccounts`,
  `JournalEntries` (سربرگ)، `JournalEntryLines` (اقلام بدهکار/بستانکار)
  + یک Chart of Accounts حداقلی Seed شده (صندوق/بانک، دریافتنی‌ها،
  موجودی کالا، پرداختنی‌ها، اسناد دریافتنی/پرداختنی، حقوق صاحبان سرمایه،
  درآمد فروش، برگشت از فروش، بهای تمام‌شده کالای فروش‌رفته).
- `services/accounting_service.py`: `post_journal_entry()` با اعتبارسنجی
  کامل قبل از لمس دیتابیس (حداقل ۲ ردیف، هر ردیف فقط یک طرف بدهکار/
  بستانکار، جمع بدهکار = جمع بستانکار با تلورانس گرد شدن، همه حساب‌ها باید
  وجود و فعال باشند)، اتمیک (Commit/Rollback مطابق الگوی خود پروژه در
  `financial_service.py`)، و برای هر سند با `create_audit_entry` موجود
  (نه یک سیستم Audit موازی) ثبت Log می‌شود.
- ۱۴ تست جدید در `tests/test_accounting_service.py` (قوانین اعتبارسنجی
  خالص + یک Fake Cursor/Connection سبک برای مسیر واقعی دیتابیس، شامل
  تست Rollback کامل در صورت شکست).
- `services.accounting_service` به لیست Import در `test_smoke.py` اضافه شد.

**تست:** `python -m pytest -q tests` → **35 passed** (۲۱ قبلی + ۱۴ جدید).

**عمداً در این فاز انجام نشد:**
- هیچ سرویس موجودی (`financial_service`, `sales_service`,
  `inventory_service`) به `post_journal_entry` وصل نشده.
- هیچ رابط UI (Ledger Viewer) ساخته نشده — طبق اولویت پروژه (UI آخرین
  اولویت است) و چون هنوز هیچ سند واقعی Post نشده که چیزی برای نمایش باشد.

## Phase 15.2 — اتصال فروش به حسابداری دوطرفه

**Commits:** روی برنچ `phase/14-workflow-audit` (لیست کامل در `AI_HANDOFF.md`)

**تحلیل وضعیت واقعی قبل از شروع (طبق دستور Brief):**
بررسی کامل `services/sales_service.py::create_sales_invoice()` نشان داد:
- سربرگ فاکتور + اقلام + کسر از قدیمی‌ترین لایه‌های FIFO + فروخته‌شدن
  سریال/IMEI + بروزرسانی `Products.CurrentStock` + `ProductCardex`، همه در
  یک Transaction اتمیک واحد (یک `Database().connect()` + یک `cursor`) روی
  `sales_service.py` انجام می‌شود؛ `conn.commit()` فقط یک‌بار در انتها،
  `except: conn.rollback(); raise` برای هر خطا.
- بهای تمام‌شده هر ردیف فاکتور از قبل به‌درستی در
  `SalesInvoiceItems.CostAmount` محاسبه و ذخیره می‌شود (خروجی همان مسیر
  FIFO موجود؛ این فاز به آن دست نزد).
- `services/sales_service.py` **هیچ تست**ی نداشت (صفر) — دقیقاً همان
  چیزی که `AI_HANDOFF.md` هشدار داده بود.
- Chart of Accounts موجود (از Phase 15.1) شامل ۱۱۰۰ (دریافتنی)، ۱۲۰۰
  (موجودی کالا)، ۴۰۰۰ (درآمد فروش)، ۵۰۰۰ (بهای تمام‌شده) بود اما **هیچ
  حساب بدهی برای مالیات دریافتی از مشتری نداشت**، درحالی‌که `TaxAmount`
  یک فیلد واقعی و فعال است (`ui/sales_window.py::tax_input`).

**ابهام حسابداری شناسایی‌شده (طبق قانون Brief گزارش شد، حدس زده نشد):**
بدون یک حساب بدهی برای مالیات، سند حسابداری فروش وقتی `TaxAmount > 0`
باشد یا موازنه نمی‌شد یا باید مالیات را حدسی به یک حساب نامرتبط (مثلاً
خود درآمد فروش) بستانکار می‌کرد که هر دو رفتار نادرست حسابداری است.
**تصمیم:** حداقل تغییر لازم اضافه شد — نه بازطراحی Chart of Accounts:
`database/migrations/010_accounting_tax_payable.sql` فقط یک حساب جدید
(`2200` — مالیات دریافتنی از مشتری / پرداختنی به سازمان مالیاتی، نوع
Liability) به‌همان روش Idempotent بقیه Seedها اضافه می‌کند.

**طراحی سند حسابداری فروش (`services/sales_service.py::_build_sales_journal_lines`):**
یک سند ترکیبی (Compound Journal Entry) به‌ازای هر فاکتور فروش:
```
بدهکار   1100 حساب‌های دریافتنی   = PayableAmount
بستانکار 4000 درآمد فروش          = TotalAmount − DiscountAmount
بستانکار 2200 مالیات دریافتنی     = TaxAmount   (فقط اگر > 0)
---
بدهکار   5000 بهای تمام‌شده کالای فروش‌رفته = SUM(CostAmount اقلام فاکتور)
بستانکار 1200 موجودی کالا                    = SUM(CostAmount اقلام فاکتور)
```
ردیف‌های با مبلغ صفر (مثلاً بدون مالیات) اصلاً ساخته نمی‌شوند. اگر کل سند
خالی شود (فاکتور با ارزش و بهای صفر — Edge Case نظری)، هیچ سندی Post
نمی‌شود؛ فاکتور بدون رویداد حسابداری معنادار باقی می‌ماند که خودش صحیح
است، نه یک نقص.

**Atomicity (طبق قانون صریح Brief، حدس زده نشد):**
`accounting_service.post_journal_entry()` قبلی همیشه Connection مستقل
خودش را باز می‌کرد — فراخوانی آن از داخل `create_sales_invoice()` هیچ
تضمین اتمیکی واقعی با تراکنش فروش نمی‌داد (دو Connection جدا روی SQL
Server، نه یک Transaction). به‌جای حدس زدن یا استفاده از راه‌حل ضعیف‌تر
(دو Commit جدا)، `accounting_service.py` Refactor شد: هسته ثبت سند
(اعتبارسنجی + INSERT سربرگ/ردیف‌ها) به یک تابع داخلی جدید
`_post_journal_entry_on_cursor(cursor, ...)` منتقل شد که هیچ commit/
rollback/close ای انجام نمی‌دهد — کاملاً بی‌طرف نسبت به Transaction
فراخوان. `post_journal_entry()` عمومی (بدون تغییر رفتار بیرونی، همان
Signature و همان ۱۴ تست Phase 15.1 بدون تغییر سبز) حالا فقط یک Wrapper
نازک روی همین تابع است که Connection/Commit/Rollback/Audit مستقل خودش را
مدیریت می‌کند. `sales_service.create_sales_invoice()` مستقیماً همان
`cursor` باز خودش را به `_post_journal_entry_on_cursor` می‌دهد — یعنی
فاکتور فروش و سند حسابداری آن حالا **واقعاً یک Transaction اتمیک واحد
روی SQL Server** هستند: یا هر دو با هم Commit می‌شوند، یا هر خطایی (شامل
حساب گم‌شده/غیرفعال، یا موازنه‌نبودن) کل فاکتور (سربرگ، اقلام، کسر FIFO،
موجودی، کاردکس، سریال/IMEI) را هم Rollback می‌کند. این دقیقاً همان تصمیم
طراحی است که `ACCOUNTING_RULES.md` مطالبه می‌کند: «سندی که موازنه نداشته
باشد هرگز نباید Post شود» — و اینجا یک قدم جلوتر: فاکتوری که سند
حسابداری موازنه‌شده متناظرش ساخته نشود هم هرگز نباید Persist شود.

**تفاوت عمدی با الگوی Audit (Phase 14.3):**
`create_audit_entry` طبق تصمیم صریح Phase 14.3 عمداً Best-Effort است (خطای
نوشتن Audit هرگز فروش واقعی را متوقف نمی‌کند، چون Audit ضمیمهٔ تراکنش است
نه پیش‌نیاز آن). سند حسابداری برعکس است: طبق `ACCOUNTING_RULES.md` و رکن
اول اولویت پروژه («پایداری و صحت حسابداری»)، پیش‌نیاز محسوب می‌شود — پس
اگر Post نشود، کل فاکتور فروش هم Rollback می‌شود. این یک ناهم‌خوانی
معماری نیست؛ دو رویداد متفاوت با دو سطح ضرورت متفاوت‌اند و این فاز آگاهانه
هرکدام را طبق قوانین مخصوص خودشان رفتار داده.

**Regression Tests (قبل از هرگونه تغییر در sales_service.py اضافه شد):**
`tests/test_sales_service.py` — پوشش کامل رفتار *فعلی* فروش (که هیچ‌کدام
نباید با اتصال Ledger بشکند): اعتبارسنجی ورودی (آیتم خالی، تعداد/قیمت
نامعتبر، تعداد سریال نادرست)، FIFO تک‌لایه و چندلایه، خطای کمبود موجودی و
Rollback کامل آن، حالت `AllowNegativeStock` فعال، بروزرسانی
`CurrentStock`/`ProductCardex`، فروخته‌شدن سریال/IMEI، رد سریال غیرموجود.

**تست‌های جدید اتصال Ledger:** سند موازنه‌شده با حساب‌های درست، وجود ردیف
مالیات فقط وقتی `TaxAmount > 0`، افزایش `EntryNumber` بین چند فاکتور،
مرجع `SourceTable`/`SourceID` صحیح، Rollback کامل فاکتور در صورت نبود
یک حساب در Chart of Accounts (تست صریح Atomicity)، و تست خالص
`_build_sales_journal_lines` (بدون دیتابیس) برای قوانین موازنه/فیلتر
ردیف صفر/اعمال تخفیف روی درآمد نه روی طلب مشتری.

نتیجه: `python -m pytest -q tests` → **56 passed** (۳۵ قبلی + ۲۱ جدید،
همه ۳۵ تست قبلی بدون هیچ تغییری سبز ماندند).

**عمداً در این فاز انجام نشد (طبق قانون صریح Brief):**
- خرید، دریافت، پرداخت، برگشت، چک/اقساط — هیچ‌کدام تغییر نکردند و هنوز به
  Ledger وصل نیستند (زیرفازهای بعدی).
- هیچ Ledger Viewer/UI ای ساخته نشده.
- بازطراحی کلی Chart of Accounts انجام نشد — فقط یک حساب واقعاً لازم
  (مالیات) اضافه شد.

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

## Phase 16B — Web Backend Skeleton

**Base commit:** `2a73b9a` (Phase 15.6.5 — Sales Return Core)
**Code commit:** `3b9fccd` — `feat(web): add FastAPI chrome test skeleton`

هدف: افزودن یک اسکلت واقعی FastAPI + Jinja2 برای اجرای StoreApp در مرورگر،
بدون بازنویسی هیچ business logic ای در `services/`.

**فایل‌های اضافه‌شده (فقط این‌ها):**
```text
web/__init__.py
web/app.py
web/templates/base.html
web/templates/home.html
web/static/style.css
requirements-web.txt
tests/test_web_skeleton.py
```

**نسخه‌ها:** `fastapi==0.141.1`, `uvicorn==0.52.4`, `jinja2==3.1.6`
(`httpx` عمداً اضافه نشد — فقط برای TestClient تست‌ها لازم است، نه Runtime وب.)

**Endpointها:**
- `GET /` → HTML واقعی، RTL/فارسی، از طریق Jinja2 template
- `GET /health` → گزارش واقعی وضعیت دیتابیس (بدون Fake کردن اتصال؛ در نبود
  ODBC/SQL Server، `not_connected` همراه با خطای واقعی گزارش می‌شود)
- `GET /static/style.css` → فایل استاتیک

**تست:**
- `tests/test_web_skeleton.py` → 10 passed
- Full suite → 217 passed (۲۰۷ قبلی + ۱۰ جدید)
- علاوه بر TestClient، سرور با `uvicorn` واقعاً روی `127.0.0.1:8000` اجرا و
  با `curl` بررسی شد (HTTP smoke test واقعی).

**عمداً در این فاز انجام نشد:**
- تست با مرورگر Chrome واقعی — **هنوز تأیید نشده است.**
- هیچ Auth/Session ای پیاده‌سازی نشد (برای Phase 16C).
- هیچ migration، تغییر schema، یا تغییر در `services/`/`database/`/`ui/`.

**فاز بعدی:** 16C — Auth Extraction + Session Login — شروع نشده، منوط به
تأیید صریح کاربر.

## Phase 16C — Auth Extraction + Session Login

**Base commit:** `2ece6da` (Phase 16B — Web Backend Skeleton)
**Branch:** `phase/16c-auth-extraction`

هدف: افزودن لایه مستقل Authentication و Session Management برای وب،
بدون حذف یا بازنویسی هیچ منطق موجود (`ui/login_window.py`,
`services/session_service.py`, `utils/security.py` همگی دست‌نخورده
باقی ماندند).

**خارج از محدوده این فاز (طبق تصمیم صریح پروژه):**
- HTML Login UI — به Phase16D موکول شد؛ `/login` و `/logout` فقط API
  سطح JSON هستند.
- Dashboard و گزارش‌های وب.
- هرگونه تغییر در معماری/جداول Legacy حسابداری
  (`DocHeader → Transaction → DetailAccounts`, `Customers`, `Factors`,
  `Cashs`, `CashBox`, `ChequeRecs`, `ChequePays`).

**فایل‌های اضافه‌شده:**
```text
services/auth_service.py
services/web_session_service.py
database/migrations/015_web_sessions.sql
tests/test_auth_service.py
tests/test_web_session_service.py
tests/test_web_login.py
```

**فایل‌های تغییریافته:**
```text
tests/_fake_database.py   (افزوده شدن پشتیبانی Users/WebSessions؛ رفتار
                            قبلی Sessions/Drafts/AuditLogs دست‌نخورده)
web/app.py                (افزوده شدن POST /login و POST /logout؛
                            GET / و GET /health دست‌نخورده)
```

**جدول جدید:** `WebSessions` (`database/migrations/015_web_sessions.sql`)
— کاملاً مستقل از جدول `Sessions` موجود (که برای بازیابی قطع برق
دسکتاپ است). فقط `TokenHash` (نه توکن خام) ذخیره می‌شود. **این
Migration اجرا نشده است** — طبق قانون پروژه، فقط فایل SQL نوشته شده تا
پیش از ورود قطعی Phase16C به صورت دستی و آگاهانه اجرا شود.

**معماری:**
```
web/app.py (POST /login, POST /logout)
        │
        ├──▶ services/auth_service.py ──▶ utils/security.py (موجود)
        │           │
        │           └──▶ database/db.py ──▶ Users (فقط SELECT + UPDATE LastLogin)
        │
        └──▶ services/web_session_service.py ──▶ database/db.py ──▶ WebSessions (جدید)
```

- توکن Session به‌صورت `secrets.token_urlsafe(32)` ساخته می‌شود، فقط هش
  SHA-256 آن در دیتابیس ذخیره می‌شود، و توکن خام در یک Cookie با
  `HttpOnly` قرار می‌گیرد.
- خطای اتصال دیتابیس در `/login`/`/logout` به‌صورت پاسخ صادقانه `503`
  گزارش می‌شود (نه یک ۵۰۰ خام با Traceback) — همان اصل `/health`.

**تست:**
- `tests/test_auth_service.py` → 7 passed
- `tests/test_web_session_service.py` → 11 passed
- `tests/test_web_login.py` → 10 passed
- Full suite → **245 passed** (217 قبلی + 28 جدید)
- علاوه بر TestClient، سرور با `uvicorn` واقعاً روی `127.0.0.1` اجرا و با
  `curl` بررسی شد. در این sandbox درایور ODBC/SQL Server واقعی نصب نیست؛
  رفتار `503` برای `/login` در همین شرایط واقعی تأیید شد (نه فرضی).

**عمداً در این فاز انجام نشد:**
- Migration اجرا نشد و Merge به `main` انجام نشد (طبق قانون پروژه).
- هیچ صفحه HTML برای Login ساخته نشد.
- `home()` در `web/app.py` هنوز Auth-gate نشده (صفحات محافظت‌شده خارج از
  محدوده این فاز است).

**فاز بعدی:** 16D — Web Dashboard — شروع نشده، منوط به تأیید صریح کاربر و
تکمیل واقعی و بررسی‌شدهٔ Phase16C.
