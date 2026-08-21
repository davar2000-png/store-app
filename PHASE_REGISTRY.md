# PHASE_REGISTRY.md

| Phase | عنوان | وضعیت | یادداشت |
|---|---|---|---|
| 1–9 | توسعه اولیه (هسته، خرید/انبار، فروش، مالی، ارتباطات، ...) | Completed | فقط به‌صورت ZIP در `archive/` موجود است |
| 10 | تنظیمات و مدیریت کاربران/دسترسی | Completed but superseded by Phase 11 | ماژول Settings و Permission ساخته شد اما در Phase 11 حذف شد |
| 11 | لیست فاکتورها، برگشت از خرید | Completed with known Regression | Settings و Permission ماژول ۱۰ را کامل حذف کرد |
| 12 | Stabilization + GitHub Normalization + Power Failure Foundation | **Completed (Partial Scope)** | جزئیات پایین |

## Phase 12 — جزئیات

**تکمیل‌شده:**
- بازیابی Settings + User Permissions (رفع Regression Phase 11)
- انتقال Source Code واقعی به ریشه Repository (خروج از حالت ZIP-محور)
- تفکیک `schema.sql` به `schema/` (Fresh Install) و `migrations/` (امن/غیرمخرب)
- ساخت تمام فایل‌های مستندات الزامی
- ساخت زیرساخت پایه Session/Draft برای مقاومت در برابر قطع برق
- `.gitignore` + شناسایی و (تا حدی) رفع خطر Backup حساس

**تکمیل‌نشده / منتقل‌شده به فاز بعد:**
- پاکسازی کامل تاریخچه Git از فایل‌های Backup حساس (نیاز به Force Push دارد؛ کاربر فعلاً به تعویق انداخت)
- اتصال AutoSave/Draft به فرم‌های واقعی UI
- Crash Detection واقعی در `main.py` (فقط API آماده است)
- ساخت Branch جداگانه `phase/12-stabilization`
- Accounting Engine (عمداً خارج از Scope این فاز)
