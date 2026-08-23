-- =========================================================
-- Phase 15.3 — Purchase Invoice → Double-Entry Accounting Ledger
-- =========================================================
-- زمینه (چرا این Migration لازم شد):
-- اتصال فاکتور خرید به Ledger (Phase 15.3) به دو حساب جدید نیاز دارد که
-- در Chart of Accounts موجود (009_accounting_core.sql, 010_accounting_tax_
-- payable.sql) وجود نداشتند:
--
--   1400 مالیات خرید / مالیات قابل کسر (Input/Recoverable Purchase Tax)
--        — این حساب عمداً از 2200 (که Liability مربوط به مالیات
--        دریافت‌شده از مشتری در فروش است، Phase 15.2) جداست؛ ماهیت
--        اقتصادی این دو کاملاً متفاوت است (مالیات پرداختی بابت خرید که
--        قابل کسر از مالیات پرداختنی است، در برابر مالیات دریافتی از
--        مشتری) و طبق تصمیم صریح Option C نباید با هم مخلوط شوند.
--
--   5100 تخفیف خرید (Purchase Discount / Contra-Purchase)
--        — ثبت مجموع تخفیف قلمی + تخفیف سربرگ فاکتور خرید در سمت
--        بستانکار سند حسابداری خرید، بدون دست‌زدن به FIFO یا
--        ProductPurchaseLayers.UnitPrice (که همچنان قیمت خام واحد را
--        نگه می‌دارد — طبق Option C).
--
-- ParentRef هر دو حساب عمداً NULL است: در Chart of Accounts فعلی هیچ
-- حساب Seed‌شده‌ای ParentRef غیر NULL ندارد و هیچ بخشی از کد (get_chart_
-- of_accounts / create_account / گزارش‌ها) به ParentRef برای Rollup یا
-- اعتبارسنجی معنایی متکی نیست؛ بنابراین فرض یک رابطه پدر-فرزند بین 5100
-- و 5000 (که ماهیت Credit/Debit متفاوتی هم دارند) در ساختار و قرارداد
-- فعلی پشتیبانی یا اعتبارسنجی نمی‌شود.
--
-- امن و غیرمخرب: هر حساب فقط در صورت نبودن Code آن اضافه می‌شود؛ هیچ
-- حساب موجودی حذف/ویرایش نمی‌شود و هیچ Backfill انجام نمی‌شود.
-- =========================================================

USE StoreAppDB;
GO

IF NOT EXISTS (SELECT 1 FROM ChartOfAccounts WHERE Code = N'1400')
    INSERT INTO ChartOfAccounts (Code, Name, AccountType, NormalBalance)
    VALUES (N'1400', N'مالیات خرید / مالیات قابل کسر', N'Asset', N'Debit');

IF NOT EXISTS (SELECT 1 FROM ChartOfAccounts WHERE Code = N'5100')
    INSERT INTO ChartOfAccounts (Code, Name, AccountType, NormalBalance)
    VALUES (N'5100', N'تخفیف خرید', N'Expense', N'Credit');
GO
