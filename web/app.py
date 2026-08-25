# -*- coding: utf-8 -*-
"""
Phase 16B — Web Backend Skeleton

هدف این فایل فقط ساخت یک اسکلت وب واقعی (FastAPI + Jinja2) است تا StoreApp
بتواند به‌صورت محلی از طریق Chrome باز شود.

هیچ business logic ای اینجا بازنویسی نمی‌شود. هیچ service ای در این فاز
فراخوانی یا تغییر داده نمی‌شود. این فایل فقط زیرساخت HTTP را فراهم می‌کند.

این ماژول عمداً هیچ اتصال دیتابیس واقعی برقرار نمی‌کند مگر در endpoint
`/health` و آن هم فقط برای گزارش وضعیت، نه برای هیچ عملیات دیگر.
"""

import os
import sys
from pathlib import Path

# اجازه import کردن `config` و `database.db` از ریشه‌ی پروژه، دقیقاً همان
# الگویی که database/db.py از آن استفاده می‌کند.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

WEB_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="StoreApp Web (Skeleton)",
    description="Phase 16B — اسکلت اولیه وب برای StoreApp",
)

app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")

templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))


def check_database_status() -> dict:
    """
    تلاش صادقانه برای بررسی اتصال به دیتابیس.

    این تابع هیچ اتصال موفق را فرض نمی‌کند. اگر درایور ODBC یا SQL Server
    در دسترس نباشد، وضعیت واقعی (not_connected) همراه با پیام خطا برگردانده
    می‌شود. هرگز خروجی fake یا optimistic تولید نمی‌شود.
    """
    try:
        # import محلی تا در صورت نبود pyodbc، کل اپ web از کار نیفتد.
        from database.db import Database

        db = Database()
        db.connect()
        db.close()
        return {"status": "connected"}
    except Exception as exc:  # noqa: BLE001 - می‌خواهیم هر نوع خطا را صادقانه گزارش کنیم
        return {"status": "not_connected", "detail": str(exc)}


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"page_title": "پیشخوان — StoreApp"},
    )


@app.get("/health")
def health():
    db_status = check_database_status()
    return {
        "status": "ok",
        "phase": "16B - Web Backend Skeleton",
        "database": db_status,
    }


if __name__ == "__main__":
    import uvicorn

    # فقط برای اجرای محلی روی سیستم توسعه؛ منتشر شدن روی شبکه در این فاز
    # مجاز نیست. صراحتاً روی localhost محدود شده است.
    uvicorn.run(
        "web.app:app",
        host="127.0.0.1",
        port=int(os.environ.get("STOREAPP_WEB_PORT", "8000")),
        reload=False,
    )
