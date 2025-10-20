#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
سكريبت فحص الإعداد
يتحقق من أن جميع المكتبات مثبتة والإعدادات صحيحة
"""

import sys
import os
import io

# إصلاح مشكلة الترميز في Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def check_python_version():
    """التحقق من نسخة Python"""
    print("=" * 50)
    print("فحص نسخة Python")
    print("=" * 50)
    version = sys.version_info
    print(f"Python {version.major}.{version.minor}.{version.micro}")

    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ يتطلب Python 3.8 أو أحدث")
        return False

    print("✅ نسخة Python مناسبة")
    return True

def check_libraries():
    """التحقق من المكتبات المطلوبة"""
    print("\n" + "=" * 50)
    print("فحص المكتبات المطلوبة")
    print("=" * 50)

    libraries = [
        ('customtkinter', 'customtkinter'),
        ('telethon', 'Telethon'),
        ('MetaTrader5', 'MetaTrader5'),
        ('dotenv', 'python-dotenv'),
        ('matplotlib', 'matplotlib'),
        ('cryptography', 'cryptography'),
    ]

    all_ok = True
    for module_name, display_name in libraries:
        try:
            __import__(module_name)
            print(f"✅ {display_name}")
        except ImportError:
            print(f"❌ {display_name} - غير مثبت")
            all_ok = False

    return all_ok

def check_env_file():
    """التحقق من ملف .env"""
    print("\n" + "=" * 50)
    print("فحص ملف الإعدادات (.env)")
    print("=" * 50)

    if not os.path.exists('.env'):
        print("❌ ملف .env غير موجود")
        print("ℹ️  قم بنسخ .env.example إلى .env وعدل الإعدادات")
        return False

    print("✅ ملف .env موجود")

    # قراءة الإعدادات
    from dotenv import load_dotenv
    load_dotenv()

    required_vars = ['API_ID', 'API_HASH', 'PHONE_NUMBER']
    all_ok = True

    for var in required_vars:
        value = os.getenv(var, '')
        if not value or value.startswith('your_'):
            print(f"⚠️  {var}: غير مُعد")
            all_ok = False
        else:
            # إخفاء القيم الحساسة
            if var == 'API_HASH':
                display = value[:4] + '...' + value[-4:]
            elif var == 'PHONE_NUMBER':
                display = value[:4] + '****' + value[-4:]
            else:
                display = value
            print(f"✅ {var}: {display}")

    return all_ok

def check_data_folder():
    """التحقق من مجلد البيانات"""
    print("\n" + "=" * 50)
    print("فحص مجلد البيانات")
    print("=" * 50)

    if not os.path.exists('data'):
        print("ℹ️  مجلد data غير موجود - سيتم إنشاؤه تلقائياً")
        try:
            os.makedirs('data')
            print("✅ تم إنشاء مجلد data")
        except Exception as e:
            print(f"❌ فشل إنشاء مجلد data: {e}")
            return False
    else:
        print("✅ مجلد data موجود")

    return True

def main():
    """الدالة الرئيسية"""
    print("\n")
    print("=" * 50)
    print("  فحص إعداد Telegram to MT5 Signal Copier")
    print("=" * 50)
    print("\n")

    checks = [
        ("نسخة Python", check_python_version),
        ("المكتبات المطلوبة", check_libraries),
        ("ملف الإعدادات", check_env_file),
        ("مجلد البيانات", check_data_folder),
    ]

    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append(result)
        except Exception as e:
            print(f"❌ خطأ في فحص {name}: {e}")
            results.append(False)

    # النتيجة النهائية
    print("\n" + "=" * 50)
    print("النتيجة النهائية")
    print("=" * 50)

    if all(results):
        print("✅ جميع الفحوصات نجحت! البرنامج جاهز للتشغيل")
        print("\nلتشغيل البرنامج:")
        print("  run.bat")
        return 0
    else:
        print("❌ بعض الفحوصات فشلت")
        print("\nحلول مقترحة:")

        if not results[1]:  # المكتبات
            print("  1. ثبت المكتبات: install.bat")

        if not results[2]:  # ملف .env
            print("  2. أنشئ ملف .env:")
            print("     copy .env.example .env")
            print("     notepad .env")

        print("\nللمزيد من المساعدة، راجع: README_AR.md")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        print("\n")
        input("اضغط Enter للخروج...")
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  تم الإلغاء")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ خطأ غير متوقع: {e}")
        import traceback
        traceback.print_exc()
        input("\nاضغط Enter للخروج...")
        sys.exit(1)
