#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
نظام تشفير الإعدادات
يستخدم cryptography لتشفير بيانات الاتصال الحساسة
"""

import os
import json
from cryptography.fernet import Fernet
from typing import Dict, Optional


class CredentialManager:
    """مدير تشفير بيانات الاعتماد"""

    def __init__(self, key_file: str = 'data/.key'):
        self.key_file = key_file
        self.credentials_file = 'data/credentials.enc'
        self._ensure_key()

    def _ensure_key(self):
        """التأكد من وجود مفتاح التشفير أو إنشاء واحد جديد"""
        os.makedirs('data', exist_ok=True)

        if os.path.exists(self.key_file):
            with open(self.key_file, 'rb') as f:
                self.key = f.read()
        else:
            # إنشاء مفتاح جديد
            self.key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(self.key)

            # إخفاء الملف في Windows
            if os.name == 'nt':
                try:
                    import ctypes
                    FILE_ATTRIBUTE_HIDDEN = 0x02
                    ctypes.windll.kernel32.SetFileAttributesW(self.key_file, FILE_ATTRIBUTE_HIDDEN)
                except:
                    pass

        self.cipher = Fernet(self.key)

    def encrypt_credentials(self, credentials: Dict) -> bool:
        """
        تشفير وحفظ بيانات الاعتماد

        Args:
            credentials: قاموس يحتوي على البيانات الحساسة

        Returns:
            True إذا نجح التشفير والحفظ
        """
        try:
            # تحويل القاموس إلى JSON
            json_data = json.dumps(credentials, ensure_ascii=False)

            # تشفير البيانات
            encrypted_data = self.cipher.encrypt(json_data.encode('utf-8'))

            # حفظ البيانات المشفرة
            with open(self.credentials_file, 'wb') as f:
                f.write(encrypted_data)

            print("✅ تم تشفير وحفظ بيانات الاعتماد بنجاح")
            return True

        except Exception as e:
            print(f"❌ خطأ في تشفير البيانات: {str(e)}")
            return False

    def decrypt_credentials(self) -> Optional[Dict]:
        """
        فك تشفير وقراءة بيانات الاعتماد

        Returns:
            قاموس يحتوي على البيانات المفكوكة، أو None في حالة الفشل
        """
        try:
            if not os.path.exists(self.credentials_file):
                return None

            # قراءة البيانات المشفرة
            with open(self.credentials_file, 'rb') as f:
                encrypted_data = f.read()

            # فك التشفير
            decrypted_data = self.cipher.decrypt(encrypted_data)

            # تحويل من JSON إلى قاموس
            credentials = json.loads(decrypted_data.decode('utf-8'))

            return credentials

        except Exception as e:
            print(f"❌ خطأ في فك تشفير البيانات: {str(e)}")
            return None

    def save_telegram_credentials(self, api_id: str, api_hash: str, phone: str) -> bool:
        """
        حفظ بيانات Telegram بشكل مشفر

        Args:
            api_id: API ID
            api_hash: API Hash
            phone: رقم الهاتف

        Returns:
            True إذا نجح الحفظ
        """
        # قراءة البيانات الحالية
        credentials = self.decrypt_credentials() or {}

        # تحديث بيانات Telegram
        credentials['telegram'] = {
            'api_id': api_id,
            'api_hash': api_hash,
            'phone': phone
        }

        return self.encrypt_credentials(credentials)

    def save_mt5_credentials(self, login: str, password: str, server: str) -> bool:
        """
        حفظ بيانات MT5 بشكل مشفر

        Args:
            login: رقم الحساب
            password: كلمة المرور
            server: اسم الخادم

        Returns:
            True إذا نجح الحفظ
        """
        # قراءة البيانات الحالية
        credentials = self.decrypt_credentials() or {}

        # تحديث بيانات MT5
        credentials['mt5'] = {
            'login': login,
            'password': password,
            'server': server
        }

        return self.encrypt_credentials(credentials)

    def get_telegram_credentials(self) -> Optional[Dict]:
        """الحصول على بيانات Telegram المحفوظة"""
        credentials = self.decrypt_credentials()
        return credentials.get('telegram') if credentials else None

    def get_mt5_credentials(self) -> Optional[Dict]:
        """الحصول على بيانات MT5 المحفوظة"""
        credentials = self.decrypt_credentials()
        return credentials.get('mt5') if credentials else None

    def clear_credentials(self) -> bool:
        """مسح جميع بيانات الاعتماد المحفوظة"""
        try:
            if os.path.exists(self.credentials_file):
                os.remove(self.credentials_file)
            print("✅ تم مسح بيانات الاعتماد")
            return True
        except Exception as e:
            print(f"❌ خطأ في مسح البيانات: {str(e)}")
            return False

    def has_saved_credentials(self) -> bool:
        """التحقق من وجود بيانات اعتماد محفوظة"""
        return os.path.exists(self.credentials_file)


# اختبار سريع
if __name__ == "__main__":
    import sys
    import io

    # إصلاح مشكلة الترميز في Windows
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    print("=" * 50)
    print("اختبار نظام التشفير")
    print("=" * 50)

    manager = CredentialManager()

    # اختبار حفظ بيانات Telegram
    print("\n📝 حفظ بيانات Telegram...")
    manager.save_telegram_credentials("12345678", "abcd1234", "+1234567890")

    # اختبار حفظ بيانات MT5
    print("\n📝 حفظ بيانات MT5...")
    manager.save_mt5_credentials("9876543", "password123", "MetaQuotes-Demo")

    # اختبار قراءة البيانات
    print("\n📖 قراءة بيانات Telegram...")
    telegram_creds = manager.get_telegram_credentials()
    if telegram_creds:
        print(f"   API ID: {telegram_creds['api_id']}")
        print(f"   Phone: {telegram_creds['phone']}")

    print("\n📖 قراءة بيانات MT5...")
    mt5_creds = manager.get_mt5_credentials()
    if mt5_creds:
        print(f"   Login: {mt5_creds['login']}")
        print(f"   Server: {mt5_creds['server']}")

    print("\n✅ الاختبار اكتمل بنجاح!")
