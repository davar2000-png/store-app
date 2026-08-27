-- =========================================================
-- Phase 15.1 — Accounting Core Foundation (Chart of Accounts + Journal Entries)
-- =========================================================
-- این Migration فقط زیرساخت حسابداری دوطرفه (Double-Entry) را اضافه می‌کند:
-- Chart of Accounts + سربرگ/اقلام سند حسابداری (Journal Entry).
--
-- عمداً هیچ داده یا جدول موجودی (CashBoxes/BankAccounts/SalesInvoices/...)
-- را تغییر نمی‌دهد و هیچ‌کدام از آن‌ها را به این سیستم متصل نمی‌کند —
-- اتصال واقعی فروش/خرید/دریافت/پرداخت به این Ledger، موضوع فازهای بعدی
-- (15.2 به بعد) است تا هر اتصال جداگانه قابل تست و Rollback باشد.
--
-- امن و غیرمخرب: هر بخش فقط در صورت نبودن از قبل ساخته می‌شود.
-- =========================================================

USE StoreAppDB;
GO

-- =========================================================
-- ۱) دفتر حساب‌ها (Chart of Accounts)
-- =========================================================
IF OBJECT_ID('ChartOfAccounts', 'U') IS NULL
BEGIN
    CREATE TABLE ChartOfAccounts (
        ID              INT IDENTITY(1,1) PRIMARY KEY,
        Code            NVARCHAR(20) NOT NULL,
        Name            NVARCHAR(200) NOT NULL,
        AccountType     NVARCHAR(20) NOT NULL,   -- Asset / Liability / Equity / Revenue / Expense
        NormalBalance   NVARCHAR(10) NOT NULL,   -- Debit / Credit
        ParentRef       INT NULL FOREIGN KEY REFERENCES ChartOfAccounts(ID),
        IsActive        BIT NOT NULL DEFAULT 1,
        CreatedAt       DATETIME2 NOT NULL DEFAULT GETDATE(),

        CONSTRAINT CK_ChartOfAccounts_AccountType
            CHECK (AccountType IN (N'Asset', N'Liability', N'Equity', N'Revenue', N'Expense')),
        CONSTRAINT CK_ChartOfAccounts_NormalBalance
            CHECK (NormalBalance IN (N'Debit', N'Credit'))
    );

    CREATE UNIQUE INDEX UX_ChartOfAccounts_Code ON ChartOfAccounts(Code);
END
GO

-- =========================================================
-- ۲) سربرگ سند حسابداری (Journal Entry Header)
-- =========================================================
IF OBJECT_ID('JournalEntries', 'U') IS NULL
BEGIN
    CREATE TABLE JournalEntries (
        ID              INT IDENTITY(1,1) PRIMARY KEY,
        EntryNumber     INT NOT NULL,
        ShamsiDate      NVARCHAR(20) NULL,
        Description     NVARCHAR(1000) NULL,

        -- ارجاع اختیاری به سند مبدأ (مثلاً SalesInvoices/123) — برای فازهای بعد
        -- که این Ledger را به تراکنش‌های واقعی وصل می‌کنند.
        SourceTable     NVARCHAR(100) NULL,
        SourceID        INT NULL,
        CorrelationID   UNIQUEIDENTIFIER NULL,

        UserRef         INT NULL FOREIGN KEY REFERENCES Users(ID),
        CreatedAt       DATETIME2 NOT NULL DEFAULT GETDATE(),
        IsDeleted       BIT NOT NULL DEFAULT 0
    );

    CREATE UNIQUE INDEX UX_JournalEntries_Number ON JournalEntries(EntryNumber);
    CREATE INDEX IX_JournalEntries_Source ON JournalEntries(SourceTable, SourceID);
END
GO

-- =========================================================
-- ۳) اقلام سند حسابداری (Journal Entry Lines)
-- =========================================================
IF OBJECT_ID('JournalEntryLines', 'U') IS NULL
BEGIN
    CREATE TABLE JournalEntryLines (
        ID              INT IDENTITY(1,1) PRIMARY KEY,
        JournalEntryRef INT NOT NULL FOREIGN KEY REFERENCES JournalEntries(ID),
        AccountRef      INT NOT NULL FOREIGN KEY REFERENCES ChartOfAccounts(ID),
        Debit           MONEY NOT NULL DEFAULT 0,
        Credit          MONEY NOT NULL DEFAULT 0,
        Description     NVARCHAR(500) NULL,

        CONSTRAINT CK_JournalEntryLines_NonNegative
            CHECK (Debit >= 0 AND Credit >= 0),
        -- هر ردیف فقط یک طرف (بدهکار یا بستانکار) می‌تواند غیر صفر باشد
        CONSTRAINT CK_JournalEntryLines_OneSided
            CHECK (NOT (Debit > 0 AND Credit > 0))
    );

    CREATE INDEX IX_JournalEntryLines_Entry ON JournalEntryLines(JournalEntryRef);
    CREATE INDEX IX_JournalEntryLines_Account ON JournalEntryLines(AccountRef);
