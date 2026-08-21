# ACCOUNTING_RULES.md

> ⚠️ این فایل فقط **قوانین هدف** برای آینده را ثبت می‌کند. طبق Scope
> صریح Phase 12، هیچ Accounting Engine در این فاز ساخته نشده است.

## اصل بنیادی: Double Entry
هر رویداد مالی باید یک سند حسابداری (`AccountingDocument`) با حداقل دو
ردیف (`AccountingEntries`) بسازد، به‌طوری‌که همیشه:

```
SUM(Debit) = SUM(Credit)
```

سندی که این تساوی برقرار نباشد **هرگز نباید Post شود**.

## رویدادهایی که در آینده باید سند حسابداری بسازند
- Purchase (خرید) → افزایش موجودی + بدهی به فروشنده
- Sale (فروش) → کاهش موجودی + درآمد + طلب از مشتری
- Payment (پرداخت) → کاهش صندوق/بانک + کاهش بدهی
- Receipt (دریافت) → افزایش صندوق/بانک + کاهش طلب

## وضعیت سند
هر `AccountingDocument` باید یکی از این وضعیت‌ها را داشته باشد:
`Draft` → `Posted` → (احتمالاً) `Cancelled`

اسناد مالی هرگز DELETE واقعی نمی‌شوند؛ فقط Status تغییر می‌کند.

## ارتباط با Power Failure Protection (Phase 12)
طبق `POWER_FAILURE_RECOVERY.md`، تفکیک Draft/Posted در Draft Service همین حالا
هم رعایت شده: AutoSave هرگز نباید سند حسابداری Posted بسازد؛ AutoSave فقط
داده خام فرم (پیش از تبدیل به رویداد مالی) را ذخیره می‌کند.

## این فایل چه چیزی نیست
این یک مشخصات فنی پیاده‌سازی (Implementation Spec) نیست. طراحی دقیق جداول،
Serviceها، و الگوریتم Posting باید در فاز اختصاصی Accounting Layer (پیشنهاد:
Phase 13) نوشته شود.
