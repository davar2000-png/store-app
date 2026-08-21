-- =========================================================
-- نرم‌افزار حسابداری فروشگاه موبایل، لپ‌تاپ و کنسول بازی
-- مرحله ۴: مالی (صندوق، بانک، دریافت، پرداخت، چک، اقساط)
-- =========================================================
-- این فایل فقط چیزهای جدید اضافه می‌کند و به داده‌های قبلی
-- (اشخاص، کالاها، فاکتورهای خرید و فروش) هیچ آسیبی نمی‌رساند.
-- =========================================================

USE StoreAppDB;
GO

-- =========================================================
-- ۱) صندوق‌ها (می‌تواند بیش از یک صندوق باشد)
-- =========================================================
IF OBJECT_ID('CashBoxes', 'U') IS NULL
BEGIN
    CREATE TABLE CashBoxes (
        ID              INT IDENTITY(1,1) PRIMARY KEY,
        Name            NVARCHAR(150) NOT NULL,
        InitialBalance  MONEY NOT NULL DEFAULT 0,
        CurrentBalance  MONEY NOT NULL DEFAULT 0,
        IsActive        BIT NOT NULL DEFAULT 1,
        CreatedAt       DATETIME2 NOT NULL DEFAULT GETDATE()
    );
END
GO

-- =========================================================
-- ۲) حساب‌های بانکی
-- =========================================================
IF OBJECT_ID('BankAccounts', 'U') IS NULL
BEGIN
    CREATE TABLE BankAccounts (
        ID              INT IDENTITY(1,1) PRIMARY KEY,
        BankName        NVARCHAR(150) NOT NULL,
        AccountTitle    NVARCHAR(200) NULL,
        AccountNumber   NVARCHAR(100) NULL,
        Sheba           NVARCHAR(50)  NULL,
        CardNumber      NVARCHAR(50)  NULL,
        InitialBalance  MONEY NOT NULL DEFAULT 0,
        CurrentBalance  MONEY NOT NULL DEFAULT 0,
        IsActive        BIT NOT NULL DEFAULT 1,
        CreatedAt       DATETIME2 NOT NULL DEFAULT GETDATE()
    );
END
GO

-- =========================================================
-- ۳) تراکنش‌های صندوق (لاگ کامل واریز/برداشت هر صندوق)
-- =========================================================
IF OBJECT_ID('CashBoxTransactions', 'U') IS NULL
BEGIN
    CREATE TABLE CashBoxTransactions (
        ID              INT IDENTITY(1,1) PRIMARY KEY,
        CashBoxRef      INT NOT NULL FOREIGN KEY REFERENCES CashBoxes(ID),
        TransactionType NVARCHAR(10) NOT NULL,   -- In / Out
        Amount          MONEY NOT NULL,
        BalanceAfter    MONEY NOT NULL,
        RefTable        NVARCHAR(100) NULL,      -- Receipts / Payments / Cheques / Manual
        RefID           INT NULL,
        ShamsiDate      NVARCHAR(20) NULL,
        Description     NVARCHAR(500) NULL,
        UserRef         INT NULL FOREIGN KEY REFERENCES Users(ID),
        CreatedAt       DATETIME2 NOT NULL DEFAULT GETDATE()
    );
END
GO

-- =========================================================
-- ۴) تراکنش‌های بانک (لاگ کامل واریز/برداشت هر حساب بانکی)
-- =========================================================
IF OBJECT_ID('BankTransactions', 'U') IS NULL
BEGIN
    CREATE TABLE BankTransactions (
        ID              INT IDENTITY(1,1) PRIMARY KEY,
        BankAccountRef  INT NOT NULL FOREIGN KEY REFERENCES BankAccounts(ID),
        TransactionType NVARCHAR(10) NOT NULL,   -- Deposit / Withdraw
        Amount          MONEY NOT NULL,
        BalanceAfter    MONEY NOT NULL,
        RefTable        NVARCHAR(100) NULL,      -- Receipts / Payments / Cheques / Manual
        RefID           INT NULL,
        ShamsiDate      NVARCHAR(20) NULL,
        Description     NVARCHAR(500) NULL,
        UserRef         INT NULL FOREIGN KEY REFERENCES Users(ID),
        CreatedAt       DATETIME2 NOT NULL DEFAULT GETDATE()
    );
END
GO