END
GO

-- =========================================================
-- ۴) دفتر حساب‌های پیش‌فرض (Seed) — فقط اگر جدول تازه ساخته شده و خالی است
-- =========================================================
-- این یک نقطه شروع حداقلی است، نه یک Chart of Accounts نهایی. کدها و
-- حساب‌های بیشتر در فازهای بعد (هم‌زمان با اتصال هر ماژول تجاری) اضافه
-- می‌شوند. هر ردیف فقط در صورت نبودن Code آن اضافه می‌شود، پس اجرای دوباره
-- این اسکریپت روی دیتابیسی که کاربر خودش حساب اضافه کرده، بی‌خطر است.

IF NOT EXISTS (SELECT 1 FROM ChartOfAccounts WHERE Code = N'1000')
    INSERT INTO ChartOfAccounts (Code, Name, AccountType, NormalBalance)
    VALUES (N'1000', N'صندوق و بانک', N'Asset', N'Debit');

IF NOT EXISTS (SELECT 1 FROM ChartOfAccounts WHERE Code = N'1100')
    INSERT INTO ChartOfAccounts (Code, Name, AccountType, NormalBalance)
    VALUES (N'1100', N'حساب‌های دریافتنی (بدهکاران/مشتریان)', N'Asset', N'Debit');

IF NOT EXISTS (SELECT 1 FROM ChartOfAccounts WHERE Code = N'1200')
    INSERT INTO ChartOfAccounts (Code, Name, AccountType, NormalBalance)
    VALUES (N'1200', N'موجودی کالا', N'Asset', N'Debit');

IF NOT EXISTS (SELECT 1 FROM ChartOfAccounts WHERE Code = N'1300')
    INSERT INTO ChartOfAccounts (Code, Name, AccountType, NormalBalance)
    VALUES (N'1300', N'اسناد دریافتنی (چک‌های نزد ما)', N'Asset', N'Debit');

IF NOT EXISTS (SELECT 1 FROM ChartOfAccounts WHERE Code = N'2000')
    INSERT INTO ChartOfAccounts (Code, Name, AccountType, NormalBalance)
    VALUES (N'2000', N'حساب‌های پرداختنی (بستانکاران/تأمین‌کنندگان)', N'Liability', N'Credit');

IF NOT EXISTS (SELECT 1 FROM ChartOfAccounts WHERE Code = N'2100')
    INSERT INTO ChartOfAccounts (Code, Name, AccountType, NormalBalance)
    VALUES (N'2100', N'اسناد پرداختنی (چک‌های صادرشده)', N'Liability', N'Credit');

IF NOT EXISTS (SELECT 1 FROM ChartOfAccounts WHERE Code = N'3000')
    INSERT INTO ChartOfAccounts (Code, Name, AccountType, NormalBalance)
    VALUES (N'3000', N'حقوق صاحبان سرمایه', N'Equity', N'Credit');

IF NOT EXISTS (SELECT 1 FROM ChartOfAccounts WHERE Code = N'4000')
    INSERT INTO ChartOfAccounts (Code, Name, AccountType, NormalBalance)
    VALUES (N'4000', N'درآمد فروش', N'Revenue', N'Credit');

IF NOT EXISTS (SELECT 1 FROM ChartOfAccounts WHERE Code = N'4100')
    INSERT INTO ChartOfAccounts (Code, Name, AccountType, NormalBalance)
    VALUES (N'4100', N'برگشت از فروش', N'Revenue', N'Debit');

IF NOT EXISTS (SELECT 1 FROM ChartOfAccounts WHERE Code = N'5000')
    INSERT INTO ChartOfAccounts (Code, Name, AccountType, NormalBalance)
    VALUES (N'5000', N'بهای تمام‌شده کالای فروش‌رفته', N'Expense', N'Debit');
GO
