-- =========================================================
-- نرم‌افزار حسابداری فروشگاه موبایل، لپ‌تاپ و کنسول بازی
-- مرحله ۱: هسته نرم‌افزار (دیتابیس، کاربران، اشخاص، کالا)
-- =========================================================

-- ساخت دیتابیس (اگر وجود نداشت)
IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'StoreAppDB')
BEGIN
    CREATE DATABASE StoreAppDB;
END
GO

USE StoreAppDB;
GO

-- =========================================================
-- جدول کاربران و دسترسی‌ها
-- =========================================================
IF OBJECT_ID('Users', 'U') IS NOT NULL DROP TABLE Users;
CREATE TABLE Users (
    ID              INT IDENTITY(1,1) PRIMARY KEY,
    Username        NVARCHAR(100) NOT NULL UNIQUE,
    PasswordHash    NVARCHAR(256) NOT NULL,
    PasswordSalt    NVARCHAR(64)  NOT NULL,
    FullName        NVARCHAR(200) NOT NULL,
    IsAdmin         BIT NOT NULL DEFAULT 0,
    IsActive        BIT NOT NULL DEFAULT 1,
    CreatedAt       DATETIME2 NOT NULL DEFAULT GETDATE(),
    LastLogin       DATETIME2 NULL
);
GO

-- دسترسی‌های ریز کارمند (هر ردیف = یک مجوز روشن/خاموش برای یک کاربر)
IF OBJECT_ID('UserPermissions', 'U') IS NOT NULL DROP TABLE UserPermissions;
CREATE TABLE UserPermissions (
    ID              INT IDENTITY(1,1) PRIMARY KEY,
    UserRef         INT NOT NULL FOREIGN KEY REFERENCES Users(ID),
    PermissionKey   NVARCHAR(100) NOT NULL,   -- مثلا: PersonView, PersonAdd, ProductEdit, SaleFactor, ...
    IsAllowed       BIT NOT NULL DEFAULT 0
);
GO

-- ثبت فعالیت کاربران (چه کسی، چه زمانی، چه کاری)
IF OBJECT_ID('ActivityLog', 'U') IS NOT NULL DROP TABLE ActivityLog;
CREATE TABLE ActivityLog (
    ID              INT IDENTITY(1,1) PRIMARY KEY,
    UserRef         INT NULL FOREIGN KEY REFERENCES Users(ID),
    ActionType      NVARCHAR(100) NOT NULL,   -- Create, Update, Delete, Login, ...
    TableName       NVARCHAR(100) NOT NULL,
    RecordID        INT NULL,
    Details         NVARCHAR(MAX) NULL,
    ActionDate      DATETIME2 NOT NULL DEFAULT GETDATE()
);
GO

-- =========================================================
-- گروه‌های اشخاص (مشتری، فروشنده، کارمند، ...)
-- =========================================================
IF OBJECT_ID('PersonGroups', 'U') IS NOT NULL DROP TABLE PersonGroups;
CREATE TABLE PersonGroups (
    ID              INT IDENTITY(1,1) PRIMARY KEY,
    Name            NVARCHAR(150) NOT NULL UNIQUE,
    Description     NVARCHAR(500) NULL
);
GO

-- =========================================================
-- اشخاص (حقیقی/حقوقی) - مشتری، فروشنده، کارمند و...
-- =========================================================
IF OBJECT_ID('Persons', 'U') IS NOT NULL DROP TABLE Persons;
CREATE TABLE Persons (
    ID              INT IDENTITY(1,1) PRIMARY KEY,
    FullName        NVARCHAR(300) NOT NULL,       -- نام و نام‌خانوادگی یا نام شرکت
    IsCompany       BIT NOT NULL DEFAULT 0,
    Picture         NVARCHAR(500) NULL,           -- مسیر فایل تصویر
    NationalCode    NVARCHAR(50)  NULL,
    Phone           NVARCHAR(30)  NULL,
    Mobile          NVARCHAR(30)  NULL,
    Address         NVARCHAR(1000) NULL,
    Job             NVARCHAR(200) NULL,
    EmployeeCode    NVARCHAR(100) NULL,
    BankCardNumber  NVARCHAR(50)  NULL,
    BankAccountNumber NVARCHAR(50) NULL,
    Sheba           NVARCHAR(50)  NULL,
    Description     NVARCHAR(MAX) NULL,
    IsCustomer      BIT NOT NULL DEFAULT 0,
    IsSeller        BIT NOT NULL DEFAULT 0,
    IsEmployee      BIT NOT NULL DEFAULT 0,
    IsActive        BIT NOT NULL DEFAULT 1,
    CreatedAt       DATETIME2 NOT NULL DEFAULT GETDATE(),
    CreatedShamsiDate NVARCHAR(20) NULL,           -- تاریخ شمسی به شکل 1405/05/21
    UpdatedAt       DATETIME2 NULL,
    IsDeleted       BIT NOT NULL DEFAULT 0          -- Soft Delete
);
GO

