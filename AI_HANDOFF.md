# AI_HANDOFF.md

> Account بعدی: این فایل را قبل از هر کاری بخوانید. به حافظه مکالمه قبلی
> اعتماد نکنید — GitHub مرجع اصلی است.

## LAST ACCOUNT
Claude Sonnet 5 (همین مکالمه)

## CURRENT PHASE
12 — Stabilization + GitHub Normalization + Power Failure Foundation

## LAST COMMIT
هنوز Push نشده — این تحویل به‌صورت یک ZIP دانلودی به کاربر داده شده چون
مدل هیچ‌وقت به Token/اعتبارنامه GitHub کاربر دسترسی مستقیم نداشت.
کاربر باید محتوای این پوشه را با یک Commit عادی (نه Force) روی `main` Push کند.

## COMPLETED
- بررسی کامل GitHub و Git History (شناسایی دو فایل Backup حساس)
- Objective B: انتقال Source Code واقعی Phase 11 به ریشه Repo؛ ZIPهای قدیمی به `archive/`
- Objective C+D: بازیابی `services/settings_service.py` و `ui/settings_window.py` از Phase 10 + رفع Regression در `ui/main_window.py` (کنترل دسترسی `is_module_allowed` دوباره وصل شد، شامل دو ماژول جدید Phase 11)
- Objective E: تفکیک `database/schema.sql` به `database/schema/001_fresh_install.sql` (مخرب، فقط نصب تازه) و `database/migrations/001-007` (امن، غیرمخرب)
- Objective F: تمام ۱۱ فایل مستندات ساخته شد
- Objective G+H: زیرساخت پایه `Sessions`/`Drafts` (جدول + Service) — نه یکپارچه‌سازی کامل
- Objective I: Smoke Test پایه (`tests/test_smoke.py`) — فقط بررسی Import و Syntax، **بدون** اتصال واقعی به SQL Server (چون این محیط به دیتابیس کاربر دسترسی ندارد)
- `.gitignore` اضافه شد

## NOT COMPLETED
- پاکسازی کامل Git History از فایل‌های Backup حساس (نیاز به تأیید صریح کاربر برای Force Push؛ کاربر فعلاً «رد کن، ادامه بده» را انتخاب کرد)
- اتصال AutoSave/Draft Recovery به فرم‌های واقعی (فقط API پایه آماده است)
- Crash Detection در `main.py` (هنوز `start_session`/`heartbeat`/`close_session_cleanly` جایی فراخوانی نمی‌شوند)
- ساخت Branch `phase/12-stabilization`
- تست واقعی روی SQL Server واقعی (این محیط sandbox به SQL Server کاربر متصل نیست)

## FILES CHANGED
**ایجادشده:**
`.gitignore`, `PROJECT_STATE.md`, `PHASE_REGISTRY.md`, `AI_HANDOFF.md`, `ARCHITECTURE.md`,
`DATABASE_SCHEMA.md`, `ACCOUNTING_RULES.md`, `SECURITY.md`, `BACKUP_POLICY.md`,
`UI_DESIGN_SYSTEM.md`, `CHANGELOG.md`, `POWER_FAILURE_RECOVERY.md`,
`database/README.md`, `database/schema/001_fresh_install.sql`,
`database/migrations/001_initial_safe.sql`, `database/migrations/007_session_recovery.sql`,
`services/session_service.py`, `services/draft_service.py`, `tests/test_smoke.py`

**تغییریافته:**
`ui/main_window.py` (بازیابی importها، ساختار سه‌تایی modules، فیلتر دسترسی، متد `open_settings`)

**بازیابی‌شده از Phase 10 (بدون تغییر محتوا):**
`services/settings_service.py`, `ui/settings_window.py`

**جابه‌جاشده:**
`StoreApp_Phase*.zip` و `TECHNOKALARoboAccBackUp*.zip` (باقی‌مانده) → `archive/`
`database/phase2_purchase_inventory.sql` → `database/migrations/002_purchase_inventory.sql` (و مشابه برای 3، 4، 6، 10)

## DATABASE CHANGES
هیچ تغییری روی دیتابیس واقعی کاربر اعمال نشد (این محیط به آن دسترسی ندارد).
یک Migration جدید (`007_session_recovery.sql`) نوشته شده که باید توسط کاربر
روی دیتابیس واقعی‌اش اجرا شود تا جداول `Sessions`/`Drafts` ساخته شوند.

## REGRESSION FIXES
Settings + User Permissions Phase 11 Regression — رفع شد (جزئیات در PHASE_REGISTRY.md)

## TESTS
`tests/test_smoke.py` نوشته و در این محیط اجرا شد — فقط Import/Syntax تمام ماژول‌های اصلی
را چک می‌کند. **اتصال واقعی به SQL Server تست نشده** چون این محیط sandbox به دیتابیس
کاربر دسترسی ندارد. صادقانه: `NOT FULLY TESTED` روی سناریوی واقعی قطع برق (بخش ۱۹ پرامپت).

## KNOWN ISSUES
1. 🔴 دو فایل Backup حساس هنوز در Git History (نه در نسخه فعلی) — نیاز به تصمیم کاربر درباره Force Push
2. Power Failure Protection فقط Foundation است، هنوز به UI وصل نشده
3. هیچ Branch جداگانه‌ای برای این فاز ساخته نشد

## NEXT PHASE
13 — پیشنهاد: اتصال AutoSave/Recovery به فرم خرید (اولین فرم پایلوت) + شروع لایه حسابداری دوطرفه
