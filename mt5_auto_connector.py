#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
نظام الاتصال التلقائي بـ MT5
يكتشف الحسابات المفتوحة ويتصل بها تلقائياً
"""

import MetaTrader5 as mt5
from typing import List, Dict, Optional
import time


class MT5AutoConnector:
    """مدير الاتصال التلقائي بـ MT5"""

    @staticmethod
    def get_current_account() -> Optional[Dict]:
        """
        الحصول على معلومات الحساب الحالي المفتوح في MT5

        Returns:
            قاموس بمعلومات الحساب أو None إذا لم يكن متصل
        """
        try:
            # محاولة التهيئة
            if not mt5.initialize():
                print("⚠️ MT5 غير مفتوح أو غير متصل")
                return None

            # الحصول على معلومات الحساب
            account_info = mt5.account_info()

            if account_info is None:
                print("⚠️ لا يوجد حساب متصل حالياً")
                mt5.shutdown()
                return None

            # تحويل إلى قاموس
            account_data = {
                'login': account_info.login,
                'server': account_info.server,
                'name': account_info.name,
                'balance': account_info.balance,
                'equity': account_info.equity,
                'currency': account_info.currency,
                'leverage': account_info.leverage,
                'company': account_info.company,
                'trade_mode': account_info.trade_mode,
            }

            print(f"✅ تم اكتشاف حساب: {account_data['login']} على {account_data['server']}")
            return account_data

        except Exception as e:
            print(f"❌ خطأ في اكتشاف الحساب: {str(e)}")
            return None
        finally:
            # عدم إغلاق MT5 للحفاظ على الاتصال
            pass

    @staticmethod
    def connect_to_current_account() -> bool:
        """
        الاتصال بالحساب المفتوح حالياً في MT5

        Returns:
            True إذا نجح الاتصال
        """
        try:
            if not mt5.initialize():
                print("❌ فشل تهيئة MT5")
                print("⚠️ تأكد من:")
                print("   1. تطبيق MT5 Terminal مفتوح")
                print("   2. تم تسجيل الدخول في MT5")
                return False

            account_info = mt5.account_info()

            if account_info is None:
                print("❌ لا يوجد حساب متصل")
                print("⚠️ افتح MT5 Terminal وسجل دخول أولاً")
                return False

            print(f"✅ متصل بحساب: {account_info.login}")
            print(f"   الخادم: {account_info.server}")
            print(f"   الشركة: {account_info.company}")
            print(f"   الرصيد: {account_info.balance} {account_info.currency}")
            print(f"   الرافعة: 1:{account_info.leverage}")

            return True

        except Exception as e:
            print(f"❌ خطأ في الاتصال: {str(e)}")
            return False

    @staticmethod
    def is_mt5_running() -> bool:
        """
        التحقق من أن MT5 Terminal يعمل

        Returns:
            True إذا كان MT5 يعمل
        """
        try:
            if mt5.initialize():
                version = mt5.version()
                if version:
                    print(f"✅ MT5 يعمل - الإصدار: {version}")
                    return True
            return False
        except:
            return False

    @staticmethod
    def get_terminal_info() -> Optional[Dict]:
        """
        الحصول على معلومات MT5 Terminal

        Returns:
            قاموس بمعلومات Terminal
        """
        try:
            if not mt5.initialize():
                return None

            terminal_info = mt5.terminal_info()

            if terminal_info is None:
                return None

            return {
                'connected': terminal_info.connected,
                'trade_allowed': terminal_info.trade_allowed,
                'build': terminal_info.build,
                'company': terminal_info.company,
                'name': terminal_info.name,
                'language': terminal_info.language,
                'path': terminal_info.path,
            }

        except Exception as e:
            print(f"❌ خطأ في الحصول على معلومات Terminal: {str(e)}")
            return None

    @staticmethod
    def check_connection_status() -> Dict:
        """
        فحص شامل لحالة الاتصال

        Returns:
            قاموس بحالة الاتصال التفصيلية
        """
        status = {
            'mt5_running': False,
            'mt5_initialized': False,
            'account_logged_in': False,
            'trade_allowed': False,
            'account_info': None,
            'terminal_info': None,
            'errors': []
        }

        try:
            # 1. التحقق من MT5
            if not mt5.initialize():
                status['errors'].append("MT5 غير مفتوح أو فشل التهيئة")
                return status

            status['mt5_running'] = True
            status['mt5_initialized'] = True

            # 2. معلومات Terminal
            terminal_info = mt5.terminal_info()
            if terminal_info:
                status['terminal_info'] = {
                    'connected': terminal_info.connected,
                    'trade_allowed': terminal_info.trade_allowed,
                    'company': terminal_info.company,
                }
                status['trade_allowed'] = terminal_info.trade_allowed

            # 3. معلومات الحساب
            account_info = mt5.account_info()
            if account_info:
                status['account_logged_in'] = True
                status['account_info'] = {
                    'login': account_info.login,
                    'server': account_info.server,
                    'balance': account_info.balance,
                    'currency': account_info.currency,
                }
            else:
                status['errors'].append("لا يوجد حساب متصل")

            return status

        except Exception as e:
            status['errors'].append(f"خطأ: {str(e)}")
            return status


# اختبار سريع
if __name__ == "__main__":
    import sys
    import io

    # إصلاح الترميز
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    print("=" * 60)
    print("اختبار نظام الاتصال التلقائي بـ MT5")
    print("=" * 60)
    print()

    connector = MT5AutoConnector()

    # 1. فحص حالة MT5
    print("📊 فحص حالة MT5...")
    status = connector.check_connection_status()

    print(f"   MT5 يعمل: {'✅' if status['mt5_running'] else '❌'}")
    print(f"   تم التهيئة: {'✅' if status['mt5_initialized'] else '❌'}")
    print(f"   حساب متصل: {'✅' if status['account_logged_in'] else '❌'}")
    print(f"   التداول مسموح: {'✅' if status['trade_allowed'] else '❌'}")

    if status['errors']:
        print("\n⚠️ أخطاء:")
        for error in status['errors']:
            print(f"   - {error}")

    # 2. محاولة الاتصال
    if status['mt5_initialized']:
        print("\n🔄 محاولة الاتصال بالحساب الحالي...")
        success = connector.connect_to_current_account()

        if success:
            print("\n✅ الاتصال ناجح!")

            # عرض معلومات الحساب
            account = connector.get_current_account()
            if account:
                print("\n📋 معلومات الحساب:")
                print(f"   رقم الحساب: {account['login']}")
                print(f"   الخادم: {account['server']}")
                print(f"   الشركة: {account['company']}")
                print(f"   الرصيد: {account['balance']} {account['currency']}")
                print(f"   الرافعة: 1:{account['leverage']}")
        else:
            print("\n❌ فشل الاتصال")
            print("⚠️ تأكد من فتح MT5 Terminal وتسجيل الدخول")

    print("\n" + "=" * 60)
    input("\nاضغط Enter للخروج...")
