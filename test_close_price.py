#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
اختبار الأمر المعلق مع السعر القريب
"""

from signal_parser import SignalParser

def test_close_price():
    parser = SignalParser()
    
    # المثال الذي أعطاه المستخدم
    message = """Gold sell limit 

Entry 4078
Sl 4093
Tp 4068
Tp 4056
Tp 4046"""
    
    print("=" * 70)
    print("🧪 اختبار: SELL LIMIT مع سعر قريب من السعر الحالي")
    print("=" * 70)
    print()
    print("📝 الرسالة:")
    print(message)
    print()
    
    signal = parser.parse(message, 'test')
    
    if not signal:
        print("❌ فشل: لم يتم التعرف على الإشارة")
        return
    
    print("✅ تم التعرف على الإشارة بنجاح!")
    print()
    print("📊 التفاصيل:")
    print(f"   الرمز: {signal.symbol}")
    print(f"   النوع: {signal.action}")
    print(f"   نوع الأمر: {signal.order_type}")
    print(f"   سعر الدخول: {signal.entry_price}")
    print(f"   أهداف الربح: {signal.take_profits}")
    print(f"   وقف الخسارة: {signal.stop_loss}")
    print()
    
    # محاكاة السعر الحالي
    current_price = 4078.32  # السعر الذي ظهر في الخطأ
    diff = abs(signal.entry_price - current_price)
    
    print("💡 تحليل السعر:")
    print(f"   سعر الدخول: {signal.entry_price}")
    print(f"   السعر الحالي (محاكاة): {current_price}")
    print(f"   الفرق: {diff:.2f} نقطة")
    print()
    
    # حساب الهامش المسموح به
    price_tolerance = max(signal.entry_price * 0.001, 0.1 * 20)  # 0.1% أو 20 نقطة
    
    print(f"🔧 الهامش المسموح به: {price_tolerance:.2f}")
    print()
    
    if signal.order_type == 'SELL_LIMIT':
        if signal.entry_price < current_price - price_tolerance:
            print("❌ خطأ: SELL LIMIT يجب أن يكون أعلى من السعر الحالي")
        else:
            print("✅ السعر مقبول - سيتم إرسال الأمر")
            if diff < price_tolerance:
                print("⚠️ ملاحظة: السعر قريب جداً، قد يتم تنفيذه فوراً")
    
    print()
    print("=" * 70)

if __name__ == "__main__":
    test_close_price()
