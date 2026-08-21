# BACKUP_POLICY.md

## اصل پایه
**Backup واقعی دیتابیس هرگز در GitHub عمومی قرار نمی‌گیرد.** GitHub فقط
کد و مستندات نگه می‌دارد؛ Backup در یک محل امن و جداگانه ذخیره می‌شود
(مثلاً یک هارد خارجی، فضای ابری خصوصی، یا سرویس Backup اختصاصی —
تصمیم نهایی بر عهده کاربر است).

## AutoSave ≠ Backup
`POWER_FAILURE_RECOVERY.md` مربوط به از‌دست‌نرفتن کار نیمه‌تمام هنگام
قطع برق است — یک لایه دفاعی کاملاً جدا و مکمل، نه جایگزین Backup واقعی.

## انواع Backup (طبق پرامپت اصلی پروژه)

| نوع | توضیح | وضعیت پیاده‌سازی |
|---|---|---|
| Manual Backup | کاربر دستی درخواست می‌دهد | موجود (`ui/backup_window.py`) |
| Scheduled Backup | به‌صورت خودکار و دوره‌ای | **PLANNED** |
| Pre-Migration Backup | قبل از هر Migration دیتابیس | **PLANNED — الزامی قبل از اجرای هر فایل در `database/migrations/`** |
| Pre-Restore Backup | قبل از هر Restore | **PLANNED** |
| On-Exit Backup | هنگام بستن برنامه | **PLANNED** |

## قانون Manifest در GitHub
اگر لازم شد اطلاعاتی درباره یک Backup در GitHub ثبت شود، فقط این موارد
مجاز است (هرگز خودِ فایل Backup):
- نسخه (Version)
- تاریخ (Date)
- Hash فایل (برای تأیید صحت)
- مرجع محل نگهداری (نه خودِ فایل)

## یادآوری از یافته امنیتی Phase 12
جزئیات کامل نقض این قانون (دو فایل Backup که وارد GitHub شدند) در
`SECURITY.md` ثبت شده است.
