# -*- coding: utf-8 -*-
"""
Phase 14.3 — Audit Reliability Hardening

قبلاً create_audit_entry هر خطای نوشتن در AuditLogs را با `except Exception:
pass` کاملاً بی‌صدا می‌بلعید؛ یعنی اگر نوشتن Audit به هر دلیلی (قطع اتصال DB،
خطای Schema و ...) شکست می‌خورد، هیچ‌کس متوجه نمی‌شد — نه Caller و نه هیچ Log
ی. برای یک سیستم Audit که هدفش دقیقاً قابلیت اثبات/ردیابی است، شکست خاموش
غیرقابل قبول است.

این تست‌ها تضمین می‌کنند:
1. مسیر موفق مثل قبل کار می‌کند (Backward-Compatible).
2. مسیر شکست دیگر بی‌صدا نیست: `audit_write_failed=True` در نتیجه برمی‌گردد
   و خطا Log می‌شود؛ اما (طراحی عمدی) Exception به بیرون Propagate نمی‌شود،
   چون create_audit_entry نباید بتواند یک تراکنش تجاری واقعی (فروش/خرید/
   تسویه) را که audit فقط ضمیمه آن است متوقف کند.
"""

import logging

import services.audit_service as audit_service
from tests._fake_database import FakeDatabase


def setup_function():
    FakeDatabase.reset()
    audit_service.Database = FakeDatabase


def test_create_audit_entry_happy_path_persists_row():
    result = audit_service.create_audit_entry(
        user_id=7,
        action_type="Create",
        table_name="SalesInvoices",
        record_id=100,
        details="Sales invoice INV-1",
    )

    assert result["audit_write_failed"] is False
    assert len(FakeDatabase.audit_logs) == 1
    row = FakeDatabase.audit_logs[0]
    assert row["UserRef"] == 7
    assert row["ActionType"] == "Create"
    assert row["TableName"] == "SalesInvoices"
    assert row["CorrelationID"] == result["CorrelationID"]


def test_create_audit_entry_db_failure_is_not_silent(caplog):
    FakeDatabase.fail_audit_insert = True

    with caplog.at_level(logging.ERROR, logger="services.audit_service"):
        result = audit_service.create_audit_entry(
            user_id=7,
            action_type="Update",
            table_name="Cheques",
            record_id=5,
            details="Cheque status changed",
        )

    # هیچ رکوردی واقعاً ذخیره نشده
    assert len(FakeDatabase.audit_logs) == 0
    # اما این بار caller/log می‌توانند بفهمند که نوشتن Audit شکست خورده
    assert result["audit_write_failed"] is True
    assert any("Audit write failed" in r.message for r in caplog.records)


def test_create_audit_entry_db_failure_does_not_raise():
    """
    عملیات تجاری اصلی (مثلاً ثبت فاکتور) نباید فقط به خاطر شکست Audit متوقف شود.
    """
    FakeDatabase.fail_audit_insert = True

    # نباید Exception بیرون بزند
    result = audit_service.create_audit_entry(1, "Create", "PurchaseInvoices", 1)
    assert result["audit_write_failed"] is True


def test_log_action_is_alias_for_create_audit_entry():
    result = audit_service.log_action(3, "Create", "Payments", 9, "Payment P-1")
    assert result["audit_write_failed"] is False
    assert len(FakeDatabase.audit_logs) == 1


def test_get_recent_logs_orders_newest_first():
    audit_service.create_audit_entry(1, "Create", "SalesInvoices", 1)
    audit_service.create_audit_entry(1, "Create", "SalesInvoices", 2)
    audit_service.create_audit_entry(1, "Create", "SalesInvoices", 3)

    rows = audit_service.get_recent_logs()

    assert [r["RecordID"] for r in rows] == [3, 2, 1]
