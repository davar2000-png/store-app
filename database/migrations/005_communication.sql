-- =========================================================
-- نرم‌افزار حسابداری فروشگاه موبایل، لپ‌تاپ و کنسول بازی
-- مرحله ۶: ارتباط با مشتری (پیامک و اتصال به پیام‌رسان بله)
-- =========================================================
-- این فایل فقط چیزهای جدید اضافه می‌کند و به داده‌های قبلی
-- هیچ آسیبی نمی‌رساند.
-- =========================================================

USE StoreAppDB;
GO

-- =========================================================
-- ۱) شناسه چت «بله» هر شخص (برای ارسال پیام از طریق ربات بله)
-- =========================================================
IF NOT EXISTS (
    SELECT * FROM sys.columns
    WHERE object_id = OBJECT_ID('Persons') AND name = 'BalehChatId'
)
BEGIN
    ALTER TABLE Persons ADD BalehChatId NVARCHAR(100) NULL;
END
GO

-- =========================================================
-- ۲) قالب‌های پیام (پیامک / بله) — قابل ویرایش توسط کاربر
-- =========================================================
IF OBJECT_ID('MessageTemplates', 'U') IS NULL
BEGIN
    CREATE TABLE MessageTemplates (
        ID              INT IDENTITY(1,1) PRIMARY KEY,
        TemplateKey     NVARCHAR(50) NOT NULL UNIQUE,   -- کلید ثابت داخلی (تغییر نکند)
        Title           NVARCHAR(200) NOT NULL,          -- عنوان فارسی نمایشی
        Content         NVARCHAR(1000) NOT NULL,         -- متن با پارامترهای {نام}، {مبلغ} و ...
        IsActive        BIT NOT NULL DEFAULT 1
    );

    INSERT INTO MessageTemplates (TemplateKey, Title, Content) VALUES
    (N'InstallmentReminder', N'یادآوری قسط',
     N'مشتری گرامی {نام}، قسط شما به مبلغ {مبلغ} تومان در تاریخ {تاریخ} سررسید می‌شود. با تشکر - {نام_فروشگاه}'),
    (N'InstallmentOverdue', N'قسط سررسیدشده',
     N'مشتری گرامی {نام}، قسط شما به مبلغ {مبلغ} تومان از تاریخ {تاریخ} سررسید گذشته است. لطفاً هرچه سریع‌تر تسویه فرمایید. - {نام_فروشگاه}'),
    (N'CustomerDebt', N'اعلام بدهی مشتری',
     N'مشتری گرامی {نام}، مانده حساب شما {مبلغ} تومان است. - {نام_فروشگاه}'),
    (N'Settlement', N'تسویه حساب',
     N'مشتری گرامی {نام}، حساب شما با مبلغ {مبلغ} تومان تسویه شد. با تشکر از خرید شما - {نام_فروشگاه}'),
    (N'InvoiceRegistered', N'ثبت فاکتور',
     N'مشتری گرامی {نام}، فاکتور شماره {شماره_فاکتور} به مبلغ {مبلغ} تومان ثبت شد. - {نام_فروشگاه}'),
    (N'PaymentReceived', N'دریافت وجه',
     N'مشتری گرامی {نام}، مبلغ {مبلغ} تومان از شما دریافت شد. با تشکر - {نام_فروشگاه}'),
    (N'Custom', N'پیام سفارشی (متن آزاد)', N'');
END
GO

-- =========================================================
-- ۳) تاریخچه پیام‌های ارسال‌شده
-- =========================================================
IF OBJECT_ID('MessageLog', 'U') IS NULL
BEGIN
    CREATE TABLE MessageLog (
        ID              INT IDENTITY(1,1) PRIMARY KEY,
        PersonRef       INT NULL FOREIGN KEY REFERENCES Persons(ID),
        Channel         NVARCHAR(20) NOT NULL,     -- SMS / Baleh
        TemplateKey     NVARCHAR(50) NULL,
        MessageText     NVARCHAR(1000) NOT NULL,
        Status          NVARCHAR(20) NOT NULL,      -- Sent / Failed
        ErrorText       NVARCHAR(1000) NULL,
        ShamsiDate      NVARCHAR(20) NULL,
        UserRef         INT NULL FOREIGN KEY REFERENCES Users(ID),
        CreatedAt       DATETIME2 NOT NULL DEFAULT GETDATE()
    );
END
GO

-- =========================================================
-- ۴) تنظیمات پیامک و بله (در همان جدول Settings کلید-مقدار قبلی)
-- =========================================================
IF NOT EXISTS (SELECT * FROM Settings WHERE SettingKey = N'SmsProvider')
    INSERT INTO Settings (SettingKey, SettingValue, Description) VALUES (N'SmsProvider', N'Kavenegar', N'نام سرویس پیامکی: Kavenegar / Melipayamak / Custom');
IF NOT EXISTS (SELECT * FROM Settings WHERE SettingKey = N'SmsApiKey')
    INSERT INTO Settings (SettingKey, SettingValue, Description) VALUES (N'SmsApiKey', N'', N'کلید API سرویس پیامکی (Kavenegar) یا رمز عبور (Melipayamak)');
IF NOT EXISTS (SELECT * FROM Settings WHERE SettingKey = N'SmsUsername')
    INSERT INTO Settings (SettingKey, SettingValue, Description) VALUES (N'SmsUsername', N'', N'نام کاربری سرویس پیامکی (در صورت نیاز - مثلا ملی‌پیامک)');
IF NOT EXISTS (SELECT * FROM Settings WHERE SettingKey = N'SmsSenderNumber')
    INSERT INTO Settings (SettingKey, SettingValue, Description) VALUES (N'SmsSenderNumber', N'', N'شماره خط ارسال پیامک');
IF NOT EXISTS (SELECT * FROM Settings WHERE SettingKey = N'SmsCustomUrlTemplate')
    INSERT INTO Settings (SettingKey, SettingValue, Description) VALUES (N'SmsCustomUrlTemplate', N'', N'فقط برای حالت Custom: آدرس API با پارامترهای {phone} و {text}');
IF NOT EXISTS (SELECT * FROM Settings WHERE SettingKey = N'BalehBotToken')
    INSERT INTO Settings (SettingKey, SettingValue, Description) VALUES (N'BalehBotToken', N'', N'توکن ربات پیام‌رسان بله');

PRINT N'✅ جداول مرحله ۶ (پیامک و بله) با موفقیت ساخته شد.';
