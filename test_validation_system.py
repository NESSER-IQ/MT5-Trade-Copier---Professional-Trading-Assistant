#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
اختبار نظام التحقق التلقائي من شروط التداول
"""

from mt5_manager import MT5Manager
from signal_parser import Signal

def test_validation_system():
    """اختبار شامل لنظام التحقق"""
    
    print("=" * 70)
    print("🧪 اختبار نظام التحقق التلقائي من شروط التداول")
    print("=" * 70)
    print()
    
    # إنشاء MT5Manager
    manager = MT5Manager()
    
    # الاتصال
    print("📡 محاولة الاتصال بـ MT5...")
    if manager.auto_connect():
        print("✅ تم الاتصال بنجاح!")
        print()
    else:
        print("❌ فشل الاتصال - يجب أن يكون MT5 مفتوحاً")
        return
    
    # الاختبارات
    tests = [
        {
            'name': 'اختبار 1: صفقة صحيحة 100%',
            'signal': Signal(
                symbol='XAUUSD',
                action='BUY',
                entry_price=4070.0,
                take_profits=[4080.0],
                stop_loss=4060.0,
                order_type='MARKET'
            ),
            'lot_size': 0.01,
            'expected': 'valid'
        },
        {
            'name': 'اختبار 2: SL قريب جداً من Entry',
            'signal': Signal(
                symbol='XAUUSD',
                action='BUY',
                entry_price=4070.0,
                take_profits=[4075.0],
                stop_loss=4069.9,  # قريب جداً (0.1 نقطة)
                order_type='MARKET'
            ),
            'lot_size': 0.01,
            'expected': 'invalid'
        },
        {
            'name': 'اختبار 3: حجم صفقة أقل من المسموح',
            'signal': Signal(
                symbol='XAUUSD',
                action='BUY',
                entry_price=4070.0,
                take_profits=[4080.0],
                stop_loss=4060.0,
                order_type='MARKET'
            ),
            'lot_size': 0.001,  # أقل من الحد الأدنى
            'expected': 'invalid'
        },
        {
            'name': 'اختبار 4: SL في اتجاه خاطئ (BUY)',
            'signal': Signal(
                symbol='XAUUSD',
                action='BUY',
                entry_price=4070.0,
                take_profits=[4080.0],
                stop_loss=4075.0,  # أعلى من Entry!
                order_type='MARKET'
            ),
            'lot_size': 0.01,
            'expected': 'invalid'
        },
        {
            'name': 'اختبار 5: رمز غير موجود',
            'signal': Signal(
                symbol='XXXYYY',
                action='BUY',
                entry_price=1.0,
                take_profits=[1.1],
                stop_loss=0.9,
                order_type='MARKET'
            ),
            'lot_size': 0.01,
            'expected': 'invalid'
        },
    ]
    
    # تشغيل الاختبارات
    passed = 0
    failed = 0
    
    for test in tests:
        print("\n" + "=" * 70)
        print(f"📝 {test['name']}")
        print("=" * 70)
        
        validation = manager.validate_trade_conditions(
            symbol=test['signal'].symbol,
            action=test['signal'].action,
            lot_size=test['lot_size'],
            entry_price=test['signal'].entry_price,
            stop_loss=test['signal'].stop_loss,
            take_profit=test['signal'].take_profits[0] if test['signal'].take_profits else None,
            order_type=test['signal'].order_type
        )
        
        is_valid = validation['valid']
        expected_valid = (test['expected'] == 'valid')
        
        if is_valid == expected_valid:
            print(f"\n✅ الاختبار نجح!")
            print(f"   النتيجة المتوقعة: {test['expected']}")
            print(f"   النتيجة الفعلية: {'valid' if is_valid else 'invalid'}")
            passed += 1
        else:
            print(f"\n❌ الاختبار فشل!")
            print(f"   النتيجة المتوقعة: {test['expected']}")
            print(f"   النتيجة الفعلية: {'valid' if is_valid else 'invalid'}")
            failed += 1
        
        # عرض التفاصيل
        if validation['errors']:
            print(f"\n🔍 الأخطاء المكتشفة:")
            for error in validation['errors']:
                print(f"   {error}")
        
        if validation['warnings']:
            print(f"\n⚠️ التحذيرات:")
            for warning in validation['warnings']:
                print(f"   {warning}")
    
    # النتيجة النهائية
    print("\n" + "=" * 70)
    print(f"📊 النتائج النهائية:")
    print(f"   ✅ نجح: {passed}/{len(tests)}")
    print(f"   ❌ فشل: {failed}/{len(tests)}")
    print("=" * 70)
    
    if failed == 0:
        print("\n🎉 ممتاز! جميع الاختبارات نجحت!")
    else:
        print(f"\n⚠️ هناك {failed} اختبار(ات) فاشلة")
    
    # قطع الاتصال
    manager.disconnect()

def test_validation_details():
    """اختبار تفصيلي لرمز واحد"""
    
    print("\n" + "=" * 70)
    print("🔍 اختبار تفصيلي: فحص خصائص XAUUSD")
    print("=" * 70)
    
    manager = MT5Manager()
    
    if not manager.auto_connect():
        print("❌ فشل الاتصال")
        return
    
    # الحصول على خصائص الرمز
    props = manager.get_symbol_properties("XAUUSD", verbose=True)
    
    if props:
        print("\n✅ يمكن استخدام هذه المعلومات للتحقق:")
        print(f"   • التداول مسموح: {props['trade_allowed']}")
        print(f"   • التداول عبر الخبراء: {props['trade_expert']}")
        print(f"   • الحد الأدنى للصفقة: {props['volume_min']}")
        print(f"   • الحد الأقصى للصفقة: {props['volume_max']}")
        print(f"   • Stop Level: {props['trade_stops_level']} نقطة")
        print(f"   • Spread الحالي: {props['spread']} نقطة")
    
    manager.disconnect()

if __name__ == "__main__":
    # تشغيل الاختبار الشامل
    test_validation_system()
    
    # تشغيل الاختبار التفصيلي
    test_validation_details()
