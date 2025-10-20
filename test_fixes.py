"""
اختبار الإصلاحات الجديدة
"""

from signal_parser import SignalParser
from daily_report_manager import DailyReportManager
import json


def test_signal_parser_fixes():
    """اختبار إصلاحات محلل الإشارات"""
    print("=" * 60)
    print("🧪 اختبار محلل الإشارات المحسّن")
    print("=" * 60)

    parser = SignalParser()

    # اختبار 1: رسالة مع "100% Sure Signal"
    print("\n📝 اختبار 1: رسالة تحتوي على نسبة مئوية")
    test_message_1 = """XAUUSD SELL NOW @ 4289.70

       Tp1: 4285.00
       Tp2: 4280.00
       Tp3: 4275.00 100% Sure Signal

   ❌ SL. TP ::: 4299.00"""

    signal_1 = parser.parse(test_message_1, "Test Channel")

    if signal_1:
        print(f"✅ تم تحليل الإشارة:")
        print(f"   الرمز: {signal_1.symbol}")
        print(f"   الاتجاه: {signal_1.action}")
        print(f"   الدخول: {signal_1.entry_price}")
        print(f"   TP: {signal_1.take_profits}")
        print(f"   SL: {signal_1.stop_loss}")

        # التحقق من عدم وجود "100" في TP
        if 100.0 in signal_1.take_profits:
            print("   ❌ فشل: لا يزال يلتقط '100' من النسبة المئوية!")
        else:
            print("   ✅ نجح: لم يلتقط النسبة المئوية")

        # التحقق من SL صحيح
        if signal_1.stop_loss == 4299.0:
            print("   ✅ نجح: SL صحيح (4299.0)")
        else:
            print(f"   ❌ فشل: SL خاطئ ({signal_1.stop_loss})")
    else:
        print("❌ فشل التحليل - الإشارة مرفوضة")

    # اختبار 2: إشارة بدون TP
    print("\n📝 اختبار 2: إشارة بدون TP (يجب رفضها)")
    test_message_2 = """GOLD BUY NOW 2050
SL 2045"""

    signal_2 = parser.parse(test_message_2, "Test Channel")

    if signal_2:
        print("   ❌ فشل: قبل إشارة بدون TP!")
    else:
        print("   ✅ نجح: رفض الإشارة بدون TP")

    # اختبار 3: إشارة بدون SL
    print("\n📝 اختبار 3: إشارة بدون SL (يجب رفضها)")
    test_message_3 = """XAUUSD BUY 2050
TP 2055
TP 2060"""

    signal_3 = parser.parse(test_message_3, "Test Channel")

    if signal_3:
        print("   ❌ فشل: قبل إشارة بدون SL!")
    else:
        print("   ✅ نجح: رفض الإشارة بدون SL")

    # اختبار 4: إشارة بأسعار غير منطقية
    print("\n📝 اختبار 4: إشارة بأسعار غير منطقية (يجب رفضها)")
    test_message_4 = """XAUUSD SELL 4289
TP 4295
TP 4300
SL 4280"""  # خطأ: في البيع TP يجب أن يكون أقل من الدخول

    signal_4 = parser.parse(test_message_4, "Test Channel")

    if signal_4:
        print("   ❌ فشل: قبل إشارة بأسعار غير منطقية!")
    else:
        print("   ✅ نجح: رفض الإشارة بأسعار غير منطقية")

    # اختبار 5: إشارة صحيحة تماماً
    print("\n📝 اختبار 5: إشارة صحيحة (يجب قبولها)")
    test_message_5 = """GOLD BUY 4218/4215

TP 4222
TP 4226
TP 4230
TP 4233

SL 4205"""

    signal_5 = parser.parse(test_message_5, "Test Channel")

    if signal_5:
        print("   ✅ نجح: قبول الإشارة الصحيحة")
        print(f"   الرمز: {signal_5.symbol}")
        print(f"   الاتجاه: {signal_5.action}")
        print(f"   TP: {signal_5.take_profits}")
        print(f"   SL: {signal_5.stop_loss}")
    else:
        print("   ❌ فشل: رفض إشارة صحيحة!")


