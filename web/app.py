# -*- coding: utf-8 -*-
"""
Phase 16B — Web Backend Skeleton
Phase 16C — Auth Extraction + Session Login (فقط API؛ بدون HTML Login UI،
طبق تصمیم صریح پروژه — فرم HTML به Phase16D موکول شده است)

هدف اصلی این فایل ساخت یک اسکلت وب واقعی (FastAPI + Jinja2) است تا StoreApp
بتواند به‌صورت محلی از طریق Chrome باز شود.

در Phase16B هیچ business logic ای اینجا بازنویسی نشد. در Phase16C، دو
endpoint جدید (`/login`, `/logout`) اضافه شده که فقط سرویس‌های مستقل
`services/auth_service.py` و `services/web_session_service.py` را
فراخوانی می‌کنند — هیچ منطق Auth/Session جدیدی مستقیماً در این فایل
نوشته نمی‌شود.

این ماژول عمداً هیچ اتصال دیتابیس واقعی برقرار نمی‌کند مگر در endpointهایی
که صریحاً به دیتابیس نیاز دارند (`/health`, `/login`, `/logout`).
"""

import os
import sys
from pathlib import Path

# اجازه import کردن `config` و `database.db` از ریشه‌ی پروژه، دقیقاً همان
# الگویی که database/db.py از آن استفاده می‌کند.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.requests import Request

from services import auth_service, web_session_service

WEB_DIR = Path(__file__).resolve().parent

#: نام Cookie که توکن خام Session وب در آن نگه‌داری می‌شود.
SESSION_COOKIE_NAME = "storeapp_session"

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


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/login")
def login(payload: LoginRequest, request: Request, response: Response):
    """
    ورود به سیستم (Phase 16C).

    فقط auth_service.authenticate_user و web_session_service.create_session
    را فراخوانی می‌کند؛ هیچ منطق Auth مستقیماً اینجا نوشته نشده است.
    در صورت موفقیت، توکن خام Session در یک Cookie با HttpOnly قرار می‌گیرد
    (هرگز در بدنه پاسخ JSON برگردانده نمی‌شود).
    """
    try:
        user = auth_service.authenticate_user(payload.username, payload.password)
    except Exception as exc:  # noqa: BLE001 - همان اصل صادقانه بودن /health
        return JSONResponse(
            status_code=503,
            content={"status": "error", "detail": f"اتصال به دیتابیس برقرار نشد: {exc}"},
        )

    if user is None:
        return JSONResponse(
            status_code=401,
            content={"status": "error", "detail": "نام کاربری یا رمز عبور نادرست است."},
        )

    try:
        raw_token = web_session_service.create_session(
            user_id=user["ID"],
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=503,
            content={"status": "error", "detail": f"اتصال به دیتابیس برقرار نشد: {exc}"},
        )

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=raw_token,
        httponly=True,
        samesite="lax",
    )

    return {
        "status": "ok",
        "user": {
            "id": user["ID"],
            "username": user["Username"],
            "fullName": user.get("FullName"),
        },
    }


@app.post("/logout")
def logout(request: Request, response: Response):
    """
    خروج از سیستم (Phase 16C).

    فقط web_session_service.revoke_session را فراخوانی می‌کند و Cookie
    Session را از مرورگر پاک می‌کند.
    """
    raw_token = request.cookies.get(SESSION_COOKIE_NAME)
    try:
        web_session_service.revoke_session(raw_token)
    except Exception:  # noqa: BLE001 - Logout همیشه باید از دید کاربر موفق باشد
        pass
    response.delete_cookie(key=SESSION_COOKIE_NAME)
    return {"status": "ok"}


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