-- =========================================================
-- ۵) چک‌ها (دریافتی از مشتری / پرداختی به تأمین‌کننده)
-- =========================================================
IF OBJECT_ID('Cheques', 'U') IS NULL
BEGIN
    CREATE TABLE Cheques (
        ID              INT IDENTITY(1,1) PRIMARY KEY,
        ChequeType      NVARCHAR(10) NOT NULL,     -- Received / Issued
        ChequeNumber    NVARCHAR(100) NOT NULL,
        SayadNumber     NVARCHAR(100) NULL,
        BankName        NVARCHAR(150) NULL,
        PersonRef       INT NOT NULL FOREIGN KEY REFERENCES Persons(ID),
        Amount          MONEY NOT NULL,
        ShamsiDate      NVARCHAR(20) NULL,          -- تاریخ دریافت/صدور چک
        DueShamsiDate   NVARCHAR(20) NULL,           -- تاریخ سررسید چک
        Status          NVARCHAR(20) NOT NULL DEFAULT N'InHand',
                        -- InHand (نزد ما) / Deposited (نزد بانک - در انتظار وصول) /
                        -- Cashed (وصول/پاس‌شده) / Bounced (برگشت‌خورده) / Returned (عودت‌شده)
        CashBoxRef      INT NULL FOREIGN KEY REFERENCES CashBoxes(ID),      -- وقتی نقد شده به کدام صندوق
        BankAccountRef  INT NULL FOREIGN KEY REFERENCES BankAccounts(ID),   -- وقتی نقد شده به کدام حساب بانکی
        RefTable        NVARCHAR(100) NULL,   -- Receipts / Payments (سند دریافت/پرداختی که این چک را ثبت کرد)
        RefID           INT NULL,
        Description     NVARCHAR(500) NULL,
        UserRef         INT NULL FOREIGN KEY REFERENCES Users(ID),
        CreatedAt       DATETIME2 NOT NULL DEFAULT GETDATE()
    );
END
GO

-- =========================================================
-- ۶) دریافت‌ها (سربرگ سند دریافت وجه از مشتری)
-- =========================================================
IF OBJECT_ID('Receipts', 'U') IS NULL
BEGIN
    CREATE TABLE Receipts (
        ID              INT IDENTITY(1,1) PRIMARY KEY,
        ReceiptNumber   INT NOT NULL,
        PersonRef       INT NOT NULL FOREIGN KEY REFERENCES Persons(ID),   -- مشتری
        ShamsiDate      NVARCHAR(20) NULL,
        TotalAmount     MONEY NOT NULL DEFAULT 0,
        Description     NVARCHAR(1000) NULL,
        UserRef         INT NULL FOREIGN KEY REFERENCES Users(ID),
        CreatedAt       DATETIME2 NOT NULL DEFAULT GETDATE(),
        IsDeleted       BIT NOT NULL DEFAULT 0
    );
    CREATE UNIQUE INDEX UX_Receipts_Number ON Receipts(ReceiptNumber);
END
GO

-- روش‌های پرداخت داخل یک سند دریافت (نقد/بانک/چک - می‌تواند ترکیبی باشد)
IF OBJECT_ID('ReceiptLines', 'U') IS NULL
BEGIN
    CREATE TABLE ReceiptLines (
        ID              INT IDENTITY(1,1) PRIMARY KEY,
        ReceiptRef      INT NOT NULL FOREIGN KEY REFERENCES Receipts(ID),
        MethodType      NVARCHAR(10) NOT NULL,   -- Cash / Bank / Cheque
        CashBoxRef      INT NULL FOREIGN KEY REFERENCES CashBoxes(ID),
        BankAccountRef  INT NULL FOREIGN KEY REFERENCES BankAccounts(ID),
        ChequeRef       INT NULL FOREIGN KEY REFERENCES Cheques(ID),
        Amount          MONEY NOT NULL
    );
END
GO

-- تخصیص مبلغ سند دریافت به فاکتور(های) فروش (یک دریافت می‌تواند بابت چند فاکتور باشد)
IF OBJECT_ID('ReceiptAllocations', 'U') IS NULL
BEGIN
    CREATE TABLE ReceiptAllocations (
        ID                  INT IDENTITY(1,1) PRIMARY KEY,
        ReceiptRef          INT NOT NULL FOREIGN KEY REFERENCES Receipts(ID),
        SalesInvoiceRef     INT NOT NULL FOREIGN KEY REFERENCES SalesInvoices(ID),
        Amount              MONEY NOT NULL
    );
