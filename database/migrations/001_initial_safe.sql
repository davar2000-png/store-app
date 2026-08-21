-- =========================================================
-- Migration 001 — هسته نرم‌افزار (نسخه امن/غیرمخرب)
-- =========================================================
-- برخلاف database/schema/001_fresh_install.sql، این فایل
-- هیچ‌وقت جدول موجود را DROP نمی‌کند. اگر جدولی از قبل باشد،
-- به‌سادگی رد می‌شود و دست‌نخورده باقی می‌ماند. فقط جداولی که
-- هنوز ساخته نشده‌اند اضافه می‌شوند.
--
-- استفاده مناسب: روی دیتابیسی که از قبل داده واقعی دارد.
-- =========================================================

IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'StoreAppDB')
BEGIN
    CREATE DATABASE StoreAppDB;
END
GO

USE StoreAppDB;
GO

-- ---------------------------------------------------------
-- Users
-- ---------------------------------------------------------
IF OBJECT_ID('Users', 'U') IS NULL
BEGIN
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
END
GO

-- ---------------------------------------------------------
-- UserPermissions
-- ---------------------------------------------------------
IF OBJECT_ID('UserPermissions', 'U') IS NULL
BEGIN
    CREATE TABLE UserPermissions (
        ID              INT IDENTITY(1,1) PRIMARY KEY,
        UserRef         INT NOT NULL FOREIGN KEY REFERENCES Users(ID),
        PermissionKey   NVARCHAR(100) NOT NULL,
        IsAllowed       BIT NOT NULL DEFAULT 0
    );
END
GO

-- ---------------------------------------------------------
-- ActivityLog
-- ---------------------------------------------------------
IF OBJECT_ID('ActivityLog', 'U') IS NULL
BEGIN
    CREATE TABLE ActivityLog (
        ID              INT IDENTITY(1,1) PRIMARY KEY,
        UserRef         INT NULL FOREIGN KEY REFERENCES Users(ID),
        ActionType      NVARCHAR(100) NOT NULL,
        TableName       NVARCHAR(100) NOT NULL,
        RecordID        INT NULL,
        Details         NVARCHAR(MAX) NULL,
        ActionDate      DATETIME2 NOT NULL DEFAULT GETDATE()
    );
END
GO

-- ---------------------------------------------------------
-- PersonGroups
-- ---------------------------------------------------------
IF OBJECT_ID('PersonGroups', 'U') IS NULL
BEGIN
    CREATE TABLE PersonGroups (
        ID              INT IDENTITY(1,1) PRIMARY KEY,
        Name            NVARCHAR(150) NOT NULL UNIQUE,
        Description     NVARCHAR(500) NULL
    );
END
GO

-- ---------------------------------------------------------
-- Persons
-- ---------------------------------------------------------
IF OBJECT_ID('Persons', 'U') IS NULL
BEGIN
    CREATE TABLE Persons (
        ID              INT IDENTITY(1,1) PRIMARY KEY,
        FullName        NVARCHAR(300) NOT NULL,
        IsCompany       BIT NOT NULL DEFAULT 0,
        Picture         NVARCHAR(500) NULL,
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
        CreatedShamsiDate NVARCHAR(20) NULL,
        UpdatedAt       DATETIME2 NULL,
        IsDeleted       BIT NOT NULL DEFAULT 0
    );
END
GO

-- ---------------------------------------------------------
-- PersonGroupMap
-- ---------------------------------------------------------
IF OBJECT_ID('PersonGroupMap', 'U') IS NULL
BEGIN
    CREATE TABLE PersonGroupMap (
        ID              INT IDENTITY(1,1) PRIMARY KEY,
        PersonRef       INT NOT NULL FOREIGN KEY REFERENCES Persons(ID),
        GroupRef        INT NOT NULL FOREIGN KEY REFERENCES PersonGroups(ID)
    );
END
GO

-- ---------------------------------------------------------
-- ProductGroups
-- ---------------------------------------------------------
IF OBJECT_ID('ProductGroups', 'U') IS NULL
BEGIN
    CREATE TABLE ProductGroups (
        ID              INT IDENTITY(1,1) PRIMARY KEY,
        Name            NVARCHAR(200) NOT NULL UNIQUE,
        Description     NVARCHAR(500) NULL
    );
