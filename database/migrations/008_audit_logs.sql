-- Phase 14 Audit Logs

IF OBJECT_ID('AuditLogs', 'U') IS NULL
BEGIN
    CREATE TABLE AuditLogs (
        ID INT IDENTITY(1,1) PRIMARY KEY,

        UserRef INT NULL,
        ActionType NVARCHAR(50) NOT NULL,
        TableName NVARCHAR(100) NOT NULL,
        RecordID INT NULL,

        Details NVARCHAR(MAX) NULL,

        ActionDate DATETIME NOT NULL DEFAULT GETDATE(),

        CorrelationID UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),

        CONSTRAINT FK_AuditLogs_Users
            FOREIGN KEY (UserRef)
            REFERENCES Users(ID)
    );

    CREATE INDEX IX_AuditLogs_Table_Record
    ON AuditLogs(TableName, RecordID);

    CREATE INDEX IX_AuditLogs_User_Date
    ON AuditLogs(UserRef, ActionDate);
END
