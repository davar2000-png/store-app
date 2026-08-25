-- =========================================================
-- Phase 15.6.5 — برگشت از فروش (Sales Return) → Core + Double-Entry Ledger
-- =========================================================
-- این Migration فقط چیزهای جدید اضافه می‌کند و به داده‌های قبلی
-- (فاکتورهای فروش، لایه‌های FIFO، سریال/IMEI، سند حسابداری قبلی) هیچ
-- آسیبی نمی‌رساند. الگوی دقیق همان چیزی است که در
-- database/migrations/006_purchase_return.sql برای برگشت از خرید استفاده
-- شد: هر بخش فقط در صورت نبودن از قبل ساخته می‌شود.
--
-- حساب 4100 (برگشت از فروش) از قبل در database/migrations/009_accounting_core.sql
-- Seed شده است و اینجا دوباره ساخته/Seed نمی‌شود.
-- =========================================================

USE StoreAppDB;
GO

-- =========================================================
-- ۱) فاکتورهای برگشت از فروش (سربرگ فاکتور)
--    هر فاکتور برگشت همیشه به یک فاکتور فروش مشخص وصل است تا معلوم باشد
--    کالا از کدام فروش برگردانده شده.
-- =========================================================
IF OBJECT_ID('SalesReturnInvoices', 'U') IS NULL
BEGIN
    CREATE TABLE SalesReturnInvoices (
        ID                      INT IDENTITY(1,1) PRIMARY KEY,
        InvoiceNumber           INT NOT NULL,
        PersonRef               INT NOT NULL FOREIGN KEY REFERENCES Persons(ID),   -- مشتری
        OriginalSalesInvoiceRef INT NULL FOREIGN KEY REFERENCES SalesInvoices(ID),
        InvoiceDate             DATETIME2 NOT NULL DEFAULT GETDATE(),
        ShamsiDate              NVARCHAR(20) NULL,
        TotalAmount             MONEY NOT NULL DEFAULT 0,   -- جمع خالص اقلام برگشتی (قبل از مالیات)
        TaxAmount               MONEY NOT NULL DEFAULT 0,
        PayableAmount           MONEY NOT NULL DEFAULT 0,   -- مبلغی که باید به مشتری برگردانده شود
        Description             NVARCHAR(1000) NULL,
        UserRef                 INT NULL FOREIGN KEY REFERENCES Users(ID),
        CreatedAt               DATETIME2 NOT NULL DEFAULT GETDATE(),
        IsDeleted                BIT NOT NULL DEFAULT 0
    );
    CREATE UNIQUE INDEX UX_SalesReturnInvoices_Number ON SalesReturnInvoices(InvoiceNumber);
END
GO

-- =========================================================
-- ۲) اقلام فاکتور برگشت از فروش
--    هر قلم برگشتی همیشه به قلم اصلی فروش (SalesInvoiceItems) وصل است تا
--    قیمت واحد و سقف قابل‌برگشت از همان رکورد اصلی استخراج شود (نه از
--    ورودی خام کاربر).
-- =========================================================
IF OBJECT_ID('SalesReturnInvoiceItems', 'U') IS NULL
BEGIN
    CREATE TABLE SalesReturnInvoiceItems (
        ID                    INT IDENTITY(1,1) PRIMARY KEY,
        InvoiceRef            INT NOT NULL FOREIGN KEY REFERENCES SalesReturnInvoices(ID),
        SalesInvoiceItemRef   INT NOT NULL FOREIGN KEY REFERENCES SalesInvoiceItems(ID),
        ProductRef            INT NOT NULL FOREIGN KEY REFERENCES Products(ID),
        Quantity              DECIMAL(18,2) NOT NULL,
        UnitPrice             MONEY NOT NULL,
        TotalPrice            MONEY NOT NULL,
        CostAmount            MONEY NOT NULL DEFAULT 0,   -- بهای بازیابی‌شده طبق همان لایه(های) FIFO فروش اصلی
        Description           NVARCHAR(500) NULL
    );
END
GO

-- =========================================================
-- ۳) ردیابی برگشت هر قلم به‌ازای هر رکورد مصرف اصلی FIFO
--    (SalesInvoiceItemLayers فروش اصلی) — برای پشتیبانی از برگشت
--    چندمرحله‌ای/جزئی بدون Mutate کردن SalesInvoiceItemLayers اصلی.
--    فقط برای کالای غیرسریالی استفاده می‌شود؛ برای کالای سریالی رکوردی
--    اینجا ساخته نمی‌شود (بازیابی سریال مستقیماً از ProductSerials.PurchaseLayerRef
--    انجام می‌شود).
-- =========================================================
IF OBJECT_ID('SalesReturnInvoiceItemLayers', 'U') IS NULL
BEGIN
    CREATE TABLE SalesReturnInvoiceItemLayers (
        ID                        INT IDENTITY(1,1) PRIMARY KEY,
        SalesReturnInvoiceItemRef INT NOT NULL FOREIGN KEY REFERENCES SalesReturnInvoiceItems(ID),
        SalesInvoiceItemLayerRef  INT NOT NULL FOREIGN KEY REFERENCES SalesInvoiceItemLayers(ID),
        PurchaseLayerRef          INT NOT NULL FOREIGN KEY REFERENCES ProductPurchaseLayers(ID),
        Quantity                  DECIMAL(18,2) NOT NULL,
        UnitPrice                 MONEY NOT NULL
    );
    CREATE INDEX IX_SalesReturnInvoiceItemLayers_SourceLayer
        ON SalesReturnInvoiceItemLayers(SalesInvoiceItemLayerRef);
END
GO

PRINT N'✅ جداول Phase 15.6.5 (برگشت از فروش) با موفقیت ساخته شد.';
