"""
اختبار النمط الجديد المطلوب من المستخدم
"""

from signal_parser import SignalParser

def test_user_pattern():
    """اختبار النمط المطلوب من المستخدم"""

    parser = SignalParser()

    # النمط المطلوب
    test_message = """XAUUSD SELL 4290_4295

TP¹.  4287
TP².  4284
TP³.  4281
TP⁴.  4278


SL.   4317"""

    print("=" * 60)
    print("اختبار النمط المطلوب")
    print("=" * 60)
    print("\nالرسالة الأصلية:")
    print(test_message)
    print("\n" + "=" * 60)

    # تحليل الإشارة
    signal = parser.parse(test_message, "Test Channel")

    if signal:
        print("\n✅ نجح! تم تحليل الإشارة بنجاح:")
        print(f"\n📊 التفاصيل:")
        print(f"   الرمز: {signal.symbol}")
        print(f"   الاتجاه: {signal.action}")
        print(f"   سعر الدخول: {signal.entry_price}")
        print(f"   نطاق الدخول: {signal.entry_price_range}")
        print(f"   أهداف الربح (TP): {signal.take_profits}")
        print(f"   وقف الخسارة (SL): {signal.stop_loss}")
        print(f"\n✅ النمط مدعوم بالكامل!")

        # التحقق من صحة البيانات
        if signal.entry_price_range:
            avg_entry = sum(signal.entry_price_range) / 2
            print(f"\n📈 متوسط سعر الدخول: {avg_entry}")

        print(f"\n🎯 التحقق من منطقية الأسعار:")
        if signal.action == "SELL":
            reference = signal.entry_price if signal.entry_price else sum(signal.entry_price_range) / 2
            print(f"   - سعر الدخول المرجعي: {reference}")
            print(f"   - أعلى TP: {max(signal.take_profits)}")
            print(f"   - أقل TP: {min(signal.take_profits)}")
            print(f"   - SL: {signal.stop_loss}")

            if all(tp < reference for tp in signal.take_profits):
                print("   ✅ أهداف الربح صحيحة (أقل من سعر الدخول)")
            else:
                print("   ❌ أهداف الربح خاطئة!")

            if signal.stop_loss > reference:
                print("   ✅ وقف الخسارة صحيح (أعلى من سعر الدخول)")
            else:
                print("   ❌ وقف الخسارة خاطئ!")
    else:
        print("\n❌ فشل! لم يتم التعرف على الإشارة")
        print("\n🔍 الأسباب المحتملة:")
        print("   - الأسعار غير منطقية")
        print("   - ناقص بيانات أساسية")
        print("   - خطأ في التنسيق")


if __name__ == "__main__":
    import sys
    import io
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    test_user_pattern()