END
GO

-- =========================================================
-- ۷) پرداخت‌ها (سربرگ سند پرداخت وجه به تأمین‌کننده)
-- =========================================================
IF OBJECT_ID('Payments', 'U') IS NULL
BEGIN
    CREATE TABLE Payments (
        ID              INT IDENTITY(1,1) PRIMARY KEY,
        PaymentNumber   INT NOT NULL,
        PersonRef       INT NOT NULL FOREIGN KEY REFERENCES Persons(ID),   -- تأمین‌کننده/فروشنده
        ShamsiDate      NVARCHAR(20) NULL,
        TotalAmount     MONEY NOT NULL DEFAULT 0,
        Description     NVARCHAR(1000) NULL,
        UserRef         INT NULL FOREIGN KEY REFERENCES Users(ID),
        CreatedAt       DATETIME2 NOT NULL DEFAULT GETDATE(),
        IsDeleted       BIT NOT NULL DEFAULT 0
    );
    CREATE UNIQUE INDEX UX_Payments_Number ON Payments(PaymentNumber);
END
GO

IF OBJECT_ID('PaymentLines', 'U') IS NULL
BEGIN
    CREATE TABLE PaymentLines (
        ID              INT IDENTITY(1,1) PRIMARY KEY,
        PaymentRef      INT NOT NULL FOREIGN KEY REFERENCES Payments(ID),
        MethodType      NVARCHAR(10) NOT NULL,   -- Cash / Bank / Cheque
        CashBoxRef      INT NULL FOREIGN KEY REFERENCES CashBoxes(ID),
        BankAccountRef  INT NULL FOREIGN KEY REFERENCES BankAccounts(ID),
        ChequeRef       INT NULL FOREIGN KEY REFERENCES Cheques(ID),
        Amount          MONEY NOT NULL
    );
END
GO

IF OBJECT_ID('PaymentAllocations', 'U') IS NULL
BEGIN
    CREATE TABLE PaymentAllocations (
        ID                  INT IDENTITY(1,1) PRIMARY KEY,
        PaymentRef          INT NOT NULL FOREIGN KEY REFERENCES Payments(ID),
        PurchaseInvoiceRef  INT NOT NULL FOREIGN KEY REFERENCES PurchaseInvoices(ID),
        Amount              MONEY NOT NULL
    );
END
GO

-- =========================================================
-- ۸) اقساط (تبدیل فاکتور فروش نسیه به چند قسط با سررسید مشخص)
-- =========================================================
IF OBJECT_ID('InstallmentPlans', 'U') IS NULL
BEGIN
    CREATE TABLE InstallmentPlans (
        ID                  INT IDENTITY(1,1) PRIMARY KEY,
        PersonRef           INT NOT NULL FOREIGN KEY REFERENCES Persons(ID),
        SalesInvoiceRef     INT NOT NULL FOREIGN KEY REFERENCES SalesInvoices(ID),
        TotalAmount         MONEY NOT NULL,
        InstallmentCount    INT NOT NULL,
        ShamsiDate          NVARCHAR(20) NULL,     -- تاریخ ثبت طرح اقساط
        Description         NVARCHAR(500) NULL,
        UserRef             INT NULL FOREIGN KEY REFERENCES Users(ID),
        CreatedAt           DATETIME2 NOT NULL DEFAULT GETDATE(),
        IsDeleted           BIT NOT NULL DEFAULT 0
    );
END
GO

IF OBJECT_ID('InstallmentItems', 'U') IS NULL
BEGIN
    CREATE TABLE InstallmentItems (
        ID                  INT IDENTITY(1,1) PRIMARY KEY,
        PlanRef             INT NOT NULL FOREIGN KEY REFERENCES InstallmentPlans(ID),
        SeqNumber           INT NOT NULL,          -- شماره قسط (۱، ۲، ۳، ...)
        DueShamsiDate       NVARCHAR(20) NOT NULL,
        Amount              MONEY NOT NULL,
        Status              NVARCHAR(20) NOT NULL DEFAULT N'Pending',  -- Pending / Paid
        PaidShamsiDate      NVARCHAR(20) NULL,
        ReceiptRef          INT NULL FOREIGN KEY REFERENCES Receipts(ID)
    );
END
GO

PRINT N'✅ جداول مرحله ۴ (مالی: صندوق، بانک، دریافت، پرداخت، چک، اقساط) با موفقیت ساخته شد.';
