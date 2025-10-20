from telethon import TelegramClient, events
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.errors import SessionPasswordNeededError
import asyncio
import json
import os
from signal_parser import SignalParser, Signal
from typing import Callable, List, Dict
from datetime import datetime

class TelegramSignalClient:
    def __init__(self, api_id: str, api_hash: str, phone: str):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.client = None
        self.is_connected = False
        self.monitored_channels = []
        self.signal_parser = SignalParser()
        self.signal_callback = None
        self.message_callback = None  # callback لجميع الرسائل (ناجحة أو فاشلة)
        self.channels_file = 'data/channels.json'

        # إنشاء مجلد البيانات
        os.makedirs('data', exist_ok=True)

        # تحميل القنوات المحفوظة
        self.load_channels()

    async def start(self):
        """بدء الاتصال بالتليجرام"""
        try:
            # استخدام مسار واضح لملف الجلسة
            session_path = os.path.join('data', 'telegram_session')
            self.client = TelegramClient(session_path, int(self.api_id), self.api_hash)

            print("⏳ جارٍ الاتصال بالتليجرام...")

            await self.client.start(phone=self.phone)

            # التحقق من الاتصال
            if await self.client.is_user_authorized():
                self.is_connected = True
                print("✅ تم الاتصال بالتليجرام بنجاح")

                # تسجيل معالج الرسائل
                self.client.add_event_handler(self.message_handler, events.NewMessage())

                print(f"📢 تم تفعيل مراقبة {len(self.monitored_channels)} قناة")

                return True
            else:
                print("❌ فشل التحقق من الاتصال")
                return False

        except SessionPasswordNeededError:
            print("⚠️ مطلوب كلمة مرور التحقق بخطوتين")
            return False
        except ValueError as e:
            print(f"❌ خطأ في API ID: {str(e)}")
            print("تأكد من أن API_ID رقم صحيح")
            self.is_connected = False
            return False
        except Exception as e:
            print(f"❌ خطأ في الاتصال بالتليجرام: {str(e)}")
            self.is_connected = False
            return False

    async def disconnect(self):
        """قطع الاتصال"""
        if self.client:
            await self.client.disconnect()
            self.is_connected = False
            print("⚠️ تم قطع الاتصال بالتليجرام")

    def set_signal_callback(self, callback: Callable):
        """تعيين دالة callback عند استقبال إشارة جديدة"""
        self.signal_callback = callback

    def set_message_callback(self, callback: Callable):
        """تعيين دالة callback لجميع الرسائل (ناجحة أو فاشلة)"""
        self.message_callback = callback

    def _normalize_channel_id(self, chat_id: int) -> int:
        """
        تحويل chat_id من Telegram إلى ID القناة الحقيقي

        Telegram يستخدم صيغة -100xxxxxxxxxx للقنوات والمجموعات الكبيرة
        نحتاج لإزالة البادئة -100 للمطابقة مع البيانات المحفوظة

        Args:
            chat_id: معرف الدردشة من Telegram

        Returns:
            معرف القناة الحقيقي
        """
        if chat_id < 0:
            # إزالة السالب والبادئة -100
            chat_id_str = str(chat_id)
            if chat_id_str.startswith('-100'):
                # إزالة -100 من البداية
                return int(chat_id_str[4:])
            else:
                # إزالة السالب فقط
                return abs(chat_id)
        return chat_id

    async def message_handler(self, event):
        """معالج الرسائل الواردة"""
        try:
            # الحصول على chat_id وتحويله إلى الصيغة الصحيحة
            chat_id = event.chat_id

            # تحويل chat_id إلى ID القناة الحقيقي
            real_channel_id = self._normalize_channel_id(chat_id)

            # التحقق من أن الرسالة من قناة مراقبة ونشطة
            active_channel_ids = [ch['id'] for ch in self.monitored_channels if ch.get('status') == 'active']

            if not active_channel_ids:
                print("⚠️ لا توجد قنوات نشطة للمراقبة")
                print(f"   عدد القنوات المحفوظة: {len(self.monitored_channels)}")
                return

            if real_channel_id not in active_channel_ids:
                return  # تجاهل الرسائل من قنوات غير مراقبة بصمت

            message_text = event.message.message
            if not message_text:
                return

            # الحصول على معلومات القناة
            channel_info = next(
                (ch for ch in self.monitored_channels if ch['id'] == real_channel_id),
                None
            )

            if not channel_info:
                return

            channel_name = channel_info['name']

            # محاولة تحليل الرسالة
            signal = self.signal_parser.parse(message_text, channel_name)

            # بيانات الرسالة للواجهة
            message_data = {
                'channel_name': channel_name,
                'channel_id': real_channel_id,
                'message_text': message_text,
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'parsed': signal is not None
            }

            if signal:
                # نجح التحليل
                message_data['signal_info'] = {
                    'symbol': signal.symbol,
                    'action': signal.action,
                    'entry_price': signal.entry_price,
                    'entry_price_range': signal.entry_price_range,
                    'take_profits': signal.take_profits,
                    'stop_loss': signal.stop_loss
                }

                # تحديث حالة القناة
                channel_info['last_signal'] = datetime.now().isoformat()
                channel_info['signal_count'] = channel_info.get('signal_count', 0) + 1
                self.save_channels()

                # استدعاء callback للإشارة
                if self.signal_callback:
                    await self.signal_callback(signal)

            else:
                # فشل التحليل - جمع معلومات التشخيص
                symbol = self.signal_parser.extract_symbol(message_text)
                action = self.signal_parser.extract_action(message_text)
                entry_price, entry_range = self.signal_parser.extract_entry_price(message_text, symbol if symbol else "")
                take_profits = self.signal_parser.extract_take_profits(message_text, symbol if symbol else "")
                stop_loss = self.signal_parser.extract_stop_loss(message_text, symbol if symbol else "")

                message_data['diagnostics'] = {
                    'symbol': symbol,
                    'action': action,
                    'entry_price': entry_price,
                    'entry_range': entry_range,
                    'take_profits': take_profits,
                    'stop_loss': stop_loss
                }

            # استدعاء callback للرسالة (ناجحة أو فاشلة)
            if self.message_callback:
                await self.message_callback(message_data, signal)

        except Exception as e:
            print(f"❌ خطأ في معالجة الرسالة: {str(e)}")
            import traceback
            traceback.print_exc()

    async def add_channel(self, channel_identifier: str) -> Dict:
        """إضافة قناة للمراقبة (رابط أو username)"""
        try:
            # محاولة الانضمام إلى القناة
            entity = await self.client.get_entity(channel_identifier)

            # الحصول على معلومات القناة الكاملة
            full_channel = await self.client(GetFullChannelRequest(entity))

            channel_info = {
                'id': entity.id,
                'name': entity.title,
                'username': entity.username if hasattr(entity, 'username') else None,
                'added_date': datetime.now().isoformat(),
                'status': 'active',
                'signal_count': 0,
                'last_signal': None
            }

            # التحقق من عدم تكرار القناة
            if not any(ch['id'] == channel_info['id'] for ch in self.monitored_channels):
                self.monitored_channels.append(channel_info)
                self.save_channels()
                print(f"✅ تمت إضافة القناة: {channel_info['name']}")
                return {'success': True, 'channel': channel_info}
            else:
                return {'success': False, 'error': 'القناة موجودة بالفعل'}

        except Exception as e:
            print(f"❌ خطأ في إضافة القناة: {str(e)}")
            return {'success': False, 'error': str(e)}

    def remove_channel(self, channel_id: int) -> bool:
        """إزالة قناة من المراقبة"""
        try:
            self.monitored_channels = [
                ch for ch in self.monitored_channels if ch['id'] != channel_id
            ]
            self.save_channels()
            print(f"✅ تمت إزالة القناة")
            return True
        except Exception as e:
            print(f"❌ خطأ في إزالة القناة: {str(e)}")
            return False

    def toggle_channel_status(self, channel_id: int) -> bool:
        """تفعيل/تعطيل قناة"""
        try:
            for channel in self.monitored_channels:
                if channel['id'] == channel_id:
                    channel['status'] = 'active' if channel['status'] == 'inactive' else 'inactive'
                    self.save_channels()
                    return True
            return False
        except Exception as e:
            print(f"❌ خطأ في تغيير حالة القناة: {str(e)}")
            return False

    def get_channels(self) -> List[Dict]:
        """الحصول على قائمة القنوات"""
        return self.monitored_channels

    def save_channels(self):
        """حفظ القنوات إلى ملف"""
        try:
            with open(self.channels_file, 'w', encoding='utf-8') as f:
                json.dump(self.monitored_channels, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"❌ خطأ في حفظ القنوات: {str(e)}")

    def load_channels(self):
        """تحميل القنوات من الملف"""
        try:
            if os.path.exists(self.channels_file):
                with open(self.channels_file, 'r', encoding='utf-8') as f:
                    self.monitored_channels = json.load(f)
                print(f"✅ تم تحميل {len(self.monitored_channels)} قناة")
        except Exception as e:
            print(f"❌ خطأ في تحميل القنوات: {str(e)}")
            self.monitored_channels = []

    async def run(self):
        """تشغيل العميل"""
        try:
            await self.client.run_until_disconnected()
        except Exception as e:
            print(f"❌ خطأ في تشغيل العميل: {str(e)}")

    def get_connection_status(self) -> Dict:
        """الحصول على حالة الاتصال"""
        return {
            'connected': self.is_connected,
            'channels_count': len(self.monitored_channels),
            'active_channels': len([ch for ch in self.monitored_channels if ch['status'] == 'active'])
        }

    async def get_all_joined_channels(self) -> List[Dict]:
        """
        الحصول على جميع القنوات التي انضم لها المستخدم

        Returns:
            قائمة بمعلومات القنوات
        """
        try:
            if not self.client or not self.is_connected:
                print("❌ يجب الاتصال بالتليجرام أولاً")
                return []

            print("⏳ جارٍ تحميل جميع القنوات...")

            channels_list = []

            # الحصول على جميع المحادثات
            async for dialog in self.client.iter_dialogs():
                # فقط القنوات والمجموعات الخارقة
                if dialog.is_channel or dialog.is_group:
                    channel_info = {
                        'id': dialog.entity.id,
                        'name': dialog.title,
                        'username': dialog.entity.username if hasattr(dialog.entity, 'username') else None,
                        'is_channel': dialog.is_channel,
                        'is_group': dialog.is_group,
                        'participants_count': getattr(dialog.entity, 'participants_count', 0),
                        'is_monitored': any(ch['id'] == dialog.entity.id for ch in self.monitored_channels)
                    }
                    channels_list.append(channel_info)

            print(f"✅ تم تحميل {len(channels_list)} قناة/مجموعة")
            return channels_list

        except Exception as e:
            print(f"❌ خطأ في تحميل القنوات: {str(e)}")
            return []

    async def add_channel_by_id(self, channel_id: int, channel_name: str, username: str = None) -> Dict:
        """
        إضافة قناة للمراقبة باستخدام ID

        Args:
            channel_id: معرف القناة
            channel_name: اسم القناة
            username: اسم المستخدم للقناة (اختياري)

        Returns:
            نتيجة العملية
        """
        try:
            # التحقق من عدم تكرار القناة
            if any(ch['id'] == channel_id for ch in self.monitored_channels):
                return {'success': False, 'error': 'القناة موجودة بالفعل'}

            channel_info = {
                'id': channel_id,
                'name': channel_name,
                'username': username,
                'added_date': datetime.now().isoformat(),
                'status': 'active',
                'signal_count': 0,
                'last_signal': None
            }

            self.monitored_channels.append(channel_info)
            self.save_channels()

            print(f"✅ تمت إضافة القناة: {channel_name}")
            return {'success': True, 'channel': channel_info}

        except Exception as e:
            print(f"❌ خطأ في إضافة القناة: {str(e)}")
            return {'success': False, 'error': str(e)}
