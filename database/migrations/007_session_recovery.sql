-- =========================================================
-- Migration 007 — پایه حفاظت در برابر قطع برق (Phase 12)
-- =========================================================
-- این Migration دو جدول پایه می‌سازد:
--   1) Sessions  — هر بار اجرای برنامه یک ردیف Session دارد؛
--      با Heartbeat دوره‌ای مشخص می‌شود که آیا برنامه هنوز
--      باز است، یا به‌درستی بسته شده، یا کرش کرده.
--   2) Drafts    — اطلاعات نیمه‌تمام فرم‌ها (مثل فاکتور خرید
--      در حال تکمیل) که هنوز ثبت نهایی نشده‌اند.
--
-- توجه: این فقط زیرساخت پایه است. اتصال این جداول به تمام
-- فرم‌های برنامه (AutoSave خودکار هر فرم) در فازهای بعدی
-- انجام می‌شود؛ در Phase 12 فقط Session و Draft Service پایه
-- ساخته شده‌اند.
-- =========================================================

IF OBJECT_ID('Sessions', 'U') IS NULL
BEGIN
    CREATE TABLE Sessions (
        ID              INT IDENTITY(1,1) PRIMARY KEY,
        SessionGuid     UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
        UserRef         INT NOT NULL FOREIGN KEY REFERENCES Users(ID),
        LoginTime       DATETIME2 NOT NULL DEFAULT GETDATE(),
        LastHeartbeat   DATETIME2 NOT NULL DEFAULT GETDATE(),
        LastAutoSave    DATETIME2 NULL,
        CloseStatus     NVARCHAR(20) NOT NULL DEFAULT N'ACTIVE'  -- ACTIVE, CLEAN, CRASHED
    );
END
GO

IF OBJECT_ID('Drafts', 'U') IS NULL
BEGIN
    CREATE TABLE Drafts (
        ID              INT IDENTITY(1,1) PRIMARY KEY,
        DraftGuid       UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
        UserRef         INT NOT NULL FOREIGN KEY REFERENCES Users(ID),
        SessionRef      INT NULL FOREIGN KEY REFERENCES Sessions(ID),
        FormType        NVARCHAR(100) NOT NULL,   -- مثلا: PurchaseInvoice, SaleInvoice
        EntityType      NVARCHAR(100) NULL,
        EntityID        INT NULL,                 -- در صورت ویرایش یک رکورد موجود
        DataJson        NVARCHAR(MAX) NOT NULL,    -- محتوای فرم به شکل JSON
        Status          NVARCHAR(20) NOT NULL DEFAULT N'ACTIVE',  -- ACTIVE, RECOVERED, DISCARDED, COMPLETED
        CreatedAt       DATETIME2 NOT NULL DEFAULT GETDATE(),
        UpdatedAt       DATETIME2 NOT NULL DEFAULT GETDATE()
    );
END
GO

PRINT N'✅ Migration 007 اجرا شد (جداول Sessions و Drafts آماده‌اند).';
