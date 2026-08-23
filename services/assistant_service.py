# -*- coding: utf-8 -*-
"""
دستیار هوش مصنوعی — به سؤالات مدیریتی فارسی با دسترسی خواندنی به داده‌های
حسابداری پاسخ می‌دهد. بر خلاف یک مدل زبانی آزاد، این دستیار بر اساس تشخیص
کلیدواژه‌های فارسی، دقیقاً به داده‌های واقعی دیتابیس (نه حدس یا توهم) متکی است
— یعنی هر پاسخ از یک کوئری واقعی روی دیتابیس گرفته می‌شود.

دستیار هرگز داده‌ای را تغییر نمی‌دهد؛ فقط خواندن (Read-Only) است.
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import Database
from services.audit_service import create_audit_entry
import services.reports_service as rs
from services.inventory_service import get_low_stock_products
from utils import date_ranges as dr


# =========================================================
# تنظیم فعال/غیرفعال بودن دستیار (نیازمند اجازه صریح کاربر)
# =========================================================
def is_assistant_enabled() -> bool:
    db = Database()
    row = db.fetch_one("SELECT SettingValue FROM Settings WHERE SettingKey = 'AiAssistantEnabled'")
    db.close()
    return row is not None and row["SettingValue"] == "1"


def set_assistant_enabled(enabled: bool):
    db = Database()
    existing = db.fetch_one("SELECT ID FROM Settings WHERE SettingKey = 'AiAssistantEnabled'")
    value = "1" if enabled else "0"
    if existing:
        db.execute("UPDATE Settings SET SettingValue = ? WHERE SettingKey = 'AiAssistantEnabled'", (value,))
        action = "Update"
        record_id = existing["ID"]
    else:
        record_id = db.execute(
            "INSERT INTO Settings (SettingKey, SettingValue, Description) VALUES (?, ?, ?)",
            ("AiAssistantEnabled", value, "دسترسی خواندنی دستیار هوش مصنوعی به داده‌های حسابداری")
        )
        action = "Create"
    db.close()

    create_audit_entry(None, action, "Settings", record_id, f"AiAssistantEnabled changed to {value}")


def fmt(n):
    try:
        return f"{float(n):,.0f}"
    except Exception:
        return str(n or "0")


# =========================================================
# هر تابع زیر یک «قابلیت» دستیار است — یک سؤال نمونه را پاسخ می‌دهد
# =========================================================
def _sales_today():
    rows, totals = rs.sales_report(dr.today_str(), dr.today_str())
    return f"فروش امروز ({dr.today_str()}): {totals['count']} فاکتور به مبلغ {fmt(totals['payable'])} تومان."


def _sales_this_month():
    rows, totals = rs.sales_report(dr.month_start_str(), dr.today_str())
    return (f"فروش از ابتدای این ماه ({dr.month_start_str()} تا {dr.today_str()}): "
            f"{totals['count']} فاکتور به مبلغ {fmt(totals['payable'])} تومان.")


def _sales_this_week():
    rows, totals = rs.sales_report(dr.week_start_str(), dr.today_str())
    return (f"فروش از ابتدای این هفته ({dr.week_start_str()} تا {dr.today_str()}): "
            f"{totals['count']} فاکتور به مبلغ {fmt(totals['payable'])} تومان.")


def _profit_today():
    rows, totals = rs.profit_report(dr.today_str(), dr.today_str(), "invoice")
    return f"سود امروز: {fmt(totals['total_profit'])} تومان (از {fmt(totals['total_sale'])} تومان فروش)."


def _profit_this_month():
    rows, totals = rs.profit_report(dr.month_start_str(), dr.today_str(), "invoice")
    return (f"سود این ماه (تا امروز): {fmt(totals['total_profit'])} تومان "
            f"(از {fmt(totals['total_sale'])} تومان فروش و {fmt(totals['total_cost'])} تومان بهای تمام‌شده).")


def _top_selling_products():
    rows, totals = rs.profit_report(dr.month_start_str(), dr.today_str(), "product")
    if not rows:
        return "در این ماه هنوز هیچ فروشی ثبت نشده."
    top5 = sorted(rows, key=lambda r: float(r["TotalQty"] or 0), reverse=True)[:5]
    lines = [f"{i+1}. {r['ProductName']} — {fmt(r['TotalQty'])} عدد، سود: {fmt(r['Profit'])} تومان"
             for i, r in enumerate(top5)]
    return "پرفروش‌ترین کالاهای این ماه:\n" + "\n".join(lines)


def _top_debtor_customer():
    debtors, total = rs.debtors_report()
    if not debtors:
        return "در حال حاضر هیچ مشتری بدهکاری ثبت نشده."
    top = max(debtors, key=lambda d: d["Debt"])
    return f"بیشترین بدهی مربوط به «{top['FullName']}» با مبلغ {fmt(top['Debt'])} تومان است."


def _installments_tomorrow():
    rows, total = rs.installments_report("Pending")
    tomorrow = dr.tomorrow_str()
    due_tomorrow = [r for r in rows if r["DueShamsiDate"] == tomorrow]
    if not due_tomorrow:
        return f"برای فردا ({tomorrow}) هیچ قسطی سررسید ندارد."
    total_amount = sum(float(r["Amount"]) for r in due_tomorrow)
    names = "، ".join(sorted(set(r["CustomerName"] for r in due_tomorrow)))
    return f"فردا ({tomorrow}) {len(due_tomorrow)} قسط به مبلغ کل {fmt(total_amount)} تومان سررسید دارد. مشتریان: {names}"


def _installments_today():
    rows, total = rs.installments_report("Pending")
    today = dr.today_str()
    due_today = [r for r in rows if r["DueShamsiDate"] == today]
    if not due_today:
        return f"امروز ({today}) هیچ قسطی سررسید ندارد."
    total_amount = sum(float(r["Amount"]) for r in due_today)
    return f"امروز {len(due_today)} قسط به مبلغ کل {fmt(total_amount)} تومان سررسید دارد."


def _overdue_installments():
    rows, total = rs.installments_report("Pending")
    today = dr.today_str()
    overdue = [r for r in rows if r["DueShamsiDate"] < today]
    if not overdue:
        return "هیچ قسط سررسیدگذشته‌ای وجود ندارد."
    total_amount = sum(float(r["Amount"]) for r in overdue)
    return f"{len(overdue)} قسط سررسیدگذشته به مبلغ کل {fmt(total_amount)} تومان وجود دارد."


def _cheques_this_week():
    rows, total = rs.cheques_report()
    start, end = dr.week_start_str(), dr.week_end_str()
    this_week = [r for r in rows if r["DueShamsiDate"] and start <= r["DueShamsiDate"] <= end]
    if not this_week:
        return "این هفته هیچ چکی سررسید ندارد."
    total_amount = sum(float(r["Amount"]) for r in this_week)
    lines = [f"- {r['ChequeNumber']} ({'دریافتی' if r['ChequeType']=='Received' else 'پرداختی'}) "
             f"از {r['PersonName']}، مبلغ {fmt(r['Amount'])}، سررسید {r['DueShamsiDate']}"
             for r in this_week]
    return f"چک‌های این هفته ({len(this_week)} مورد، جمع {fmt(total_amount)} تومان):\n" + "\n".join(lines)


def _low_stock_products():
    rows = get_low_stock_products()
    if not rows:
        return "در حال حاضر هیچ کالایی به نقطه سفارش نرسیده — موجودی‌ها مناسب هستند."
    lines = [f"- {r['Name']}: موجودی {fmt(r['CurrentStock'])} (نقطه سفارش: {fmt(r['OrderPoint'])})" for r in rows]
    return f"{len(rows)} کالا به نقطه سفارش رسیده یا کمتر شده:\n" + "\n".join(lines)


def _inventory_value():
    rows, totals = rs.inventory_report()
    return (f"موجودی انبار: {totals['count']} قلم کالا، جمع تعداد {fmt(totals['total_qty'])}، "
            f"ارزش ریالی کل {fmt(totals['total_value'])} تومان. "
            f"({totals['low_stock_count']} کالا کمبوددار، {totals['zero_stock_count']} کالا بدون موجودی)")


def _purchase_today():
    rows, totals = rs.purchase_report(dr.today_str(), dr.today_str())
    return f"خرید امروز: {totals['count']} فاکتور به مبلغ {fmt(totals['payable'])} تومان."


def _purchase_this_month():
    rows, totals = rs.purchase_report(dr.month_start_str(), dr.today_str())
    return f"خرید این ماه (تا امروز): {totals['count']} فاکتور به مبلغ {fmt(totals['payable'])} تومان."


def _net_profit_this_month():
    data = rs.net_profit_loss_report(dr.month_start_str(), dr.today_str())
    return (f"سود و زیان خالص این ماه: فروش {fmt(data['revenue'])} تومان، "
            f"بهای تمام‌شده {fmt(data['cogs'])} تومان، سود ناخالص {fmt(data['gross_profit'])} تومان، "
            f"سود خالص {fmt(data['net_profit'])} تومان.")


def _sales_week_comparison():
    """فروش این هفته نسبت به هفته قبل"""
    _, this_week = rs.sales_report(dr.week_start_str(), dr.today_str())
    import jdatetime
    last_week_end = jdatetime.date.today() - jdatetime.timedelta(days=jdatetime.date.today().weekday() + 1)
    last_week_start = last_week_end - jdatetime.timedelta(days=6)
    _, last_week = rs.sales_report(last_week_start.strftime("%Y/%m/%d"), last_week_end.strftime("%Y/%m/%d"))

    this_amount = this_week["payable"]
    last_amount = last_week["payable"]
    diff = this_amount - last_amount
    percent = (diff / last_amount * 100) if last_amount else 0
    direction = "افزایش" if diff >= 0 else "کاهش"
    return (f"فروش این هفته تاکنون {fmt(this_amount)} تومان، فروش هفته قبل {fmt(last_amount)} تومان بود. "
            f"یعنی {direction} {fmt(abs(percent))} درصدی.")


def _customer_count():
    db = Database()
    row = db.fetch_one("SELECT COUNT(*) AS Cnt FROM Persons WHERE IsCustomer=1 AND IsDeleted=0")
    db.close()
    return f"در حال حاضر {row['Cnt']} مشتری در سیستم ثبت شده است."


def _product_count():
    db = Database()
    row = db.fetch_one("SELECT COUNT(*) AS Cnt FROM Products WHERE IsDeleted=0")
    db.close()
    return f"در حال حاضر {row['Cnt']} قلم کالا در سیستم تعریف شده است."


# =========================================================
# موتور تشخیص سؤال (بر اساس کلیدواژه فارسی)
# =========================================================
# هر ورودی: (لیست کلیدواژه‌هایی که همه باید در سؤال باشند, تابع پاسخ)
RULES = [
    (["فروش", "امروز"], _sales_today),
    (["فروش", "این ماه"], _sales_this_month),
    (["فروش", "ماه"], _sales_this_month),
    (["فروش", "این هفته"], _sales_this_week),
    (["فروش", "هفته", "نسبت"], _sales_week_comparison),
    (["فروش", "هفته"], _sales_this_week),

    (["سود", "امروز"], _profit_today),
    (["سود", "این ماه"], _profit_this_month),
    (["سود", "ماه"], _profit_this_month),
    (["سود و زیان"], _net_profit_this_month),
    (["سود خالص"], _net_profit_this_month),

    (["پرفروش"], _top_selling_products),

    (["بیشترین بدهی"], _top_debtor_customer),
    (["بدهکار"], _top_debtor_customer),

    (["قسط", "فردا"], _installments_tomorrow),
    (["اقساط", "فردا"], _installments_tomorrow),
    (["قسط", "امروز"], _installments_today),
    (["اقساط", "امروز"], _installments_today),
    (["قسط", "عقب"], _overdue_installments),
    (["قسط", "معوق"], _overdue_installments),
    (["قسط", "سررسیدگذشته"], _overdue_installments),

    (["چک", "هفته"], _cheques_this_week),
    (["چک", "سررسید"], _cheques_this_week),

    (["نقطه سفارش"], _low_stock_products),
    (["کمبود"], _low_stock_products),
    (["کم‌موجودی"], _low_stock_products),

    (["ارزش موجودی"], _inventory_value),
    (["موجودی انبار"], _inventory_value),

    (["خرید", "امروز"], _purchase_today),
    (["خرید", "این ماه"], _purchase_this_month),
    (["خرید", "ماه"], _purchase_this_month),

    (["تعداد مشتری"], _customer_count),
    (["چند تا مشتری"], _customer_count),
    (["تعداد کالا"], _product_count),
    (["چند تا کالا"], _product_count),
]

SUGGESTED_QUESTIONS = [
    "فروش امروز چقدر بوده؟",
    "سود این ماه چقدر است؟",
    "پرفروش‌ترین کالاهای این ماه کدام هستند؟",
    "کدام مشتری بیشترین بدهی را دارد؟",
    "اقساط فردا چقدر است؟",
    "کدام چک‌ها این هفته سررسید می‌شوند؟",
    "کدام کالاها به نقطه سفارش رسیده‌اند؟",
    "سود و زیان خالص این ماه چقدر است؟",
    "فروش این هفته نسبت به هفته قبل چقدر تغییر کرده؟",
]


def answer_question(question: str) -> str:
    """
    ورودی: سؤال فارسی کاربر
    خروجی: پاسخ متنی بر اساس داده‌های واقعی دیتابیس
    """
    if not is_assistant_enabled():
        return ("دستیار هوش مصنوعی هنوز فعال نشده. برای فعال‌سازی، به تب «تنظیمات» همین پنجره برو "
                "و دسترسی خواندنی به اطلاعات حسابداری را تأیید کن.")

    q = question.strip()
    if not q:
        return "لطفاً یک سؤال بنویس."

    q_normalized = q.replace("؟", "").replace("?", "")

    best_match = None
    best_score = 0
    for keywords, handler in RULES:
        if all(kw in q_normalized for kw in keywords):
            score = len(keywords)
            if score > best_score:
                best_score = score
                best_match = handler

    if best_match:
        try:
            return best_match()
        except Exception as e:
            return f"در محاسبه پاسخ خطایی رخ داد: {e}"

    return (
        "متوجه این سؤال نشدم. می‌توانی یکی از سؤال‌های نمونه زیر (یا مشابه آن) را بپرسی:\n\n"
        + "\n".join(f"• {sq}" for sq in SUGGESTED_QUESTIONS)
    )
