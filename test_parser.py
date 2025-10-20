"""
اختبار محلل الإشارات على جميع الأنماط المقدمة
"""

import sys
import io

# إصلاح ترميز Unicode في Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from signal_parser import SignalParser

def test_all_patterns():
    parser = SignalParser()

    test_messages = [
        {
            'name': 'نمط 1: BTCUSD شراء',
            'message': """BTCUSD buy NOW 117200

TP 117500
TP 117700
TP 117900

SL 116700"""
        },
        {
            'name': 'نمط 2: GOLD بيع مع نطاق',
            'message': """GOLD sell NOW 3343   - 45

TP 3340
TP 3337
TP 3333

SL 3351"""
        },
        {
            'name': 'نمط 3: GBPJPY بيع',
            'message': """GBPJPY Sell NOW 200.000

TP 199.800
TP 199.600
TP 199.400

SL 200.500"""
        },
        {
            'name': 'نمط 4: GOLD مع رموز تعبيرية',
            'message': """🕯 GOLD SEL NOW 3335📈

🌟Take Profit       3320

☄️Stop Lose        3345

⚠️Use Lots According To
Your Account Equity Balance"""
        },
        {
            'name': 'نمط 5: XAUUSD بيع متعدد TP',
            'message': """XAUUSD SELL 3344
TP 3342
TP 3340
TP 3338
TP 3335
SL 3354"""
        },
        {
            'name': 'نمط 6: GBPJPY مع أرقام TP',
            'message': """GBPJPY SELL 199.400

TP¹ 199.100
TP² 198.800
TP³ 198.500

SL  199.900"""
        },
        {
            'name': 'نمط 7: EURJPY مع مسافات',
            'message': """EURJPY SELL 172  100

TP¹ 171.800
TP² 171.500
TP³ 171.200

SL  172.600"""
        },
        {
            'name': 'نمط 8: XAUUSD_GOLD مع رموز',
            'message': """🔵XAUUSD_GOLD BUY 3331


🔳TP : 3335.00
🔳TP : 3338.00
🔳TP : 3343.00

❌SL : 3321.000"""
        },
        {
            'name': 'نمط 9: GBPUSD بيع',
            'message': """🔵GBPUSD SELL  1.35600


🔳TP : 1.35300
🔳TP : 1.35000
🔳TP : 1.34800

❌SL : 1.36100✅️✅️✅️"""
        },
        {
            'name': 'نمط 10: XAUUSD مع 4 مستويات TP',
            'message': """XAUUSD BUY 3330

TP¹.  3333
TP².  3336
TP³.  3339
TP⁴.  3342

SL.   3310"""
        },
        {
            'name': 'نمط 11: XAUUSD مبسط',
            'message': """XAUUSD BUY 3330

TP 3334
TP 3338
TP 3343
TP 3346
SL 3317"""
        },
        {
            'name': 'نمط 12: #XAUUSD مع هاشتاج',
            'message': """#𝗫𝗔𝗨𝗨𝗦𝗗 SELL 3349
TP 3346
TP 3343
TP 3340

SL 3355"""
        },
        {
            'name': 'نمط 13: Xauusd حروف صغيرة',
            'message': """Xauusd Buy 3350

TP 3355
TP 3360

SL 3340"""
        },
        {
            'name': 'نمط 14: XAUUSD مع نطاق دخول',
            'message': """XAUUSD BUY NOW
Price Open @ 3333- 3330

Take profit 1 🔼@ 3337
Take profit 2 🔼@ 3342
Take profit 3 🔼@ 3350

➕Stop loss @ 3325
Use Small lots size 🔥🔥🔥
KEEP STRONG HOLD 💯💯💯✔️"""
        },
        {
            'name': 'نمط 15: XAUUSD بيع مع 5 مستويات',
            'message': """XAUUSD SELL 3352
TP.       3348
TP.       3344
TP.       3340
TP.       3336
SL.      3365"""
        },
        {
            'name': 'نمط 16: XAUUAD (خطأ إملائي) مع 6 مستويات',
            'message': """XAUUAD SELL 3333

TP1 3330
TP2 3327
TP3 3324
TP4 3321
TP5 3317
TP6 3315

SL. 3347"""
        },
        {
            'name': 'نمط 17: GBPJPY بيع مع SL خاطئ',
            'message': """GBPJPY SELL 199.200

TP 199.100
TP 199.000
TP 198.900
TP 198.800
TP 198.700

SL 198.700"""
        },
        {
            'name': 'نمط 18: XAUUSD_GOLD مع رموز سعيدة',
            'message': """😄XAUUSD_GOLD BUY 3338

😄TP : 3342
😄TP : 3345
😄TP : 3348
😄TP : 3351
😄TP : 3354

👎SL : 3328"""
        }
    ]

    print("=" * 80)
    print("اختبار محلل الإشارات - جميع الأنماط")
    print("=" * 80)
    print()

    passed = 0
    failed = 0

    for i, test in enumerate(test_messages, 1):
        print(f"\n{'='*80}")
        print(f"اختبار {i}: {test['name']}")
        print(f"{'='*80}")
        print("\nالرسالة الأصلية:")
        print("-" * 80)
        print(test['message'])
        print("-" * 80)

        signal = parser.parse(test['message'], f"TestChannel{i}")

        if signal:
            print("\n✅ تم التحليل بنجاح!")
            print(f"\n📊 تفاصيل الإشارة:")
            print(f"   الرمز: {signal.symbol}")
            print(f"   النوع: {signal.action}")

            if signal.entry_price:
                print(f"   سعر الدخول: {signal.entry_price}")
            elif signal.entry_price_range:
                print(f"   نطاق الدخول: {signal.entry_price_range[0]} - {signal.entry_price_range[1]}")

            print(f"   مستويات أخذ الربح ({len(signal.take_profits)}):")
            for j, tp in enumerate(signal.take_profits, 1):
                print(f"      TP{j}: {tp}")

            print(f"   وقف الخسارة: {signal.stop_loss}")

            # التحقق من المنطقية
            ref_price = signal.entry_price if signal.entry_price else sum(signal.entry_price_range) / 2

            if signal.action == 'BUY':
                tps_valid = all(tp > ref_price for tp in signal.take_profits)
                sl_valid = signal.stop_loss < ref_price
            else:
                tps_valid = all(tp < ref_price for tp in signal.take_profits)
                sl_valid = signal.stop_loss > ref_price

            if tps_valid and sl_valid:
                print("\n   ✅ البيانات منطقية وصحيحة")
                passed += 1
            else:
                print("\n   ⚠️ تحذير: البيانات قد لا تكون منطقية")
                if not tps_valid:
                    print("      - مستويات TP غير صحيحة بالنسبة لسعر الدخول")
                if not sl_valid:
                    print("      - SL غير صحيح بالنسبة لسعر الدخول")
                failed += 1
        else:
            print("\n❌ فشل التحليل")
            print("   السبب: لم يتم التعرف على الإشارة أو البيانات غير كاملة")
            failed += 1

    print("\n" + "=" * 80)
    print("ملخص النتائج")
    print("=" * 80)
    print(f"✅ نجح: {passed}/{len(test_messages)}")
    print(f"❌ فشل: {failed}/{len(test_messages)}")
    print(f"📊 نسبة النجاح: {(passed/len(test_messages)*100):.1f}%")
    print("=" * 80)

if __name__ == "__main__":
    test_all_patterns()
