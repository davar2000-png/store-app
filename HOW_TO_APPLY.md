# Phase 16C — نحوه‌ی اعمال و Push

این فاز روی برنچ `phase/16c-auth-extraction` (بر پایه‌ی دقیق سرِ فعلی
`phase/14-workflow-audit`، یعنی commit `2ece6da`) به‌صورت یک commit
محلی (`ea3ba0a`) آماده شده. من به این ریپو دسترسی Push ندارم، پس یکی از
دو روش زیر را روی نسخه‌ی محلی خودتان اجرا کنید.

## روش ۱ — git bundle (ساده‌تر و ایمن‌تر)

```bash
git fetch origin
git checkout phase/14-workflow-audit
git pull origin phase/14-workflow-audit   # مطمئن شوید دقیقاً روی 2ece6da هستید

git checkout -b phase/16c-auth-extraction
git pull phase-16c-auth-extraction.bundle phase/16c-auth-extraction

# اجرای تست‌ها قبل از Push
pip install -r requirements.txt -r requirements-web.txt --break-system-packages
python -m pytest tests/ -q     # باید 244 passed بدهد

git push origin phase/16c-auth-extraction
```

## روش ۲ — git am (patch file)

```bash
git fetch origin
git checkout phase/14-workflow-audit
git pull origin phase/14-workflow-audit

git checkout -b phase/16c-auth-extraction
git am phase-16c-auth-extraction-ea3ba0a.patch

python -m pytest tests/ -q     # باید 244 passed بدهد

git push origin phase/16c-auth-extraction
```

## نکته‌ی مهم درباره‌ی دیتابیس

قبل از تست کردن Login وب روی دیتابیس واقعی، باید Migration جدید را روی
SQL Server خودتان اجرا کنید:

```
database/migrations/015_web_sessions.sql
```

این فقط یک جدول جدید (`WebSessions`) می‌سازد و به هیچ جدول موجودی
(`Users`, `Sessions`, ...) دست نمی‌زند. تا قبل از اجرای این Migration،
`POST /login` با خطای اتصال به جدول مواجه می‌شود (به‌صورت صادقانه گزارش
می‌شود، نه Fail خاموش).

## اجرای وب برای تست دستی

```bash
python -m uvicorn web.app:app --host 127.0.0.1 --port 8000
```

سپس در Chrome به `http://127.0.0.1:8000/` بروید — باید به `/login`
Redirect شوید. من خودم فقط با HTTP (curl/TestClient) تست کردم؛ تأیید
واقعی با مرورگر و SQL Server واقعی هنوز انجام نشده (طبق `AI_HANDOFF.md`).

## Merge به main

طبق تصمیم‌های قبلی پروژه، Merge هیچ‌کدام از `phase/14-workflow-audit` یا
`phase/16c-auth-extraction` به `main` توسط من انجام نشد — این تصمیم با
شماست.
