-- =========================================================
-- Migration 015 — Phase 16C: Web Session Storage
-- =========================================================
-- این Migration فقط یک جدول جدید و کاملاً مستقل می‌سازد: WebSessions.
--
-- محدودیت‌های عمدی این Migration:
--   • هیچ جدول موجودی (Users, Sessions, ...) تغییر داده نمی‌شود — نه
--     ALTER TABLE، نه افزودن ستون، نه تغییر Constraint.
--   • WebSessions هیچ ارتباطی با جدول Sessions موجود
--     (database/migrations/007_session_recovery.sql) ندارد. آن جدول برای
--     بازیابی بعد از قطع برق در برنامه دسکتاپی است؛ این جدول برای
--     Login/Logout در وب است. این دو concern عمداً جدا نگه داشته شده‌اند.
--   • هیچ ارتباطی با زنجیره Legacy حسابداری (DocHeader → Transaction →
--     DetailAccounts) و جداول عملیاتی آن (Customers, Factors, Cashs,
--     CashBox, ChequeRecs, ChequePays) ندارد و نباید داشته باشد.
--   • امن و غیرمخرب: مطابق الگوی همه Migration های قبلی این پروژه، فقط در
--     صورت نبودن جدول از قبل ساخته می‌شود (IF OBJECT_ID ... IS NULL).
--
-- توکن خام Session هرگز اینجا ذخیره نمی‌شود — فقط هش SHA-256 آن
-- (ستون TokenHash)، مطابق services/web_session_service.py.
-- =========================================================

USE StoreAppDB;
GO

IF OBJECT_ID('WebSessions', 'U') IS NULL
BEGIN
    CREATE TABLE WebSessions (
        ID              INT             IDENTITY(1,1) PRIMARY KEY,
        TokenHash       NVARCHAR(128)   NOT NULL UNIQUE,
        UserRef         INT             NOT NULL FOREIGN KEY REFERENCES Users(ID),
        CreatedAt       DATETIME2       NOT NULL DEFAULT GETDATE(),
        ExpiresAt       DATETIME2       NOT NULL,
        LastActivity    DATETIME2       NOT NULL DEFAULT GETDATE(),
        IsRevoked       BIT             NOT NULL DEFAULT 0,
        UserAgent       NVARCHAR(400)   NULL,
        IPAddress       NVARCHAR(64)    NULL
    );

    CREATE INDEX IX_WebSessions_UserRef ON WebSessions(UserRef);
END
GO

PRINT N'✅ Migration 015 اجرا شد (جدول WebSessions آماده است).';
GO

-- =========================================================
-- Rollback (اجرای دستی در صورت نیاز؛ به‌صورت خودکار اجرا نمی‌شود):
--
--   DROP INDEX IX_WebSessions_UserRef ON WebSessions;
--   DROP TABLE WebSessions;
--
-- این Rollback هیچ جدول دیگری (Users, Sessions, ...) را لمس نمی‌کند.
-- =========================================================
