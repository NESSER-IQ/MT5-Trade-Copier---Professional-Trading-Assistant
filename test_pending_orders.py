#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
اختبار الأوامر المعلقة
"""

from signal_parser import SignalParser

def test_pending_orders():
    parser = SignalParser()
    
    tests = [
        {
            'name': 'SELL LIMIT (المثال الأصلي)',
            'message': '''Gold sell limit

Entry 4078
Sl 4093
Tp 4068
Tp 4056
Tp 4046''',
            'expected_type': 'SELL_LIMIT',
            'expected_action': 'SELL'
        },
        {
            'name': 'BUY LIMIT',
            'message': '''XAUUSD buy limit 4072
TP 4077
TP 4082
SL 4065''',
            'expected_type': 'BUY_LIMIT',
            'expected_action': 'BUY'
        },
        {
            'name': 'SELL STOP',
            'message': '''Gold sell stop

Entry 4070
SL 4080
TP 4060
TP 4055''',
            'expected_type': 'SELL_STOP',
            'expected_action': 'SELL'
        },
        {
            'name': 'BUY STOP',
            'message': '''XAUUSD buy stop

Entry 4080
SL 4072
TP 4085
TP 4090''',
            'expected_type': 'BUY_STOP',
            'expected_action': 'BUY'
        },
        {
            'name': 'MARKET BUY (عادي)',
            'message': '''Gold buy 4072
TP 4077
TP 4082
SL 4065''',
            'expected_type': 'MARKET',
            'expected_action': 'BUY'
        },
        {
            'name': 'MARKET SELL (عادي)',
            'message': '''XAUUSD sell 4078
TP 4073
TP 4068
SL 4083''',
            'expected_type': 'MARKET',
            'expected_action': 'SELL'
        }
    ]
    
    print("=" * 70)
    print("🧪 اختبار الأوامر المعلقة (Pending Orders)")
    print("=" * 70)
    print()
    
    passed = 0
    failed = 0
    
    for test in tests:
        print(f"📝 اختبار: {test['name']}")
        signal = parser.parse(test['message'], 'test')
        
        if not signal:
            print(f"   ❌ فشل: لم يتم التعرف على الإشارة")
            failed += 1
            print()
            continue
        
        # التحقق من نوع الأمر
        if signal.order_type != test['expected_type']:
            print(f"   ❌ فشل: نوع الأمر خاطئ")
            print(f"      المتوقع: {test['expected_type']}")
            print(f"      الفعلي: {signal.order_type}")
            failed += 1
        elif signal.action != test['expected_action']:
            print(f"   ❌ فشل: نوع الصفقة خاطئ")
            print(f"      المتوقع: {test['expected_action']}")
            print(f"      الفعلي: {signal.action}")
            failed += 1
        else:
            print(f"   ✅ نجح")
            print(f"      الرمز: {signal.symbol}")
            print(f"      النوع: {signal.action} - {signal.order_type}")
            print(f"      الدخول: {signal.entry_price}")
            print(f"      TPs: {signal.take_profits}")
            print(f"      SL: {signal.stop_loss}")
            passed += 1
        
        print()
    
    print("=" * 70)
    print(f"📊 النتائج: ✅ نجح {passed} | ❌ فشل {failed} | 📝 المجموع {len(tests)}")
    print("=" * 70)
    
    if failed == 0:
        print("🎉 تهانينا! جميع الاختبارات نجحت!")
    else:
        print(f"⚠️ هناك {failed} اختبار(ات) فاشلة تحتاج إلى إصلاح")

if __name__ == "__main__":
    test_pending_orders()
