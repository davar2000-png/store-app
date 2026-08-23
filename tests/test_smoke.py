# -*- coding: utf-8 -*-
"""
Smoke Test — Phase 12

⚠️ صادقانه: این تست فقط بررسی می‌کند که تمام فایل‌های اصلی برنامه بدون
خطای Syntax/Import قابل بارگذاری هستند (Application Starts سطح پایه).
این تست:
- به SQL Server واقعی وصل نمی‌شود.
- عملکرد واقعی Login، دسترسی Admin/User، AutoSave، یا Recovery را تست
  نمی‌کند (این‌ها نیاز به یک دیتابیس واقعی و PyQt6 Event Loop دارند که
  در این محیط sandbox در دسترس نیست).

اجرا: python -m pytest tests/test_smoke.py -v
یا:   python tests/test_smoke.py
"""

import sys
import os
import importlib

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# لیست ماژول‌های Service — نباید نیاز به اتصال دیتابیس در سطح Import داشته باشند
SERVICE_MODULES = [
    "services.settings_service",
    "services.session_service",
    "services.draft_service",
    "services.inventory_service",
    "services.sales_service",
    "services.financial_service",
    "services.invoices_service",
    "services.communication_service",
    "services.backup_service",
    "services.reports_service",
    "services.assistant_service",
    "services.robat_import_service",
    "services.accounting_service",
]

UTIL_MODULES = [
    "utils.security",
    "utils.persian_date",
]

DATABASE_MODULES = [
    "database.db",
]


def _try_import(module_name: str):
    try:
        importlib.import_module(module_name)
        return True, None
    except Exception as e:  # noqa: BLE001 - می‌خواهیم هر نوع خطا را بگیریم و گزارش کنیم
        return False, str(e)


def test_service_modules_import():
    failures = []
    for m in SERVICE_MODULES:
        ok, err = _try_import(m)
        if not ok:
            failures.append(f"{m}: {err}")
    assert not failures, "این ماژول‌ها Import نشدند:\n" + "\n".join(failures)


def test_util_modules_import():
    failures = []
    for m in UTIL_MODULES:
        ok, err = _try_import(m)
        if not ok:
            failures.append(f"{m}: {err}")
    assert not failures, "این ماژول‌ها Import نشدند:\n" + "\n".join(failures)


def test_database_module_imports():
    failures = []
    for m in DATABASE_MODULES:
        ok, err = _try_import(m)
        if not ok:
            failures.append(f"{m}: {err}")
    assert not failures, "این ماژول‌ها Import نشدند:\n" + "\n".join(failures)


def test_ui_modules_syntax_only():
    """
    ماژول‌های ui/ نیاز به PyQt6 QApplication دارند تا واقعاً Import شوند؛
    این تست فقط سلامت Syntax فایل را با ast.parse بررسی می‌کند، نه اجرای
    واقعی PyQt6.
    """
    import ast
    ui_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui")
    failures = []
    for fname in os.listdir(ui_dir):
        if not fname.endswith(".py"):
            continue
        path = os.path.join(ui_dir, fname)
        with open(path, encoding="utf-8") as f:
            src = f.read()
        try:
            ast.parse(src)
        except SyntaxError as e:
            failures.append(f"{fname}: {e}")
    assert not failures, "این فایل‌های ui/ خطای Syntax دارند:\n" + "\n".join(failures)


if __name__ == "__main__":
    # اجرای ساده بدون pytest، برای محیط‌هایی که pytest نصب نیست
    tests = [
        test_database_module_imports,
        test_util_modules_import,
        test_service_modules_import,
        test_ui_modules_syntax_only,
    ]
    passed, failed = 0, 0
    for t in tests:
        try:
            t()
            print(f"PASS: {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL: {t.__name__}\n  {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