-- رابطه چند به چند: هر شخص می‌تواند در چند گروه باشد
IF OBJECT_ID('PersonGroupMap', 'U') IS NOT NULL DROP TABLE PersonGroupMap;
CREATE TABLE PersonGroupMap (
    ID              INT IDENTITY(1,1) PRIMARY KEY,
    PersonRef       INT NOT NULL FOREIGN KEY REFERENCES Persons(ID),
    GroupRef        INT NOT NULL FOREIGN KEY REFERENCES PersonGroups(ID)
);
GO

-- =========================================================
-- گروه‌های کالا
-- =========================================================
IF OBJECT_ID('ProductGroups', 'U') IS NOT NULL DROP TABLE ProductGroups;
CREATE TABLE ProductGroups (
    ID              INT IDENTITY(1,1) PRIMARY KEY,
    Name            NVARCHAR(200) NOT NULL UNIQUE,
    Description     NVARCHAR(500) NULL
);
GO

-- =========================================================
-- کالاها
-- =========================================================
IF OBJECT_ID('Products', 'U') IS NOT NULL DROP TABLE Products;
CREATE TABLE Products (
    ID                  INT IDENTITY(1,1) PRIMARY KEY,
    Name                NVARCHAR(300) NOT NULL,
    Code                NVARCHAR(100) NULL,          -- کد دستی
    AutoCode            NVARCHAR(100) NULL,          -- کد خودکار سیستم
    GroupRef            INT NULL FOREIGN KEY REFERENCES ProductGroups(ID),
    Brand               NVARCHAR(150) NULL,
    Model               NVARCHAR(150) NULL,
    Color               NVARCHAR(100) NULL,
    Memory              NVARCHAR(100) NULL,          -- حافظه/رم
    Capacity            NVARCHAR(100) NULL,          -- ظرفیت/حافظه داخلی
    Specs               NVARCHAR(MAX) NULL,          -- مشخصات فنی
    HasSerial           BIT NOT NULL DEFAULT 0,       -- سریالی است؟ (موبایل/لپ‌تاپ/کنسول)
    BarCode             NVARCHAR(200) NULL,
    Unit                NVARCHAR(50)  NULL DEFAULT N'عدد',
    MinStock            DECIMAL(18,2) NOT NULL DEFAULT 0,
    OrderPoint          DECIMAL(18,2) NOT NULL DEFAULT 0,
    PurchasePrice       MONEY NOT NULL DEFAULT 0,     -- آخرین قیمت خرید (نمایشی؛ FIFO واقعی در ProductPurchaseLayers است)
    SalePrice           MONEY NOT NULL DEFAULT 0,
    ProfitPercent       DECIMAL(9,2) NOT NULL DEFAULT 0,
    Description         NVARCHAR(MAX) NULL,
    Picture             NVARCHAR(500) NULL,
    IsActive            BIT NOT NULL DEFAULT 1,
    CreatedAt           DATETIME2 NOT NULL DEFAULT GETDATE(),
    UpdatedAt           DATETIME2 NULL,
    IsDeleted           BIT NOT NULL DEFAULT 0
);
GO

-- شماره سریال/IMEI هر واحد کالا (برای کنترل یکتا بودن سریال کالاهای موجود)
IF OBJECT_ID('ProductSerials', 'U') IS NOT NULL DROP TABLE ProductSerials;
CREATE TABLE ProductSerials (
    ID              INT IDENTITY(1,1) PRIMARY KEY,
    ProductRef      INT NOT NULL FOREIGN KEY REFERENCES Products(ID),
    SerialNumber    NVARCHAR(200) NOT NULL,
    IMEI            NVARCHAR(200) NULL,
    Status          NVARCHAR(50) NOT NULL DEFAULT N'InStock',  -- InStock, Sold, Returned
    PurchaseLayerRef INT NULL,   -- در مرحله ۲ (FIFO) به لایه خرید متصل می‌شود
    CreatedAt       DATETIME2 NOT NULL DEFAULT GETDATE()
);
GO
-- جلوگیری از ثبت دوباره یک سریال برای کالاهای «موجود»
CREATE UNIQUE INDEX UX_ProductSerials_Unique_InStock
    ON ProductSerials(SerialNumber)
    WHERE Status = N'InStock';
GO

-- =========================================================
-- تنظیمات کلی نرم‌افزار (کلید-مقدار)
-- =========================================================
IF OBJECT_ID('Settings', 'U') IS NOT NULL DROP TABLE Settings;
CREATE TABLE Settings (
    ID              INT IDENTITY(1,1) PRIMARY KEY,
    SettingKey      NVARCHAR(150) NOT NULL UNIQUE,
    SettingValue    NVARCHAR(MAX) NULL,
    Description     NVARCHAR(300) NULL
);
GO

-- مقادیر پیش‌فرض تنظیمات
INSERT INTO Settings (SettingKey, SettingValue, Description) VALUES
(N'StoreName', N'فروشگاه من', N'نام فروشگاه'),
(N'StoreAddress', N'', N'آدرس فروشگاه'),
(N'StorePhone', N'', N'تلفن فروشگاه'),
(N'AllowNegativeStock', N'0', N'اجازه فروش با موجودی منفی (0=خیر, 1=بله)'),
(N'DefaultProfitPercent', N'20', N'درصد سود پیش‌فرض برای محاسبه قیمت فروش');
GO

PRINT N'✅ ساختار پایه دیتابیس با موفقیت ساخته شد.';
