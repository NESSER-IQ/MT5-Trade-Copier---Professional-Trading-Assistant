#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
اختبار نظام التشفير
Test Encryption System
"""

import sys
import io
import os

# إصلاح مشكلة الترميز في Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from encryption import CredentialManager

def test_encryption():
    """اختبار شامل لنظام التشفير"""
    print("=" * 60)
    print("🔐 اختبار نظام تشفير بيانات الاعتماد")
    print("=" * 60)
    print()

    # إنشاء مدير التشفير
    manager = CredentialManager()

    # بيانات تجريبية
    test_telegram = {
        'api_id': '12345678',
        'api_hash': 'abcd1234567890abcdef1234567890ab',
        'phone': '+1234567890'
    }

    test_mt5 = {
        'login': '98765432',
        'password': 'SecurePassword123!',
        'server': 'MetaQuotes-Demo'
    }

    # اختبار 1: حفظ بيانات Telegram
    print("📝 اختبار 1: حفظ بيانات Telegram...")
    result = manager.save_telegram_credentials(
        test_telegram['api_id'],
        test_telegram['api_hash'],
        test_telegram['phone']
    )

    if result:
        print("   ✅ نجح حفظ بيانات Telegram")
    else:
        print("   ❌ فشل حفظ بيانات Telegram")
        return False

    # اختبار 2: حفظ بيانات MT5
    print("\n📝 اختبار 2: حفظ بيانات MT5...")
    result = manager.save_mt5_credentials(
        test_mt5['login'],
        test_mt5['password'],
        test_mt5['server']
    )

    if result:
        print("   ✅ نجح حفظ بيانات MT5")
    else:
        print("   ❌ فشل حفظ بيانات MT5")
        return False

    # اختبار 3: قراءة بيانات Telegram
    print("\n📖 اختبار 3: قراءة بيانات Telegram...")
    telegram_creds = manager.get_telegram_credentials()

    if telegram_creds:
        print("   ✅ نجح قراءة بيانات Telegram")
        print(f"      API ID: {telegram_creds['api_id']}")
        print(f"      Phone: {telegram_creds['phone']}")
        print(f"      API Hash: {telegram_creds['api_hash'][:4]}...{telegram_creds['api_hash'][-4:]}")

        # التحقق من صحة البيانات
        if (telegram_creds['api_id'] == test_telegram['api_id'] and
            telegram_creds['phone'] == test_telegram['phone']):
            print("   ✅ البيانات صحيحة 100%")
        else:
            print("   ❌ البيانات غير صحيحة!")
            return False
    else:
        print("   ❌ فشل قراءة بيانات Telegram")
        return False

    # اختبار 4: قراءة بيانات MT5
    print("\n📖 اختبار 4: قراءة بيانات MT5...")
    mt5_creds = manager.get_mt5_credentials()

    if mt5_creds:
        print("   ✅ نجح قراءة بيانات MT5")
        print(f"      Login: {mt5_creds['login']}")
        print(f"      Server: {mt5_creds['server']}")
        print(f"      Password: {'*' * len(mt5_creds['password'])}")

        # التحقق من صحة البيانات
        if (mt5_creds['login'] == test_mt5['login'] and
            mt5_creds['server'] == test_mt5['server'] and
            mt5_creds['password'] == test_mt5['password']):
            print("   ✅ البيانات صحيحة 100%")
        else:
            print("   ❌ البيانات غير صحيحة!")
            return False
    else:
        print("   ❌ فشل قراءة بيانات MT5")
        return False

    # اختبار 5: التحقق من الملفات المنشأة
    print("\n📁 اختبار 5: التحقق من الملفات المنشأة...")

    key_file = 'data/.key'
    creds_file = 'data/credentials.enc'

    if os.path.exists(key_file):
        print(f"   ✅ ملف المفتاح موجود: {key_file}")
        print(f"      حجم الملف: {os.path.getsize(key_file)} bytes")
    else:
        print(f"   ❌ ملف المفتاح غير موجود: {key_file}")
        return False

    if os.path.exists(creds_file):
        print(f"   ✅ ملف البيانات المشفرة موجود: {creds_file}")
        print(f"      حجم الملف: {os.path.getsize(creds_file)} bytes")
    else:
        print(f"   ❌ ملف البيانات المشفرة غير موجود: {creds_file}")
        return False

    # اختبار 6: محاولة قراءة الملف المشفر مباشرة
    print("\n🔒 اختبار 6: محاولة قراءة الملف المشفر مباشرة...")
    try:
        with open(creds_file, 'r', encoding='utf-8') as f:
            content = f.read(50)  # أول 50 حرف
            print(f"   المحتوى المشفر: {content}...")

            # التحقق من عدم وجود بيانات واضحة
            if test_telegram['api_hash'] in content or test_mt5['password'] in content:
                print("   ❌ تحذير: البيانات غير مشفرة!")
                return False
            else:
                print("   ✅ البيانات مشفرة بشكل صحيح (غير قابلة للقراءة)")
    except UnicodeDecodeError:
        print("   ✅ البيانات مشفرة بشكل ثنائي (غير قابلة للقراءة كنص)")

    print("\n" + "=" * 60)
    print("✅ جميع الاختبارات نجحت!")
    print("=" * 60)
    return True

def cleanup_test_files():
    """تنظيف ملفات الاختبار"""
    print("\n🧹 هل تريد حذف ملفات الاختبار؟ (y/n): ", end='')
    try:
        choice = input().lower()
        if choice == 'y':
            files_to_delete = ['data/.key', 'data/credentials.enc']
            for file in files_to_delete:
                if os.path.exists(file):
                    os.remove(file)
                    print(f"   ✅ تم حذف: {file}")
            print("   ✅ تم التنظيف")
        else:
            print("   ℹ️  تم الاحتفاظ بالملفات")
    except:
        print("   ℹ️  تم الاحتفاظ بالملفات")

if __name__ == "__main__":
    try:
        os.makedirs('data', exist_ok=True)

        success = test_encryption()

        if success:
            cleanup_test_files()
            sys.exit(0)
        else:
            print("\n❌ فشل بعض الاختبارات")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n⚠️  تم الإلغاء")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ خطأ غير متوقع: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
