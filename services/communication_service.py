# -*- coding: utf-8 -*-
"""
لایه منطق تجاری «ارتباط با مشتری» (پیامک و پیام‌رسان بله).
اتصال واقعی به سرویس‌های پیامکی ایرانی (کاوه‌نگار، ملی‌پیامک) و ربات بله
از طریق API انجام می‌شود. تنظیمات (کلید API، شماره خط، توکن) در جدول Settings
ذخیره می‌شود تا کاربر بدون تغییر کد بتواند سرویس خودش را وارد کند.
"""

import sys
import os
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import Database
from utils.persian_date import today_shamsi_str


class CommunicationError(Exception):
    pass


# =========================================================
# تنظیمات (خواندن/نوشتن از جدول Settings)
# =========================================================
def get_setting(key: str, default: str = "") -> str:
    db = Database()
    row = db.fetch_one("SELECT SettingValue FROM Settings WHERE SettingKey = ?", (key,))
    db.close()
    return row["SettingValue"] if row and row["SettingValue"] is not None else default


def set_setting(key: str, value: str):
    db = Database()
    existing = db.fetch_one("SELECT ID FROM Settings WHERE SettingKey = ?", (key,))
    if existing:
        db.execute("UPDATE Settings SET SettingValue = ? WHERE SettingKey = ?", (value, key))
    else:
        db.execute("INSERT INTO Settings (SettingKey, SettingValue) VALUES (?, ?)", (key, value))
    db.close()


def get_communication_settings() -> dict:
    keys = ["SmsProvider", "SmsApiKey", "SmsUsername", "SmsSenderNumber",
            "SmsCustomUrlTemplate", "BalehBotToken", "StoreName"]
    return {k: get_setting(k) for k in keys}


def save_communication_settings(data: dict):
    for key, value in data.items():
        set_setting(key, value)


# =========================================================
# ارسال پیامک — بر اساس سرویس انتخاب‌شده در تنظیمات
# =========================================================
def send_sms(phone: str, text: str) -> tuple:
    """
    ارسال پیامک با سرویس تنظیم‌شده.
    خروجی: (success: bool, error_message: str|None)
    """
    provider = get_setting("SmsProvider", "Kavenegar")
    phone = (phone or "").strip()
    if not phone:
        return False, "شماره موبایل خالی است."

    try:
        if provider == "Kavenegar":
            api_key = get_setting("SmsApiKey")
            sender = get_setting("SmsSenderNumber")
            if not api_key:
                return False, "کلید API کاوه‌نگار در تنظیمات وارد نشده."
            url = f"https://api.kavenegar.com/v1/{api_key}/sms/send.json"
            params = {"receptor": phone, "message": text}
            if sender:
                params["sender"] = sender
            resp = requests.get(url, params=params, timeout=15)
            data = resp.json()
            if resp.status_code == 200 and data.get("return", {}).get("status") == 200:
                return True, None
            return False, str(data.get("return", {}).get("message", resp.text))

        elif provider == "Melipayamak":
            username = get_setting("SmsUsername")
            password = get_setting("SmsApiKey")  # از همان فیلد به‌عنوان رمز عبور استفاده می‌شود
            sender = get_setting("SmsSenderNumber")
            if not username or not password or not sender:
                return False, "نام کاربری، رمز عبور یا شماره خط ملی‌پیامک وارد نشده."
            url = "https://rest.payamak-panel.com/api/SendSMS/SendSMS"
            payload = {
                "username": username, "password": password,
                "to": phone, "from": sender, "text": text, "isflash": False
            }
            resp = requests.post(url, json=payload, timeout=15)
            data = resp.json()
            if data.get("RetStatus") == 1:
                return True, None
            return False, str(data.get("StrRetStatus", resp.text))

        elif provider == "Custom":
            url_template = get_setting("SmsCustomUrlTemplate")
            if not url_template:
                return False, "آدرس API سفارشی در تنظیمات وارد نشده."
            url = url_template.replace("{phone}", phone).replace("{text}", requests.utils.quote(text))
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                return True, None
            return False, f"کد پاسخ سرور: {resp.status_code}"

        else:
            return False, f"سرویس پیامکی ناشناخته: {provider}"

    except requests.exceptions.RequestException as e:
        return False, f"خطای اتصال به سرویس پیامک: {e}"
    except Exception as e:
        return False, f"خطای غیرمنتظره: {e}"


# =========================================================
# ارسال پیام از طریق ربات بله
# =========================================================
def send_baleh(chat_id: str, text: str) -> tuple:
    """ارسال پیام متنی از طریق ربات بله. خروجی: (success, error_message)"""
    token = get_setting("BalehBotToken")
    chat_id = (chat_id or "").strip()

    if not token:
        return False, "توکن ربات بله در تنظیمات وارد نشده."
    if not chat_id:
        return False, "شناسه چت بله (Chat ID) این شخص ثبت نشده."

    try:
        url = f"https://tapi.bale.ai/bot{token}/sendMessage"
        resp = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=15)
        data = resp.json()
        if data.get("ok"):
            return True, None
        return False, str(data.get("description", resp.text))
    except requests.exceptions.RequestException as e:
        return False, f"خطای اتصال به بله: {e}"
    except Exception as e:
        return False, f"خطای غیرمنتظره: {e}"