def test_daily_report_manager():
    """اختبار مدير التقارير اليومية"""
    print("\n" + "=" * 60)
    print("🧪 اختبار نظام التقارير اليومية")
    print("=" * 60)

    manager = DailyReportManager()

    # اختبار 1: حفظ إشارة
    print("\n📝 اختبار 1: حفظ إشارة")
    test_signal = {
        'symbol': 'XAUUSD',
        'action': 'BUY',
        'entry_price': 4218.0,
        'take_profits': [4222.0, 4226.0, 4230.0],
        'stop_loss': 4205.0,
        'channel_name': 'Test Channel'
    }

    try:
        manager.save_signal(test_signal)
        print("   ✅ نجح: تم حفظ الإشارة")

        # التحقق من وجود الملف
        report = manager.load_report('signals')
        if report and report.get('total_signals', 0) > 0:
            print(f"   ✅ تم العثور على {report['total_signals']} إشارة في التقرير")
        else:
            print("   ⚠️ لم يتم العثور على إشارات في التقرير")
    except Exception as e:
        print(f"   ❌ فشل: {e}")

    # اختبار 2: حفظ صفقة
    print("\n📝 اختبار 2: حفظ صفقة")
    test_trade = {
        'ticket': 999999,
        'entry_price': 4220.5,
        'lot_size': 0.1,
        'profit': 25.50,
        'status': 'closed',
        'signal': test_signal
    }

    try:
        manager.save_trade(test_trade)
        print("   ✅ نجح: تم حفظ الصفقة")

        # التحقق من وجود الملف
        report = manager.load_report('trades')
        if report and report.get('total_trades', 0) > 0:
            print(f"   ✅ تم العثور على {report['total_trades']} صفقة في التقرير")
            print(f"   📊 إجمالي الأرباح: ${report.get('total_profit', 0):.2f}")
        else:
            print("   ⚠️ لم يتم العثور على صفقات في التقرير")
    except Exception as e:
        print(f"   ❌ فشل: {e}")

    # اختبار 3: إنشاء ملخص
    print("\n📝 اختبار 3: إنشاء ملخص يومي")
    try:
        summary = manager.generate_daily_summary()
        print("   ✅ نجح: تم إنشاء الملخص")
        print(f"\n   📊 الملخص:")
        print(f"   - التاريخ: {summary.get('date')}")
        print(f"   - عدد الإشارات: {summary['signals']['total']}")
        print(f"   - عدد الصفقات: {summary['trades']['total']}")
        print(f"   - معدل النجاح: {summary['trades']['win_rate']}%")
        print(f"   - صافي الربح: ${summary['profit_loss']['net_profit']:.2f}")
    except Exception as e:
        print(f"   ❌ فشل: {e}")

    # اختبار 4: تصدير إلى CSV
    print("\n📝 اختبار 4: تصدير إلى CSV")
    try:
        csv_file = manager.export_to_csv('signals')
        if csv_file:
            print(f"   ✅ نجح: تم التصدير إلى {csv_file}")
        else:
            print("   ⚠️ لم يتم التصدير (ربما لا توجد بيانات)")
    except Exception as e:
        print(f"   ❌ فشل: {e}")


def test_message_filtering():
    """اختبار تصفية الرسائل"""
    print("\n" + "=" * 60)
    print("🧪 اختبار تصفية الرسائل غير المفيدة")
    print("=" * 60)

    from main_gui import TelegramMT5GUI
    import re

    # إنشاء دالة is_useful_message بشكل مستقل للاختبار
    def is_useful_message(message_text: str) -> bool:
        useless_patterns = [
            r'profit.*achieved', r'target.*hit', r'tp.*reached',
            r'result.*today', r'join.*vip', r'subscribe',
            r'congratulation', r'congrats'
        ]

        message_upper = message_text.upper()
        for pattern in useless_patterns:
            if re.search(pattern, message_upper, re.IGNORECASE):
                return False

        required_keywords = [
            r'\b(GOLD|XAUUSD|BTC|EUR|GBP|USD|OIL|NAS)\b',
            r'\b(BUY|SELL|LONG|SHORT)\b',
        ]

        has_required = all(
            re.search(pattern, message_upper, re.IGNORECASE)
            for pattern in required_keywords
        )

        return has_required

    # اختبار رسائل مختلفة
    test_messages = [
        ("XAUUSD BUY 2050 TP 2055 SL 2045", True, "إشارة صحيحة"),
        ("Target hit! 50 pips profit!", False, "رسالة نتيجة"),
        ("Join our VIP group", False, "رسالة ترويجية"),
        ("Congratulations! TP reached", False, "رسالة تهنئة"),
        ("GOLD SELL NOW 2060", True, "إشارة بدون تفاصيل كاملة"),
        ("Market analysis for today", False, "رسالة تحليل"),
    ]

    for message, expected, description in test_messages:
        result = is_useful_message(message)
        status = "✅" if result == expected else "❌"
        print(f"{status} {description}: {'مفيدة' if result else 'غير مفيدة'}")


if __name__ == "__main__":
    # Set UTF-8 encoding for console output
    import sys
    import io
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("\n>>> بدء اختبار الإصلاحات الجديدة\n")

    # تشغيل جميع الاختبارات
    test_signal_parser_fixes()
    test_daily_report_manager()
    test_message_filtering()

    print("\n" + "=" * 60)
    print(">>> انتهت جميع الاختبارات")
    print("=" * 60)
    print("\n>>> راجع النتائج أعلاه للتأكد من نجاح جميع الإصلاحات\n")