END
GO

-- ---------------------------------------------------------
-- Products
-- ---------------------------------------------------------
IF OBJECT_ID('Products', 'U') IS NULL
BEGIN
    CREATE TABLE Products (
        ID                  INT IDENTITY(1,1) PRIMARY KEY,
        Name                NVARCHAR(300) NOT NULL,
        Code                NVARCHAR(100) NULL,
        AutoCode            NVARCHAR(100) NULL,
        GroupRef            INT NULL FOREIGN KEY REFERENCES ProductGroups(ID),
        Brand               NVARCHAR(150) NULL,
        Model               NVARCHAR(150) NULL,
        Color               NVARCHAR(100) NULL,
        Memory              NVARCHAR(100) NULL,
        Capacity            NVARCHAR(100) NULL,
        Specs               NVARCHAR(MAX) NULL,
        HasSerial           BIT NOT NULL DEFAULT 0,
        BarCode             NVARCHAR(200) NULL,
        Unit                NVARCHAR(50)  NULL DEFAULT N'عدد',
        MinStock            DECIMAL(18,2) NOT NULL DEFAULT 0,
        OrderPoint          DECIMAL(18,2) NOT NULL DEFAULT 0,
        PurchasePrice       MONEY NOT NULL DEFAULT 0,
        SalePrice           MONEY NOT NULL DEFAULT 0,
        ProfitPercent       DECIMAL(9,2) NOT NULL DEFAULT 0,
        Description         NVARCHAR(MAX) NULL,
        Picture             NVARCHAR(500) NULL,
        IsActive            BIT NOT NULL DEFAULT 1,
        CreatedAt           DATETIME2 NOT NULL DEFAULT GETDATE(),
        UpdatedAt           DATETIME2 NULL,
        IsDeleted           BIT NOT NULL DEFAULT 0
    );
END
GO

-- ---------------------------------------------------------
-- ProductSerials
-- ---------------------------------------------------------
IF OBJECT_ID('ProductSerials', 'U') IS NULL
BEGIN
    CREATE TABLE ProductSerials (
        ID              INT IDENTITY(1,1) PRIMARY KEY,
        ProductRef      INT NOT NULL FOREIGN KEY REFERENCES Products(ID),
        SerialNumber    NVARCHAR(200) NOT NULL,
        IMEI            NVARCHAR(200) NULL,
        Status          NVARCHAR(50) NOT NULL DEFAULT N'InStock',
        PurchaseLayerRef INT NULL,
        CreatedAt       DATETIME2 NOT NULL DEFAULT GETDATE()
    );

    CREATE UNIQUE INDEX UX_ProductSerials_Unique_InStock
        ON ProductSerials(SerialNumber)
        WHERE Status = N'InStock';
END
GO

-- ---------------------------------------------------------
-- Settings
-- ---------------------------------------------------------
IF OBJECT_ID('Settings', 'U') IS NULL
BEGIN
    CREATE TABLE Settings (
        ID              INT IDENTITY(1,1) PRIMARY KEY,
        SettingKey      NVARCHAR(150) NOT NULL UNIQUE,
        SettingValue    NVARCHAR(MAX) NULL,
        Description     NVARCHAR(300) NULL
    );

    INSERT INTO Settings (SettingKey, SettingValue, Description) VALUES
    (N'StoreName', N'فروشگاه من', N'نام فروشگاه'),
    (N'StoreAddress', N'', N'آدرس فروشگاه'),
    (N'StorePhone', N'', N'تلفن فروشگاه'),
    (N'AllowNegativeStock', N'0', N'اجازه فروش با موجودی منفی (0=خیر, 1=بله)'),
    (N'DefaultProfitPercent', N'20', N'درصد سود پیش‌فرض برای محاسبه قیمت فروش');
END
GO

PRINT N'✅ Migration 001 اجرا شد (جداول موجود دست‌نخورده باقی ماندند).';
