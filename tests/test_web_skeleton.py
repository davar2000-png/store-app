# -*- coding: utf-8 -*-
"""
Phase 16B — تست‌های اسکلت وب.

این تست‌ها فقط لایه‌ی HTTP (FastAPI) را بررسی می‌کنند و به هیچ service یا
دیتابیس واقعی دست نمی‌زنند.
"""

from fastapi.testclient import TestClient

from web.app import app

client = TestClient(app)


def test_home_returns_200():
    response = client.get("/")
    assert response.status_code == 200


def test_home_returns_html():
    response = client.get("/")
    assert "text/html" in response.headers["content-type"]


def test_home_is_persian_rtl():
    response = client.get("/")
    body = response.text
    assert 'dir="rtl"' in body
    assert 'lang="fa"' in body


def test_home_has_storeapp_title():
    response = client.get("/")
    assert "StoreApp" in response.text


def test_health_returns_200():
    response = client.get("/health")
    assert response.status_code == 200


def test_health_reports_status_ok():
    response = client.get("/health")
    data = response.json()
    assert data["status"] == "ok"


def test_health_reports_database_field():
    response = client.get("/health")
    data = response.json()
    assert "database" in data
    assert "status" in data["database"]
    # این محیط sandbox به SQL Server واقعی متصل نیست؛ گزارش باید صادقانه باشد.
    assert data["database"]["status"] in ("connected", "not_connected")


def test_static_style_css_returns_200():
    response = client.get("/static/style.css")
    assert response.status_code == 200


def test_static_style_css_is_css():
    response = client.get("/static/style.css")
    assert "css" in response.headers["content-type"]


def test_nonexistent_route_returns_404():
    response = client.get("/nonexistent-route")
    assert response.status_code == 404
