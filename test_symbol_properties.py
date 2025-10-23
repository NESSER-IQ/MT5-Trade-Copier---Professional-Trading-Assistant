#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
اختبار نظام فحص خصائص الرموز
"""

import MetaTrader5 as mt5
from mt5_manager import MT5Manager

def test_symbol_properties():
    """اختبار الحصول على خصائص رمز"""
    
    print("=" * 70)
    print("🧪 اختبار نظام فحص خصائص الرموز")
    print("=" * 70)
    print()
    
    # إنشاء MT5Manager
    manager = MT5Manager()
    
    # محاولة الاتصال التلقائي
    print("📡 محاولة الاتصال بـ MT5...")
    if manager.auto_connect():
        print("✅ تم الاتصال بنجاح!")
        print()
    else:
        print("❌ فشل الاتصال - يجب أن يكون MT5 مفتوحاً")
        return
    
    # اختبار 1: فحص رمز واحد
    print("\n" + "=" * 70)
    print("📝 اختبار 1: فحص رمز واحد (XAUUSD)")
    print("=" * 70)
    
    properties = manager.get_symbol_properties("XAUUSD", verbose=True)
    
    if properties:
        print("✅ نجح الاختبار 1")
        
        # حفظ الخصائص
        print("\n💾 حفظ الخصائص في ملف...")
        if manager.save_symbol_properties("XAUUSD"):
            print("✅ تم الحفظ بنجاح")
        else:
            print("❌ فشل الحفظ")
    else:
        print("❌ فشل الاختبار 1")
    
    # اختبار 2: فحص رموز متعددة
    print("\n" + "=" * 70)
    print("📝 اختبار 2: فحص رموز متعددة")
    print("=" * 70)
    
    test_symbols = ['EURUSD', 'GBPUSD', 'USDJPY']
    
    for symbol in test_symbols:
        print(f"\n🔍 فحص {symbol}...")
        props = manager.get_symbol_properties(symbol, verbose=False)
        if props:
            print(f"   ✅ {symbol}: trade_allowed={props['trade_allowed']}, "
                  f"digits={props['digits']}, "
                  f"spread={props['spread']}")
        else:
            print(f"   ❌ {symbol}: فشل الفحص")
    
    # اختبار 3: التحقق من الملف المحفوظ
    print("\n" + "=" * 70)
    print("📝 اختبار 3: التحقق من الملف المحفوظ")
    print("=" * 70)
    
    import os
    import json
    
    if os.path.exists('data/symbols_info.json'):
        with open('data/symbols_info.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"✅ الملف موجود")
        print(f"   عدد الرموز المحفوظة: {len(data)}")
        print(f"   الرموز: {', '.join(list(data.keys())[:10])}")
        
        if len(data) > 10:
            print(f"   ... و {len(data) - 10} رمز آخر")
    else:
        print("⚠️ الملف غير موجود بعد")
    
    print("\n" + "=" * 70)
    print("🎯 انتهى الاختبار")
    print("=" * 70)
    
    # قطع الاتصال
    manager.disconnect()

if __name__ == "__main__":
    test_symbol_properties()
