# -*- coding: utf-8 -*-
"""ابزار کار با تاریخ شمسی (جلالی)"""

import jdatetime
import datetime


def today_shamsi_str() -> str:
    """تاریخ امروز به شکل 1405/05/21"""
    return jdatetime.date.today().strftime("%Y/%m/%d")


def gregorian_to_shamsi(g_date: datetime.datetime) -> str:
    """تبدیل تاریخ میلادی به رشته شمسی"""
    if g_date is None:
        return ""
    j = jdatetime.date.fromgregorian(date=g_date.date() if isinstance(g_date, datetime.datetime) else g_date)
    return j.strftime("%Y/%m/%d")


def shamsi_str_to_gregorian(shamsi_str: str) -> datetime.date:
    """تبدیل رشته شمسی (1405/05/21) به تاریخ میلادی"""
    parts = shamsi_str.strip().split("/")
    y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
    j = jdatetime.date(y, m, d)
    return j.togregorian()


def add_months_shamsi(shamsi_str: str, months: int) -> str:
    """یک تاریخ شمسی را چند ماه جلو می‌برد و رشته شمسی جدید را برمی‌گرداند (برای سررسید اقساط)"""
    parts = shamsi_str.strip().split("/")
    y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
    total_months = (m - 1) + months
    new_y = y + total_months // 12
    new_m = total_months % 12 + 1
    # اگر روز از تعداد روزهای ماه مقصد بیشتر بود (مثلا ۳۱ در ماهی که ۳۰ روزه است)
    max_day = 29 if new_m == 12 else (31 if new_m <= 6 else 30)
    new_d = min(d, max_day)
    try:
        j = jdatetime.date(new_y, new_m, new_d)
    except ValueError:
        j = jdatetime.date(new_y, new_m, max_day)
    return j.strftime("%Y/%m/%d")
