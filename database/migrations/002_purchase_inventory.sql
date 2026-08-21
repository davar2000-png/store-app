-- =========================================================
-- نرم‌افزار حسابداری فروشگاه موبایل، لپ‌تاپ و کنسول بازی
-- مرحله ۲: خرید و انبار (FIFO، کاردکس، سریال/IMEI، نقطه سفارش)
-- =========================================================
-- این فایل فقط چیزهای جدید اضافه می‌کند و به داده‌های قبلی
-- (اشخاص و کالاهایی که قبلاً ثبت کرده‌اید) هیچ آسیبی نمی‌رساند.
-- =========================================================

USE StoreAppDB;
GO

-- =========================================================
-- ۱) اضافه‌کردن ستون «موجودی فعلی» به جدول Products
--    (اگر قبلاً اضافه شده باشد، دوباره اضافه نمی‌شود)
-- =========================================================
IF NOT EXISTS (
    SELECT * FROM sys.columns
    WHERE object_id = OBJECT_ID('Products') AND name = 'CurrentStock'
)
BEGIN
    ALTER TABLE Products ADD CurrentStock DECIMAL(18,2) NOT NULL DEFAULT 0;
END
GO

-- =========================================================
-- ۲) فاکتورهای خرید (سربرگ فاکتور)
-- =========================================================
IF OBJECT_ID('PurchaseInvoices', 'U') IS NULL
BEGIN
    CREATE TABLE PurchaseInvoices (
        ID              INT IDENTITY(1,1) PRIMARY KEY,
        InvoiceNumber   INT NOT NULL,
        PersonRef       INT NOT NULL FOREIGN KEY REFERENCES Persons(ID),   -- فروشنده/تأمین‌کننده
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
    CREATE UNIQUE INDEX UX_PurchaseInvoices_Number ON PurchaseInvoices(InvoiceNumber);
END
GO

-- =========================================================
-- ۳) اقلام فاکتور خرید
-- =========================================================
IF OBJECT_ID('PurchaseInvoiceItems', 'U') IS NULL
BEGIN
    CREATE TABLE PurchaseInvoiceItems (
        ID              INT IDENTITY(1,1) PRIMARY KEY,
        InvoiceRef      INT NOT NULL FOREIGN KEY REFERENCES PurchaseInvoices(ID),
        ProductRef      INT NOT NULL FOREIGN KEY REFERENCES Products(ID),
        Quantity        DECIMAL(18,2) NOT NULL,
        UnitPrice       MONEY NOT NULL,
        DiscountAmount  MONEY NOT NULL DEFAULT 0,
        TotalPrice      MONEY NOT NULL,
        Description     NVARCHAR(500) NULL
    );
END
GO

-- =========================================================
-- ۴) لایه‌های FIFO خرید
--    هر بار خرید یک «لایه» جدید می‌سازد. وقتی کالا فروخته می‌شود
--    (در مرحله ۳) از قدیمی‌ترین لایه با موجودی باقیمانده کم می‌شود
--    تا بهای تمام‌شده دقیق محاسبه شود.
-- =========================================================
IF OBJECT_ID('ProductPurchaseLayers', 'U') IS NULL
BEGIN
    CREATE TABLE ProductPurchaseLayers (
        ID                  INT IDENTITY(1,1) PRIMARY KEY,
        ProductRef          INT NOT NULL FOREIGN KEY REFERENCES Products(ID),
        InvoiceItemRef      INT NOT NULL FOREIGN KEY REFERENCES PurchaseInvoiceItems(ID),
        PurchaseDate        DATETIME2 NOT NULL DEFAULT GETDATE(),
        ShamsiDate          NVARCHAR(20) NULL,
        OriginalQuantity    DECIMAL(18,2) NOT NULL,
        RemainingQuantity   DECIMAL(18,2) NOT NULL,   -- هر چه فروخته شود از این کم می‌شود
        UnitPrice           MONEY NOT NULL,
        CreatedAt           DATETIME2 NOT NULL DEFAULT GETDATE()
    );
END
GO

-- =========================================================
-- ۵) کاردکس کالا (دفتر کل ورود/خروج انبار)
-- =========================================================
IF OBJECT_ID('ProductCardex', 'U') IS NULL
BEGIN
    CREATE TABLE ProductCardex (
        ID              INT IDENTITY(1,1) PRIMARY KEY,
        ProductRef      INT NOT NULL FOREIGN KEY REFERENCES Products(ID),
        MovementDate    DATETIME2 NOT NULL DEFAULT GETDATE(),
        ShamsiDate      NVARCHAR(20) NULL,
        MovementType    NVARCHAR(50) NOT NULL,   -- Buy, Sell, BuyReturn, SellReturn, Initial, Adjustment
        RefTable        NVARCHAR(100) NULL,      -- مثلا PurchaseInvoices
        RefID           INT NULL,
        InQuantity      DECIMAL(18,2) NOT NULL DEFAULT 0,
        OutQuantity     DECIMAL(18,2) NOT NULL DEFAULT 0,
        UnitPrice       MONEY NOT NULL DEFAULT 0,
        BalanceQuantity DECIMAL(18,2) NOT NULL DEFAULT 0,   -- موجودی بعد از این حرکت
        Description     NVARCHAR(500) NULL,
        UserRef         INT NULL FOREIGN KEY REFERENCES Users(ID),
        CreatedAt       DATETIME2 NOT NULL DEFAULT GETDATE()
    );
END
GO

-- =========================================================
-- ۶) اتصال سریال/IMEI به لایه خرید مربوطه
--    (ستون PurchaseLayerRef از مرحله ۱ موجود است؛ فقط FK اضافه می‌شود)
-- =========================================================
IF NOT EXISTS (
    SELECT * FROM sys.foreign_keys WHERE name = 'FK_ProductSerials_Layer'
)
BEGIN
    ALTER TABLE ProductSerials
    ADD CONSTRAINT FK_ProductSerials_Layer
    FOREIGN KEY (PurchaseLayerRef) REFERENCES ProductPurchaseLayers(ID);
END
GO

PRINT N'✅ جداول مرحله ۲ (خرید و انبار با FIFO) با موفقیت ساخته شد.';