# =========================================================
# قالب‌های پیام
# =========================================================
def get_templates():
    db = Database()
    rows = db.fetch_all("SELECT * FROM MessageTemplates ORDER BY ID")
    db.close()
    return rows


def save_template(template_id: int, title: str, content: str):
    db = Database()
    db.execute(
        "UPDATE MessageTemplates SET Title = ?, Content = ? WHERE ID = ?",
        (title, content, template_id)
    )
    db.close()


def render_template(content: str, context: dict) -> str:
    """جایگزینی پارامترهای {نام}، {مبلغ} و ... با مقدار واقعی"""
    text = content
    for key, value in context.items():
        text = text.replace("{" + key + "}", str(value))
    return text


def build_context(person: dict, amount=None, date=None, invoice_number=None) -> dict:
    store_name = get_setting("StoreName", "فروشگاه")
    ctx = {
        "نام": person.get("FullName", ""),
        "نام_فروشگاه": store_name,
    }
    if amount is not None:
        ctx["مبلغ"] = f"{float(amount):,.0f}"
    if date is not None:
        ctx["تاریخ"] = date
    if invoice_number is not None:
        ctx["شماره_فاکتور"] = str(invoice_number)
    return ctx


# =========================================================
# ارسال پیام به یک شخص + ثبت در تاریخچه
# =========================================================
def send_message_to_person(person_id: int, channel: str, text: str,
                            template_key: str = None, user_id: int = None) -> tuple:
    """
    channel: 'SMS' یا 'Baleh'
    خروجی: (success, error_message)
    """
    db = Database()
    person = db.fetch_one("SELECT * FROM Persons WHERE ID = ?", (person_id,))
    db.close()

    if not person:
        return False, "شخص یافت نشد."

    if channel == "SMS":
        success, error = send_sms(person.get("Mobile"), text)
    elif channel == "Baleh":
        success, error = send_baleh(person.get("BalehChatId"), text)
    else:
        return False, f"کانال ناشناخته: {channel}"

    db = Database()
    db.execute(
        """INSERT INTO MessageLog
           (PersonRef, Channel, TemplateKey, MessageText, Status, ErrorText, ShamsiDate, UserRef)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (person_id, channel, template_key, text,
         "Sent" if success else "Failed", error, today_shamsi_str(), user_id)
    )
    db.close()

    return success, error


def get_message_log(search: str = ""):
    db = Database()
    like = f"%{search.strip()}%"
    rows = db.fetch_all(
        """SELECT ml.ID, p.FullName AS PersonName, ml.Channel, ml.MessageText,
                  ml.Status, ml.ErrorText, ml.ShamsiDate
           FROM MessageLog ml
           LEFT JOIN Persons p ON p.ID = ml.PersonRef
           WHERE (p.FullName LIKE ? OR ml.MessageText LIKE ?)
           ORDER BY ml.ID DESC""",
        (like, like)
    )
    db.close()
    return rows


# =========================================================
# یادآوری دسته‌جمعی اقساط (نزدیک سررسید و سررسیدشده)
# =========================================================
def send_bulk_installment_reminders(channel: str = "SMS", user_id: int = None) -> dict:
    """
    برای همه اقساط پرداخت‌نشده (Pending) یک پیام یادآوری/سررسید می‌فرستد.
    خروجی: {'sent': N, 'failed': N, 'details': [...]}
    """
    db = Database()
    today = today_shamsi_str()
    rows = db.fetch_all(
        """SELECT ii.ID, ii.DueShamsiDate, ii.Amount, p.ID AS PersonID, p.FullName, p.Mobile, p.BalehChatId
           FROM InstallmentItems ii
           JOIN InstallmentPlans ip ON ip.ID = ii.PlanRef
           JOIN Persons p ON p.ID = ip.PersonRef
           WHERE ii.Status = N'Pending' AND ip.IsDeleted = 0"""
    )
    templates = {t["TemplateKey"]: t["Content"] for t in get_templates()}
    db.close()

    sent, failed, details = 0, 0, []

    for r in rows:
        is_overdue = r["DueShamsiDate"] < today
        template_key = "InstallmentOverdue" if is_overdue else "InstallmentReminder"
        content = templates.get(template_key, "")
        person = {"FullName": r["FullName"], "BalehChatId": r["BalehChatId"], "Mobile": r["Mobile"], "ID": r["PersonID"]}
        ctx = build_context(person, amount=r["Amount"], date=r["DueShamsiDate"])
        text = render_template(content, ctx)

        success, error = send_message_to_person(r["PersonID"], channel, text, template_key, user_id)
        if success:
            sent += 1
        else:
            failed += 1
        details.append({"name": r["FullName"], "success": success, "error": error})

    return {"sent": sent, "failed": failed, "details": details}
