-- =========================================================
-- نرم‌افزار حسابداری فروشگاه موبایل، لپ‌تاپ و کنسول بازی
-- مرحله ۱۰: فاکتور برگشت از خرید (مرجوعی کالا به تأمین‌کننده)
-- =========================================================
-- این فایل فقط چیزهای جدید اضافه می‌کند و به داده‌های قبلی
-- (اشخاص، کالاها، فاکتورهای خرید و فروش) هیچ آسیبی نمی‌رساند.
-- =========================================================

USE StoreAppDB;
GO

-- =========================================================
-- ۱) فاکتورهای برگشت از خرید (سربرگ فاکتور)
--    هر فاکتور برگشت همیشه به یک فاکتور خرید مشخص وصل است
--    تا معلوم باشد کالا از کدام خرید و کدام لایه FIFO برگردانده شده.
-- =========================================================
IF OBJECT_ID('PurchaseReturnInvoices', 'U') IS NULL
BEGIN
    CREATE TABLE PurchaseReturnInvoices (
        ID                          INT IDENTITY(1,1) PRIMARY KEY,
        InvoiceNumber               INT NOT NULL,
        PersonRef                   INT NOT NULL FOREIGN KEY REFERENCES Persons(ID),   -- فروشنده/تأمین‌کننده
        OriginalPurchaseInvoiceRef  INT NULL FOREIGN KEY REFERENCES PurchaseInvoices(ID),
        InvoiceDate                 DATETIME2 NOT NULL DEFAULT GETDATE(),
        ShamsiDate                  NVARCHAR(20) NULL,
        TotalAmount                 MONEY NOT NULL DEFAULT 0,
        PayableAmount               MONEY NOT NULL DEFAULT 0,   -- مبلغی که تأمین‌کننده باید به فروشگاه برگرداند
        PaidAmount                  MONEY NOT NULL DEFAULT 0,   -- برای مرحله بعد (دریافت از تأمین‌کننده) رزرو شده
        Description                 NVARCHAR(1000) NULL,
        UserRef                     INT NULL FOREIGN KEY REFERENCES Users(ID),
        CreatedAt                   DATETIME2 NOT NULL DEFAULT GETDATE(),
        IsDeleted                   BIT NOT NULL DEFAULT 0
    );
    CREATE UNIQUE INDEX UX_PurchaseReturnInvoices_Number ON PurchaseReturnInvoices(InvoiceNumber);
END
GO

-- =========================================================
-- ۲) اقلام فاکتور برگشت از خرید
-- =========================================================
IF OBJECT_ID('PurchaseReturnInvoiceItems', 'U') IS NULL
BEGIN
    CREATE TABLE PurchaseReturnInvoiceItems (
        ID              INT IDENTITY(1,1) PRIMARY KEY,
        InvoiceRef      INT NOT NULL FOREIGN KEY REFERENCES PurchaseReturnInvoices(ID),
        ProductRef      INT NOT NULL FOREIGN KEY REFERENCES Products(ID),
        Quantity        DECIMAL(18,2) NOT NULL,
        UnitPrice       MONEY NOT NULL,
        DiscountAmount  MONEY NOT NULL DEFAULT 0,
        TotalPrice      MONEY NOT NULL,
        Description     NVARCHAR(500) NULL
    );
END
GO

PRINT N'✅ جداول مرحله ۱۰ (فاکتور برگشت از خرید) با موفقیت ساخته شد.';
