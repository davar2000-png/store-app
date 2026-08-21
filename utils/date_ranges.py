# -*- coding: utf-8 -*-
"""محاسبه بازه‌های تاریخ شمسی (امروز، فردا، این هفته، این ماه) برای دستیار هوش مصنوعی و گزارش‌ها"""

import jdatetime


def today_str() -> str:
    return jdatetime.date.today().strftime("%Y/%m/%d")


def tomorrow_str() -> str:
    d = jdatetime.date.today() + jdatetime.timedelta(days=1)
    return d.strftime("%Y/%m/%d")


def yesterday_str() -> str:
    d = jdatetime.date.today() - jdatetime.timedelta(days=1)
    return d.strftime("%Y/%m/%d")


def month_start_str() -> str:
    today = jdatetime.date.today()
    return jdatetime.date(today.year, today.month, 1).strftime("%Y/%m/%d")


def month_end_str() -> str:
    today = jdatetime.date.today()
    days_in_month = 31 if today.month <= 6 else (30 if today.month <= 11 else 29)
    return jdatetime.date(today.year, today.month, days_in_month).strftime("%Y/%m/%d")


def week_start_str() -> str:
    """هفته شمسی از شنبه شروع می‌شود (weekday(): شنبه=0)"""
    today = jdatetime.date.today()
    start = today - jdatetime.timedelta(days=today.weekday())
    return start.strftime("%Y/%m/%d")


def week_end_str() -> str:
    today = jdatetime.date.today()
    end = today + jdatetime.timedelta(days=(6 - today.weekday()))
    return end.strftime("%Y/%m/%d")


def last_month_start_str() -> str:
    today = jdatetime.date.today()
    month = today.month - 1
    year = today.year
    if month == 0:
        month = 12
        year -= 1
    return jdatetime.date(year, month, 1).strftime("%Y/%m/%d")


def last_month_end_str() -> str:
    return month_start_str()  # یک روز قبل از شروع این ماه هم کافی است برای بازه تقریبی
