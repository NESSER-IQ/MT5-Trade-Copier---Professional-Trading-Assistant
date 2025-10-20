import MetaTrader5 as mt5
from typing import Optional, Dict, List, Tuple
from datetime import datetime
import time
import json
import os
from signal_parser import Signal
from threading import Thread, Lock

try:
    from mt5_auto_connector import MT5AutoConnector
except ImportError:
    MT5AutoConnector = None

class MT5Manager:
    def __init__(self):
        self.is_connected = False
        self.account_info = None
        self.active_positions = {}
        self.trade_history = []
        self.lock = Lock()
        self.trailing_thread = None
        self.trailing_active = False
        self.trades_file = 'data/trades.json'
        self.auto_connector = MT5AutoConnector() if MT5AutoConnector else None

        # إنشاء مجلد البيانات
        os.makedirs('data', exist_ok=True)

        # ذاكرة تخزين مؤقت لأسماء الرموز (لتسريع البحث)
        self.symbol_cache = {}

    def connect(self, login: int, password: str, server: str) -> bool:
        """الاتصال بـ MT5"""
        try:
            # التحقق من تثبيت MT5
            if not mt5.initialize():
                error_code, error_msg = mt5.last_error()
                print(f"❌ فشل تهيئة MT5: ({error_code}, '{error_msg}')")

                if error_code == -6:
                    print("⚠️  تأكد من:")
                    print("   1. تطبيق MT5 Terminal مفتوح ويعمل")
                    print("   2. لم يتم إدخال كلمة مرور خاطئة عدة مرات")
                    print("   3. الحساب غير محظور")
                return False

            # تسجيل الدخول
            authorized = mt5.login(login=login, password=password, server=server)

            if not authorized:
                error_code, error_msg = mt5.last_error()
                print(f"❌ فشل تسجيل الدخول: ({error_code}, '{error_msg}')")

                if error_code == -6:
                    print("⚠️  أسباب محتملة:")
                    print("   1. رقم الحساب خاطئ")
                    print("   2. كلمة المرور خاطئة")
                    print("   3. اسم الخادم خاطئ")
                    print("   4. الحساب منتهي أو محظور")
                    print("   5. افتح MT5 Terminal يدوياً وتأكد من تسجيل الدخول أولاً")

                mt5.shutdown()
                return False

            self.is_connected = True
            self.account_info = mt5.account_info()

            if self.account_info is None:
                print("❌ فشل الحصول على معلومات الحساب")
                return False

            print(f"✅ تم الاتصال بـ MT5 - الحساب: {self.account_info.login}")
            print(f"   الرصيد: {self.account_info.balance} USD")
            print(f"   الرافعة: 1:{self.account_info.leverage}")

            # بدء نظام Trailing Stop
            self.start_trailing_stop()

            return True

        except Exception as e:
            print(f"❌ خطأ في الاتصال بـ MT5: {str(e)}")
            return False

    def disconnect(self):
        """قطع الاتصال"""
        self.trailing_active = False
        if self.trailing_thread:
            self.trailing_thread.join(timeout=5)

        mt5.shutdown()
        self.is_connected = False
        print("⚠️ تم قطع الاتصال بـ MT5")

    def connect_auto(self) -> bool:
        """الاتصال التلقائي بالحساب المفتوح في MT5 Terminal"""
        try:
            if not self.auto_connector:
                print("❌ نظام الاتصال التلقائي غير متوفر")
                print("⚠️ تأكد من وجود ملف mt5_auto_connector.py")
                return False

            print("🔍 البحث عن حساب MT5 مفتوح...")

            # محاولة الاتصال بالحساب الحالي
            if self.auto_connector.connect_to_current_account():
                # الحصول على معلومات الحساب
                account_data = self.auto_connector.get_current_account()

                if account_data:
                    self.is_connected = True
                    self.account_info = mt5.account_info()

                    print(f"✅ تم الاتصال التلقائي بـ MT5")
                    print(f"   الحساب: {account_data['login']}")
                    print(f"   الخادم: {account_data['server']}")
                    print(f"   الشركة: {account_data['company']}")
                    print(f"   الرصيد: {account_data['balance']} {account_data['currency']}")
                    print(f"   الرافعة: 1:{account_data['leverage']}")

                    # بدء نظام Trailing Stop
                    self.start_trailing_stop()

                    return True
                else:
                    print("❌ فشل الحصول على معلومات الحساب")
                    return False
            else:
                print("❌ فشل الاتصال التلقائي")
                print("⚠️ تأكد من:")
                print("   1. تطبيق MT5 Terminal مفتوح")
                print("   2. تم تسجيل الدخول في MT5")
                print("   3. الحساب نشط ومتصل")
                return False

        except Exception as e:
            print(f"❌ خطأ في الاتصال التلقائي: {str(e)}")
            return False

    def get_available_symbols(self, search_term: str = "") -> List[str]:
        """
        الحصول على قائمة الرموز المتاحة في المنصة
        يمكن تصفية النتائج باستخدام search_term
        """
        if not self.is_connected:
            return []

        try:
            all_symbols = mt5.symbols_get()
            if not all_symbols:
                return []

            symbol_names = [s.name for s in all_symbols]

            if search_term:
                search_lower = search_term.lower()
                symbol_names = [s for s in symbol_names if search_lower in s.lower()]

            return sorted(symbol_names)
        except Exception as e:
            print(f"❌ خطأ في الحصول على الرموز: {e}")
            return []

    def clear_symbol_cache(self):
        """مسح ذاكرة التخزين المؤقت للرموز"""
        self.symbol_cache.clear()
        print("✅ تم مسح ذاكرة الرموز المؤقتة")

    def find_symbol_in_platform(self, base_symbol: str) -> Optional[str]:
        """
        البحث الذكي عن الرمز في المنصة مع مراعاة اللواحق والبادئات
        مثال: XAUUSD -> XAUUSD, XAUUSD+, XAUUSD#, XAUUSDm, etc.
        """
        # التحقق من الذاكرة المؤقتة أولاً
        if base_symbol in self.symbol_cache:
            cached_symbol = self.symbol_cache[base_symbol]
            # التحقق من أن الرمز المحفوظ لا زال موجوداً
            if mt5.symbol_info(cached_symbol) is not None:
                return cached_symbol

        # البحث المباشر - محاولة الاسم الأصلي أولاً
        if mt5.symbol_info(base_symbol) is not None:
            self.symbol_cache[base_symbol] = base_symbol
            return base_symbol

        print(f"🔍 البحث عن الرمز {base_symbol} في المنصة...")

        # الحصول على جميع الرموز المتاحة
        all_symbols = mt5.symbols_get()
        if not all_symbols:
            print(f"❌ فشل الحصول على قائمة الرموز من MT5")
            return None

        # قائمة باللواحق والبادئات الشائعة
        common_suffixes = ['', '+', '#', '-', '.', 'm', 'pro', 'a', 'b', 'c', '_', 'i', 'f']

        # 1. البحث بالتطابق الدقيق مع اللواحق الشائعة
        for suffix in common_suffixes:
            test_symbol = f"{base_symbol}{suffix}"
            symbol_info = mt5.symbol_info(test_symbol)
            if symbol_info is not None:
                print(f"✅ تم العثور على الرمز: {base_symbol} -> {test_symbol}")
                self.symbol_cache[base_symbol] = test_symbol
                return test_symbol

        # 2. البحث في جميع الرموز المتاحة (case-insensitive)
        base_lower = base_symbol.lower()
        for symbol in all_symbols:
            symbol_name = symbol.name
            # تحقق من أن الرمز يبدأ بالاسم الأساسي
            if symbol_name.lower().startswith(base_lower):
                # تحقق من أن الفرق طفيف (لواحق فقط)
                suffix = symbol_name[len(base_symbol):]
                if len(suffix) <= 4:  # لواحق قصيرة فقط
                    print(f"✅ تم العثور على الرمز: {base_symbol} -> {symbol_name}")
                    self.symbol_cache[base_symbol] = symbol_name
                    return symbol_name

        # 3. البحث العكسي - قد يكون هناك بادئة
        for symbol in all_symbols:
            symbol_name = symbol.name
            if base_lower in symbol_name.lower():
                print(f"⚠️ وُجد رمز مشابه: {base_symbol} -> {symbol_name} (تحقق يدوياً)")
                # لا نحفظ في الذاكرة المؤقتة لأنه غير دقيق
                return symbol_name

        print(f"❌ لم يتم العثور على الرمز {base_symbol} في المنصة")
        print(f"💡 نصيحة: تحقق من أن الرمز متاح في حسابك")

        # عرض الرموز المتاحة المشابهة
        similar = [s.name for s in all_symbols if base_symbol[:4].lower() in s.name.lower()]
        if similar:
            print(f"📋 رموز مشابهة متاحة: {', '.join(similar[:5])}")

        return None

    def execute_signal(self, signal: Signal, lot_size: float = 0.01) -> Dict:
        """تنفيذ إشارة تداول - مع دعم البحث الذكي عن الرموز"""
        if not self.is_connected:
            return {'success': False, 'error': 'غير متصل بـ MT5'}

        try:
            # البحث الذكي عن الرمز في المنصة
            actual_symbol = self.find_symbol_in_platform(signal.symbol)

            if actual_symbol is None:
                return {'success': False, 'error': f'الرمز {signal.symbol} غير موجود في المنصة'}

            # الحصول على معلومات الرمز
            symbol_info = mt5.symbol_info(actual_symbol)
            if symbol_info is None:
                return {'success': False, 'error': f'فشل الحصول على معلومات الرمز {actual_symbol}'}

            if not symbol_info.visible:
                if not mt5.symbol_select(actual_symbol, True):
                    return {'success': False, 'error': f'فشل تفعيل الرمز {actual_symbol}'}

            # تحديد نوع الأمر
            order_type = mt5.ORDER_TYPE_BUY if signal.action == 'BUY' else mt5.ORDER_TYPE_SELL

            # تحديد سعر الدخول
            if signal.entry_price:
                entry_price = signal.entry_price
            elif signal.entry_price_range:
                # استخدام متوسط النطاق
                entry_price = sum(signal.entry_price_range) / 2
            else:
                # استخدام السعر الحالي
                if signal.action == 'BUY':
                    entry_price = mt5.symbol_info_tick(actual_symbol).ask
                else:
                    entry_price = mt5.symbol_info_tick(actual_symbol).bid

            # إعداد طلب التداول
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": actual_symbol,  # استخدام الرمز الفعلي من المنصة
                "volume": lot_size,
                "type": order_type,
                "price": entry_price,
                "sl": signal.stop_loss,
                "tp": signal.take_profits[0] if signal.take_profits else 0,  # أول TP
                "deviation": 20,
                "magic": 234000,
                "comment": f"Signal: {signal.symbol} from {signal.channel_name}",  # حفظ الاسم الأصلي في التعليق
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            # إرسال الطلب
            result = mt5.order_send(request)

            if result is None:
                return {'success': False, 'error': 'فشل إرسال الطلب'}

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                return {
                    'success': False,
                    'error': f'فشل تنفيذ الطلب: {result.retcode} - {result.comment}'
                }

            # حفظ معلومات الصفقة
            trade_info = {
                'ticket': result.order,
                'signal': signal.__dict__,
                'opened_at': datetime.now().isoformat(),
                'entry_price': result.price,
                'lot_size': lot_size,
                'current_tp_index': 0,  # لتتبع TP الحالي
                'status': 'open'
            }

            with self.lock:
                self.active_positions[result.order] = trade_info
                self.save_trades()

            # عرض رسالة نجاح مع الاسم الفعلي إذا كان مختلفاً
            symbol_display = f"{signal.symbol} ({actual_symbol})" if actual_symbol != signal.symbol else signal.symbol
            print(f"✅ تم فتح صفقة {signal.action} على {symbol_display}")
            print(f"   التذكرة: {result.order}")
            print(f"   السعر: {result.price}")

            return {
                'success': True,
                'ticket': result.order,
                'price': result.price,
                'actual_symbol': actual_symbol,  # إضافة الاسم الفعلي
                'trade_info': trade_info
            }

        except Exception as e:
            print(f"❌ خطأ في تنفيذ الإشارة: {str(e)}")
            return {'success': False, 'error': str(e)}

    def start_trailing_stop(self):
        """بدء نظام Trailing Stop"""
        if not self.trailing_active:
            self.trailing_active = True
            self.trailing_thread = Thread(target=self._trailing_stop_worker, daemon=True)
            self.trailing_thread.start()
            print("✅ تم تشغيل نظام Trailing Stop")

    def _trailing_stop_worker(self):
        """عامل Trailing Stop - يعمل في خلفية منفصلة"""
        while self.trailing_active:
            try:
                if not self.is_connected:
                    time.sleep(5)
                    continue

                with self.lock:
                    # نسخة من المراكز للعمل عليها
                    positions = dict(self.active_positions)

                for ticket, trade_info in positions.items():
                    self._update_trailing_stop(ticket, trade_info)

                time.sleep(2)  # فحص كل 2 ثانية

            except Exception as e:
                print(f"❌ خطأ في Trailing Stop: {str(e)}")
                time.sleep(5)

    def _update_trailing_stop(self, ticket: int, trade_info: Dict):
        """تحديث Trailing Stop لصفقة معينة"""
        try:
            # الحصول على معلومات الصفقة الحالية
            position = mt5.positions_get(ticket=ticket)

            if not position or len(position) == 0:
                # الصفقة مغلقة
                with self.lock:
                    if ticket in self.active_positions:
                        self.active_positions[ticket]['status'] = 'closed'
                        self.active_positions[ticket]['closed_at'] = datetime.now().isoformat()

                        # نقل إلى السجل
                        self.trade_history.append(self.active_positions[ticket])
                        del self.active_positions[ticket]
                        self.save_trades()
                return

            position = position[0]
            signal = Signal(**trade_info['signal'])

            # الحصول على السعر الحالي
            current_price = position.price_current
            entry_price = trade_info['entry_price']
            current_tp_index = trade_info['current_tp_index']

            # التحقق من الوصول إلى TP
            if signal.action == 'BUY':
                # للشراء: نتحقق إذا وصل السعر إلى TP التالي
                if current_tp_index < len(signal.take_profits):
                    next_tp = signal.take_profits[current_tp_index]

                    if current_price >= next_tp:
                        # وصلنا إلى TP جديد
                        print(f"🎯 الصفقة {ticket}: تم تحقيق TP{current_tp_index + 1} عند {next_tp}")

                        # حساب SL الجديد
                        new_sl = self._calculate_new_sl(
                            signal, current_tp_index, entry_price
                        )

                        # تحديث الـ index حتى لو لم نحرك SL
                        with self.lock:
                            trade_info['current_tp_index'] = current_tp_index + 1
                            self.save_trades()

                        # تحريك SL إذا كان هناك قيمة جديدة
                        if new_sl and new_sl != position.sl:
                            if self._modify_position(ticket, position.sl, new_sl, position.tp):
                                print(f"📈 تم تحريك SL للصفقة {ticket} من {position.sl:.5f} إلى {new_sl:.5f}")
                            else:
                                print(f"⚠️ فشل تحريك SL للصفقة {ticket}")

            else:  # SELL
                # للبيع: نتحقق إذا انخفض السعر إلى TP التالي
                if current_tp_index < len(signal.take_profits):
                    next_tp = signal.take_profits[current_tp_index]

                    if current_price <= next_tp:
                        # وصلنا إلى TP جديد
                        print(f"🎯 الصفقة {ticket}: تم تحقيق TP{current_tp_index + 1} عند {next_tp}")

                        # حساب SL الجديد
                        new_sl = self._calculate_new_sl(
                            signal, current_tp_index, entry_price
                        )

                        # تحديث الـ index حتى لو لم نحرك SL
                        with self.lock:
                            trade_info['current_tp_index'] = current_tp_index + 1
                            self.save_trades()

                        # تحريك SL إذا كان هناك قيمة جديدة
                        if new_sl and new_sl != position.sl:
                            if self._modify_position(ticket, position.sl, new_sl, position.tp):
                                print(f"📉 تم تحريك SL للصفقة {ticket} من {position.sl:.5f} إلى {new_sl:.5f}")
                            else:
                                print(f"⚠️ فشل تحريك SL للصفقة {ticket}")

        except Exception as e:
            print(f"❌ خطأ في تحديث trailing stop: {str(e)}")

    def _calculate_new_sl(self, signal: Signal, current_tp_index: int, entry_price: float) -> Optional[float]:
        """
        حساب SL الجديد بعد الوصول إلى TP

        القواعد:
        - TP1: نحرك SL إلى نقطة الدخول + السبريد
        - TP2: لا نحرك SL (نتركه عند نقطة الدخول)
        - TP3: نحرك SL إلى TP1
        - TP4: نحرك SL إلى TP2
        - TP5: نحرك SL إلى TP3
        وهكذا...
        """
        # الحصول على معلومات الرمز لحساب السبريد
        symbol_info = mt5.symbol_info(signal.symbol)
        spread = 0
        if symbol_info:
            # حساب السبريد بالنقاط
            spread = symbol_info.spread * symbol_info.point

        if current_tp_index == 0:
            # عند الوصول إلى TP1: نحرك SL إلى نقطة الدخول + السبريد
            if signal.action == 'BUY':
                new_sl = entry_price + spread
            else:  # SELL
                new_sl = entry_price - spread

            print(f"📊 TP1 تم تحقيقه - تحريك SL إلى نقطة الدخول + السبريد: {new_sl:.5f}")
            return new_sl

        elif current_tp_index == 1:
            # عند الوصول إلى TP2: لا نحرك SL (نتركه عند نقطة الدخول)
            print(f"📊 TP2 تم تحقيقه - SL يبقى عند نقطة الدخول")
            return None  # عدم التعديل

        elif current_tp_index >= 2 and current_tp_index < len(signal.take_profits):
            # من TP3 فصاعداً: نحرك SL إلى TP السابق بمقدار 2
            # TP3 → SL إلى TP1
            # TP4 → SL إلى TP2
            # TP5 → SL إلى TP3
            target_tp_index = current_tp_index - 2
            new_sl = signal.take_profits[target_tp_index]

            print(f"📊 TP{current_tp_index + 1} تم تحقيقه - تحريك SL إلى TP{target_tp_index + 1}: {new_sl:.5f}")
            return new_sl

        else:
            # وصلنا إلى آخر TP
            print(f"🎯 تم تحقيق جميع الأهداف!")
            return None

    def _modify_position(self, ticket: int, old_sl: float, new_sl: float, tp: float) -> bool:
        """تعديل SL/TP لصفقة"""
        try:
            position = mt5.positions_get(ticket=ticket)
            if not position or len(position) == 0:
                return False

            position = position[0]

            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": ticket,
                "symbol": position.symbol,
                "sl": new_sl,
                "tp": tp,
                "magic": 234000,
            }

            result = mt5.order_send(request)

            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                return True
            else:
                print(f"⚠️ فشل تعديل الصفقة: {result.comment if result else 'Unknown error'}")
                return False

        except Exception as e:
            print(f"❌ خطأ في تعديل الصفقة: {str(e)}")
            return False

    def get_open_positions(self) -> List[Dict]:
        """الحصول على الصفقات المفتوحة"""
        try:
            positions = mt5.positions_get()
            if positions is None:
                return []

            result = []
            for pos in positions:
                result.append({
                    'ticket': pos.ticket,
                    'symbol': pos.symbol,
                    'type': 'BUY' if pos.type == 0 else 'SELL',
                    'volume': pos.volume,
                    'price_open': pos.price_open,
                    'price_current': pos.price_current,
                    'sl': pos.sl,
                    'tp': pos.tp,
                    'profit': pos.profit,
                    'time': pos.time
                })

            return result

        except Exception as e:
            print(f"❌ خطأ في الحصول على الصفقات: {str(e)}")
            return []

    def get_account_info(self) -> Optional[Dict]:
        """الحصول على معلومات الحساب"""
        if not self.is_connected:
            return None

        try:
            info = mt5.account_info()
            if info is None:
                return None

            return {
                'login': info.login,
                'balance': info.balance,
                'equity': info.equity,
                'margin': info.margin,
                'free_margin': info.margin_free,
                'profit': info.profit,
                'leverage': info.leverage
            }

        except Exception as e:
            print(f"❌ خطأ في الحصول على معلومات الحساب: {str(e)}")
            return None

    def get_today_statistics(self) -> Dict:
        """إحصائيات تداول اليوم"""
        try:
            from datetime import datetime, timedelta

            # الحصول على صفقات اليوم
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            deals = mt5.history_deals_get(today, datetime.now())

            if deals is None or len(deals) == 0:
                return {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'total_profit': 0.0,
                    'win_rate': 0.0
                }

            total_profit = 0.0
            winning = 0
            losing = 0

            for deal in deals:
                if deal.profit != 0:
                    total_profit += deal.profit
                    if deal.profit > 0:
                        winning += 1
                    else:
                        losing += 1

            total = winning + losing
            win_rate = (winning / total * 100) if total > 0 else 0

            return {
                'total_trades': total,
                'winning_trades': winning,
                'losing_trades': losing,
                'total_profit': total_profit,
                'win_rate': win_rate
            }

        except Exception as e:
            print(f"❌ خطأ في الحصول على الإحصائيات: {str(e)}")
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'total_profit': 0.0,
                'win_rate': 0.0
            }

    def save_trades(self):
        """حفظ الصفقات إلى ملف"""
        try:
            data = {
                'active_positions': self.active_positions,
                'trade_history': self.trade_history
            }
            with open(self.trades_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"❌ خطأ في حفظ الصفقات: {str(e)}")

    def load_trades(self):
        """تحميل الصفقات من الملف"""
        try:
            if os.path.exists(self.trades_file):
                with open(self.trades_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.active_positions = data.get('active_positions', {})
                    self.trade_history = data.get('trade_history', [])
        except Exception as e:
            print(f"❌ خطأ في تحميل الصفقات: {str(e)}")

    def get_connection_status(self) -> Dict:
        """الحصول على حالة الاتصال"""
        return {
            'connected': self.is_connected,
            'account': self.account_info.login if self.account_info else None,
            'balance': self.account_info.balance if self.account_info else 0,
            'open_positions': len(self.active_positions)
        }
