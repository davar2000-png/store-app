# POWER_FAILURE_RECOVERY.md

## Risk Model
برق ممکن است بدون هشدار قطع شود؛ برنامه نباید فرض کند همیشه به‌درستی بسته می‌شود. دو نوع اطلاعات در معرض خطر است:
1. **عملیات مالی نیمه‌کاره** (مثلاً موجودی ثبت شد ولی پرداخت نه) → باید با Database Transaction کاملاً جلوگیری شود.
2. **کار نیمه‌تمام کاربر در فرم** (مثلاً فاکتور خریدی که هنوز دکمه ثبت نهایی نخورده) → باید با Draft/AutoSave قابل بازیابی باشد.

## Immediate Transaction Commit
اصل: هر عملیات مالی نهایی باید در یک `BEGIN TRANSACTION ... COMMIT` انجام شود؛ در صورت خطا `ROLLBACK` کامل. **وضعیت در Phase 12: طراحی مستند شده، اما بازبینی/تضمین این الگو در تمام Service های موجود (Purchase، Sale، Payment، ...) انجام نشده — این کار در فاز بعدی باید انجام شود.**

## AutoSave Every 60 Seconds
طبق طراحی، `DraftService.save_draft()` باید هر ۶۰ ثانیه و همچنین در رویدادهای مهم فرم (تغییر کالا/مبلغ/شخص، رفتن به فرم دیگر، از دست‌دادن Focus) فراخوانی شود.
**وضعیت: API آماده است (`services/draft_service.py`)، اما هنوز از هیچ فرم UI واقعی فراخوانی نمی‌شود.**

## Draft Recovery
`DraftService.get_active_drafts(user_id, form_type)` باید هنگام باز شدن هر فرم فراخوانی شود تا مشخص شود آیا کار نیمه‌تمام قابل بازیابی وجود دارد.
**وضعیت: API آماده، یکپارچه‌سازی با UI انجام نشده.**

## Session Heartbeat
`SessionService.heartbeat(session_id)` باید هر ۶۰ ثانیه از یک Timer در برنامه فراخوانی شود.
**وضعیت: API آماده، هنوز به `main.py` وصل نشده.**

## Unexpected Shutdown Detection
منطق: در شروع برنامه، `SessionService.find_crashed_sessions(user_id)` باید فراخوانی شود. اگر Session فعالی (`CloseStatus = 'ACTIVE'`) از اجرای قبلی پیدا شود که هرگز `CLEAN` نشده، یعنی برنامه به‌درستی بسته نشده (قطع برق یا Crash).
**وضعیت: منطق نوشته شده، اما فراخوانی آن در `main.py` هنگام شروع برنامه هنوز اضافه نشده.**

## Duplicate Prevention
هر Draft و هر Session یک `GUID` یکتا دارد (`DraftGuid`, `SessionGuid`). طراحی هدف: قبل از ثبت نهایی هر عملیات مالی، بررسی شود که آیا عملیاتی با همان Correlation ID/Document ID قبلاً Posted شده یا نه، تا از ثبت دوباره جلوگیری شود.
**وضعیت: طراحی مستند شده در `ACCOUNTING_RULES.md`؛ پیاده‌سازی واقعی هنوز نشده چون به لایه حسابداری (که هنوز ساخته نشده) وابسته است.**

## Recovery Workflow (طراحی هدف)
1. بررسی اتصال دیتابیس
2. بررسی آخرین Session کاربر (`find_crashed_sessions`)
3. پیدا کردن Draft های فعال (`get_active_drafts`)
4. اطلاع‌رسانی به کاربر («یک کار نیمه‌تمام از دفعه قبل پیدا شد»)
5. ارائه گزینه Recover / Discard
6. هرگز عملیات مالی Posted را دوباره ثبت نکند

## Testing Strategy
یک سناریوی تست دستی طراحی شد (باز کردن فرم خرید → پر کردن اطلاعات → بستن غیرعادی برنامه → اجرای مجدد → بررسی Recovery)، اما:

**⚠️ NOT FULLY TESTED.** این محیط توسعه (sandbox) به یک نمونه SQL Server یا محیط دسکتاپ واقعی کاربر دسترسی ندارد، پس این سناریو عملاً اجرا نشده — فقط تا سطح Import/Syntax صحیح بودن کد بررسی شد (`tests/test_smoke.py`). اجرای واقعی این تست بر عهده فاز بعدی (یا خود کاربر) است.

## Known Limitations
- AutoSave/Recovery هنوز به هیچ فرم UI وصل نیست — این فقط زیرساخت پایه (Foundation) است
- Transaction Wrapping در Service های موجود (Purchase/Sale/...) بازبینی نشده
- تست واقعی روی سناریوی قطع برق انجام نشده
