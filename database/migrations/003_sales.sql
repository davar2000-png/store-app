-- =========================================================
-- نرم‌افزار حسابداری فروشگاه موبایل، لپ‌تاپ و کنسول بازی
-- مرحله ۳ (بخش اول): فاکتور فروش با کسر خودکار از FIFO
-- =========================================================
-- این فایل فقط چیزهای جدید اضافه می‌کند و به داده‌های قبلی
-- (اشخاص، کالاها، فاکتورهای خرید) هیچ آسیبی نمی‌رساند.
-- =========================================================

USE StoreAppDB;
GO

-- =========================================================
-- ۱) فاکتورهای فروش (سربرگ فاکتور)
-- =========================================================
IF OBJECT_ID('SalesInvoices', 'U') IS NULL
BEGIN
    CREATE TABLE SalesInvoices (
        ID              INT IDENTITY(1,1) PRIMARY KEY,
        InvoiceNumber   INT NOT NULL,
        PersonRef       INT NOT NULL FOREIGN KEY REFERENCES Persons(ID),   -- مشتری
        InvoiceDate     DATETIME2 NOT NULL DEFAULT GETDATE(),
        ShamsiDate      NVARCHAR(20) NULL,
        TotalAmount     MONEY NOT NULL DEFAULT 0,     -- جمع اقلام قبل از تخفیف کل فاکتور
        DiscountAmount  MONEY NOT NULL DEFAULT 0,      -- تخفیف کل فاکتور
        TaxAmount       MONEY NOT NULL DEFAULT 0,
        PayableAmount   MONEY NOT NULL DEFAULT 0,      -- مبلغ نهایی قابل پرداخت
        PaidAmount      MONEY NOT NULL DEFAULT 0,      -- در مرحله مالی تکمیل می‌شود
        Description     NVARCHAR(1000) NULL,
        UserRef         INT NULL FOREIGN KEY REFERENCES Users(ID),
        CreatedAt       DATETIME2 NOT NULL DEFAULT GETDATE(),
        IsDeleted       BIT NOT NULL DEFAULT 0
    );
    CREATE UNIQUE INDEX UX_SalesInvoices_Number ON SalesInvoices(InvoiceNumber);
END
GO

-- =========================================================
-- ۲) اقلام فاکتور فروش
-- =========================================================
IF OBJECT_ID('SalesInvoiceItems', 'U') IS NULL
BEGIN
    CREATE TABLE SalesInvoiceItems (
        ID              INT IDENTITY(1,1) PRIMARY KEY,
        InvoiceRef      INT NOT NULL FOREIGN KEY REFERENCES SalesInvoices(ID),
        ProductRef      INT NOT NULL FOREIGN KEY REFERENCES Products(ID),
        Quantity        DECIMAL(18,2) NOT NULL,
        UnitPrice       MONEY NOT NULL,               -- قیمت فروش واحد
        DiscountAmount  MONEY NOT NULL DEFAULT 0,
        TotalPrice      MONEY NOT NULL,               -- جمع فروش این قلم (بعد از تخفیف)
        CostAmount      MONEY NOT NULL DEFAULT 0,      -- بهای تمام‌شده این قلم طبق FIFO (برای گزارش سود در مراحل بعد)
        Description     NVARCHAR(500) NULL
    );
END
GO

-- =========================================================
-- ۳) اتصال هر قلم فروش به لایه(های) خریدی که از آن کسر شده
--    (چون ممکن است یک فروش از چند لایه با قیمت متفاوت تأمین شود)
-- =========================================================
IF OBJECT_ID('SalesInvoiceItemLayers', 'U') IS NULL
BEGIN
    CREATE TABLE SalesInvoiceItemLayers (
        ID                      INT IDENTITY(1,1) PRIMARY KEY,
        SalesInvoiceItemRef     INT NOT NULL FOREIGN KEY REFERENCES SalesInvoiceItems(ID),
        PurchaseLayerRef        INT NOT NULL FOREIGN KEY REFERENCES ProductPurchaseLayers(ID),
        Quantity                DECIMAL(18,2) NOT NULL,
        UnitPrice               MONEY NOT NULL    -- قیمت خرید همان لایه در لحظه فروش
    );
END
GO

-- =========================================================
-- ۴) ردیابی این‌که هر سریال/IMEI در کدام قلم فروش، فروخته شده
--    (برای «برگشت از فروش» در مرحله بعد لازم می‌شود)
-- =========================================================
IF NOT EXISTS (
    SELECT * FROM sys.columns
    WHERE object_id = OBJECT_ID('ProductSerials') AND name = 'SoldInInvoiceItemRef'
)
BEGIN
    ALTER TABLE ProductSerials ADD SoldInInvoiceItemRef INT NULL;
END
GO

PRINT N'✅ جداول مرحله ۳ (فروش با FIFO) با موفقیت ساخته شد.';
