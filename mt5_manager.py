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
        
        # ملف حفظ خصائص الرموز
        self.symbols_info_file = 'data/symbols_info.json'

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

    def _enable_auto_trading(self) -> bool:
        """محاولة تفعيل التداول التلقائي بذكاء"""
        try:
            # للأسف، MT5 API لا يسمح بتفعيل التداول التلقائي برمجياً
            # ولكن يمكننا إعطاء تعليمات واضحة للمستخدم
            print("━" * 60)
            print("📢 تنبيه: التداول التلقائي معطل في MT5!")
            print("━" * 60)
            print("⚙️ لتفعيل التداول التلقائي، اتبع الخطوات التالية:")
            print("   1. افتح MT5 Terminal")
            print("   2. اذهب إلى: Tools → Options")
            print("   3. اختر تبويب Expert Advisors")
            print("   4. فعّل ✓ Allow automated trading")
            print("   5. فعّل ✓ Allow DLL imports (اختياري)")
            print("   6. اضغط OK")
            print("   7. تأكد من ظهور زر 'AutoTrading' أخضر في أعلى MT5")
            print("━" * 60)
            print("⏳ انتظر 10 ثوان للتفعيل...")
            print()
            
            # انتظار 10 ثوان للمستخدم
            for i in range(10, 0, -1):
                print(f"⏱️  {i} ثانية متبقية...", end='\r')
                time.sleep(1)
            print()
            
            # إعادة فحص
            terminal_info = mt5.terminal_info()
            if terminal_info and terminal_info.trade_allowed:
                print("✅ تم تفعيل التداول التلقائي بنجاح!")
                return True
            else:
                print("⚠️ التداول التلقائي لا يزال معطلاً")
                print("💡 يرجى التفعيل يدوياً ثم الضغط على 'إعادة المحاولة' في الواجهة")
                return False
                
        except Exception as e:
            print(f"❌ خطأ في فحص التداول التلقائي: {e}")
            return False

    def _get_error_message(self, error_code: int, original_message: str) -> str:
        """الحصول على رسالة خطأ واضحة بالعربية"""
        error_messages = {
            10004: "❌ خطأ في الخادم - يرجى المحاولة لاحقاً",
            10006: "❌ طلب مرفوض - تحقق من الاتصال",
            10007: "❌ طلب ملغى من قبل المتداول",
            10008: "❌ طلب موضوع بالفعل",
            10009: "❌ طلب معالج بالفعل",
            10010: "❌ طلب معالج جزئياً فقط",
            10011: "❌ خطأ في معالجة الطلب",
            10012: "❌ طلب ملغى بسبب timeout",
            10013: "❌ طلب غير صالح",
            10014: "❌ حجم تداول غير صالح",
            10015: "❌ سعر غير صالح",
            10016: "❌ stop levels غير صالح",
            10017: "❌ التداول معطل",
            10018: "❌ السوق مغلق",
            10019: "❌ لا توجد أموال كافية",
            10020: "❌ الأسعار تغيرت",
            10021: "❌ لا توجد أسعار",
            10022: "❌ طلب غير صالح",
            10023: "❌ الحجم غير صالح",
            10024: "❌ السعر غير صالح",
            10025: "❌ Stop Loss غير صالح",
            10026: "❌ Take Profit غير صالح",
            10027: "⚠️ التداول التلقائي معطل - يجب تفعيله من Tools → Options → Expert Advisors",
            10028: "❌ التداول التلقائي معطل من قبل الخادم",
            10029: "❌ طلب محظور - الحساب للقراءة فقط",
            10030: "❌ طلب محظور - التداول عبر الخبراء معطل",
            10031: "❌ الحد الأقصى للصفقات المفتوحة",
        }
        
        return error_messages.get(error_code, f"❌ خطأ {error_code}: {original_message}")

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

    def validate_trade_conditions(self, symbol: str, action: str, lot_size: float, 
                                  entry_price: Optional[float], stop_loss: Optional[float], 
                                  take_profit: Optional[float], order_type: str = "MARKET") -> Dict:
        """
        التحقق الشامل من شروط التداول قبل تنفيذ الصفقة
        
        Returns:
            Dict مع 'valid': bool و 'errors': List[str] و 'warnings': List[str]
        """
        errors = []
        warnings = []
        
        try:
            # 1. التحقق من وجود الرمز
            actual_symbol = self.find_symbol_in_platform(symbol)
            if not actual_symbol:
                errors.append(f"❌ الرمز {symbol} غير موجود في المنصة")
                return {'valid': False, 'errors': errors, 'warnings': warnings}
            
            # 2. الحصول على معلومات الرمز
            symbol_info = mt5.symbol_info(actual_symbol)
            if symbol_info is None:
                errors.append(f"❌ فشل الحصول على معلومات الرمز {actual_symbol}")
                return {'valid': False, 'errors': errors, 'warnings': warnings}
            
            # 3. التحقق من أن التداول مسموح
            if not symbol_info.trade_allowed:
                errors.append(f"❌ التداول غير مسموح على الرمز {actual_symbol}")
                errors.append("   السبب المحتمل: السوق مغلق أو الرمز معطل")
            
            # 4. التحقق من التداول عبر الخبراء
            if hasattr(symbol_info, 'trade_expert') and not symbol_info.trade_expert:
                errors.append(f"❌ التداول عبر الخبراء غير مسموح على {actual_symbol}")
                errors.append("   يجب تفعيل 'Allow Algo Trading' في إعدادات الرمز")
            
            # 5. التحقق من حجم الصفقة
            if lot_size < symbol_info.volume_min:
                errors.append(f"❌ حجم الصفقة ({lot_size}) أقل من الحد الأدنى ({symbol_info.volume_min})")
            elif lot_size > symbol_info.volume_max:
                errors.append(f"❌ حجم الصفقة ({lot_size}) أكبر من الحد الأقصى ({symbol_info.volume_max})")
            
            # التحقق من خطوة الحجم
            step = symbol_info.volume_step
            remainder = round((lot_size / step) - int(lot_size / step), 10)
            if remainder > 0.0001:  # هامش صغير للخطأ العشري
                correct_size = round(lot_size / step) * step
                warnings.append(f"⚠️ حجم الصفقة يجب أن يكون من مضاعفات {step}")
                warnings.append(f"   القيمة المقترحة: {correct_size}")
            
            # 6. الحصول على السعر الحالي
            tick = mt5.symbol_info_tick(actual_symbol)
            if tick is None:
                errors.append(f"❌ فشل الحصول على السعر الحالي للرمز {actual_symbol}")
                return {'valid': False, 'errors': errors, 'warnings': warnings}
            
            current_price = tick.ask if action == 'BUY' else tick.bid
            
            # 7. التحقق من Stop Level (المسافة الدنيا للـ SL/TP)
            stops_level = symbol_info.trade_stops_level
            point = symbol_info.point
            min_distance = stops_level * point
            
            if stops_level > 0:
                # تحديد سعر المرجع
                if order_type == "MARKET":
                    reference_price = current_price
                elif entry_price:
                    reference_price = entry_price
                else:
                    reference_price = current_price
                
                # التحقق من SL
                if stop_loss:
                    sl_distance = abs(reference_price - stop_loss)
                    if sl_distance < min_distance:
                        errors.append(f"❌ المسافة بين Entry و SL ({sl_distance:.5f}) أقل من الحد الأدنى ({min_distance:.5f})")
                        errors.append(f"   Stop Level: {stops_level} نقطة")
                        suggested_sl = reference_price - (min_distance * 1.5) if action == 'BUY' else reference_price + (min_distance * 1.5)
                        warnings.append(f"💡 SL مقترح: {suggested_sl:.5f}")
                
                # التحقق من TP
                if take_profit:
                    tp_distance = abs(reference_price - take_profit)
                    if tp_distance < min_distance:
                        errors.append(f"❌ المسافة بين Entry و TP ({tp_distance:.5f}) أقل من الحد الأدنى ({min_distance:.5f})")
                        errors.append(f"   Stop Level: {stops_level} نقطة")
                        suggested_tp = reference_price + (min_distance * 1.5) if action == 'BUY' else reference_price - (min_distance * 1.5)
                        warnings.append(f"💡 TP مقترح: {suggested_tp:.5f}")
            
            # 8. التحقق من اتجاه SL/TP
            if stop_loss and entry_price:
                if action == 'BUY' and stop_loss >= entry_price:
                    errors.append(f"❌ SL في صفقة BUY يجب أن يكون أقل من Entry")
                    errors.append(f"   Entry: {entry_price}, SL: {stop_loss}")
                elif action == 'SELL' and stop_loss <= entry_price:
                    errors.append(f"❌ SL في صفقة SELL يجب أن يكون أعلى من Entry")
                    errors.append(f"   Entry: {entry_price}, SL: {stop_loss}")
            
            if take_profit and entry_price:
                if action == 'BUY' and take_profit <= entry_price:
                    errors.append(f"❌ TP في صفقة BUY يجب أن يكون أعلى من Entry")
                    errors.append(f"   Entry: {entry_price}, TP: {take_profit}")
                elif action == 'SELL' and take_profit >= entry_price:
                    errors.append(f"❌ TP في صفقة SELL يجب أن يكون أقل من Entry")
                    errors.append(f"   Entry: {entry_price}, TP: {take_profit}")
            
            # 9. التحقق من الرؤية
            if not symbol_info.visible:
                warnings.append(f"⚠️ الرمز {actual_symbol} غير مرئي في Market Watch")
                warnings.append("   سيتم تفعيله تلقائياً")
            
            # 10. معلومات إضافية
            if symbol_info.spread > 100:
                warnings.append(f"⚠️ السبريد مرتفع: {symbol_info.spread} نقطة")
            
            # النتيجة النهائية
            is_valid = len(errors) == 0
            
            if is_valid and warnings:
                print("\n" + "="*60)
                print("✅ التحقق من شروط التداول: نجح")
                print("="*60)
                for warning in warnings:
                    print(warning)
                print("="*60 + "\n")
            elif not is_valid:
                print("\n" + "="*60)
                print("❌ التحقق من شروط التداول: فشل")
                print("="*60)
                for error in errors:
                    print(error)
                if warnings:
                    print("\n⚠️ تحذيرات:")
                    for warning in warnings:
                        print(warning)
                print("="*60 + "\n")
            
            return {
                'valid': is_valid,
                'errors': errors,
                'warnings': warnings,
                'symbol_info': symbol_info,
                'actual_symbol': actual_symbol,
                'current_price': current_price,
                'min_distance': min_distance
            }
            
        except Exception as e:
            errors.append(f"❌ خطأ في التحقق: {str(e)}")
            return {'valid': False, 'errors': errors, 'warnings': warnings}

    def execute_signal(self, signal: Signal, lot_size: float = 0.01) -> Dict:
        """تنفيذ إشارة تداول - مع دعم الأوامر المعلقة والفورية"""
        if not self.is_connected:
            return {'success': False, 'error': 'غير متصل بـ MT5'}

        # إذا كان أمر معلق، استخدم دالة place_pending_order
        if signal.order_type in ['BUY_LIMIT', 'SELL_LIMIT', 'BUY_STOP', 'SELL_STOP']:
            return self.place_pending_order(signal, lot_size)

        # الأوامر الفورية (MARKET)
        try:
            # ===== 1. فحص وتفعيل التداول التلقائي =====
            terminal_info = mt5.terminal_info()
            if terminal_info and not terminal_info.trade_allowed:
                print("⚠️ التداول التلقائي معطل - جاري التفعيل...")
                # محاولة تفعيل التداول التلقائي
                if not self._enable_auto_trading():
                    return {
                        'success': False,
                        'error': 'التداول التلقائي معطل في MT5',
                        'error_code': 10027,
                        'fix_required': True,
                        'fix_message': 'يرجى تفعيل التداول التلقائي يدوياً من: Tools -> Options -> Expert Advisors -> Allow automated trading'
                    }
            
            # ===== 2. تحديد سعر الدخول المتوقع =====
            if signal.entry_price:
                entry_price = signal.entry_price
            elif signal.entry_price_range:
                entry_price = sum(signal.entry_price_range) / 2
            else:
                entry_price = None  # سيتم تحديده من السعر الحالي
            
            # ===== 3. التحقق الشامل من شروط التداول =====
            validation = self.validate_trade_conditions(
                symbol=signal.symbol,
                action=signal.action,
                lot_size=lot_size,
                entry_price=entry_price,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profits[0] if signal.take_profits else None,
                order_type="MARKET"
            )
            
            if not validation['valid']:
                error_msg = "فشل التحقق من شروط التداول:\n" + "\n".join(validation['errors'])
                return {'success': False, 'error': error_msg, 'validation_errors': validation['errors']}
            
            # استخدام البيانات من التحقق
            actual_symbol = validation['actual_symbol']
            symbol_info = validation['symbol_info']
            
            # تفعيل الرمز إذا لم يكن مرئياً
            if not symbol_info.visible:
                if not mt5.symbol_select(actual_symbol, True):
                    return {'success': False, 'error': f'فشل تفعيل الرمز {actual_symbol}'}

            # ===== 4. تحديد نوع الأمر =====
            order_type = mt5.ORDER_TYPE_BUY if signal.action == 'BUY' else mt5.ORDER_TYPE_SELL

            # ===== 5. تحديد سعر الدخول =====
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

            # ===== 6. إعداد طلب التداول =====
            # تنظيف التعليق لتجنب محارف غير صالحة
            comment = f"Signal {signal.symbol}"
            comment = comment.encode('ascii', 'ignore').decode('ascii')[:31]  # MT5 يقبل max 31 حرف
            
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
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            # ===== 7. إرسال الطلب =====
            result = mt5.order_send(request)

            if result is None:
                return {'success': False, 'error': 'فشل إرسال الطلب'}

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                # التعامل الذكي مع أخطاء محددة
                error_msg = self._get_error_message(result.retcode, result.comment)
                return {
                    'success': False,
                    'error': error_msg,
                    'error_code': result.retcode,
                    'retcode': result.retcode
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

    def place_pending_order(self, signal: Signal, lot_size: float = 0.01) -> Dict:
        """وضع أمر معلق (Pending Order) - BUY_LIMIT, SELL_LIMIT, BUY_STOP, SELL_STOP"""
        if not self.is_connected:
            return {'success': False, 'error': 'غير متصل بـ MT5'}

        try:
            # ===== 1. فحص وتفعيل التداول التلقائي =====
            terminal_info = mt5.terminal_info()
            if terminal_info and not terminal_info.trade_allowed:
                print("⚠️ التداول التلقائي معطل - جاري التفعيل...")
                if not self._enable_auto_trading():
                    return {
                        'success': False,
                        'error': 'التداول التلقائي معطل في MT5',
                        'error_code': 10027,
                        'fix_required': True,
                        'fix_message': 'يرجى تفعيل التداول التلقائي يدوياً'
                    }
            
            # ===== 2. التحقق من سعر الدخول =====
            if not signal.entry_price:
                return {'success': False, 'error': 'الأوامر المعلقة تحتاج لسعر دخول محدد'}
            
            # ===== 3. التحقق الشامل من شروط التداول =====
            validation = self.validate_trade_conditions(
                symbol=signal.symbol,
                action=signal.action,
                lot_size=lot_size,
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profits[0] if signal.take_profits else None,
                order_type=signal.order_type
            )
            
            if not validation['valid']:
                error_msg = "فشل التحقق من شروط التداول:\n" + "\n".join(validation['errors'])
                return {'success': False, 'error': error_msg, 'validation_errors': validation['errors']}
            
            # استخدام البيانات من التحقق
            actual_symbol = validation['actual_symbol']
            symbol_info = validation['symbol_info']
            current_price = validation['current_price']
            
            # تفعيل الرمز إذا لم يكن مرئياً
            if not symbol_info.visible:
                if not mt5.symbol_select(actual_symbol, True):
                    return {'success': False, 'error': f'فشل تفعيل الرمز {actual_symbol}'}

            # ===== 4. تحديد نوع الأمر المعلق =====
            order_type_map = {
                'BUY_LIMIT': mt5.ORDER_TYPE_BUY_LIMIT,
                'SELL_LIMIT': mt5.ORDER_TYPE_SELL_LIMIT,
                'BUY_STOP': mt5.ORDER_TYPE_BUY_STOP,
                'SELL_STOP': mt5.ORDER_TYPE_SELL_STOP
            }
            
            order_type = order_type_map.get(signal.order_type)
            if order_type is None:
                return {'success': False, 'error': f'نوع أمر غير صحيح: {signal.order_type}'}

            # ===== 5. تحديد سعر الدخول =====
            entry_price = signal.entry_price
            
            # ===== 6. التحقق من منطقية السعر للأمر المعلق =====
            # حساب الفرق المسموح به (0.1% من السعر أو 20 نقطة، أيهما أكبر)
            price_tolerance = max(entry_price * 0.001, symbol_info.point * 20)
            
            # التحقق من أن السعر منطقي لنوع الأمر (مع هامش تسامح)
            if signal.order_type == 'BUY_LIMIT':
                if entry_price > current_price + price_tolerance:
                    return {'success': False, 'error': f'BUY LIMIT يجب أن يكون أقل من السعر الحالي ({current_price})'}
            elif signal.order_type == 'SELL_LIMIT':
                if entry_price < current_price - price_tolerance:
                    return {'success': False, 'error': f'SELL LIMIT يجب أن يكون أعلى من السعر الحالي ({current_price})'}
            elif signal.order_type == 'BUY_STOP':
                if entry_price < current_price - price_tolerance:
                    return {'success': False, 'error': f'BUY STOP يجب أن يكون أعلى من السعر الحالي ({current_price})'}
            elif signal.order_type == 'SELL_STOP':
                if entry_price > current_price + price_tolerance:
                    return {'success': False, 'error': f'SELL STOP يجب أن يكون أقل من السعر الحالي ({current_price})'}
            
            # ملاحظة: إذا كان السعر قريب جداً من السعر الحالي، سيتم تنفيذه كأمر فوري تلقائياً من MT5

            # طباعة معلومات تشخيصية
            print(f"📊 معلومات الأمر المعلق:")
            print(f"   الرمز: {actual_symbol}")
            print(f"   النوع: {signal.order_type}")
            print(f"   سعر الدخول: {entry_price}")
            print(f"   السعر الحالي: {current_price}")
            print(f"   الفرق: {abs(entry_price - current_price):.2f}")
            
            # معلومات Stop Level
            if validation['min_distance'] > 0:
                print(f"   Stop Level: {symbol_info.trade_stops_level} نقطة ({validation['min_distance']:.5f})")

            # ===== 7. إعداد طلب الأمر المعلق =====
            # تنظيف التعليق لتجنب محارف غير صالحة
            channel_safe = signal.channel_name if signal.channel_name else "Unknown"
            # إزالة المحارف الخاصة والعربية (MT5 يدعم ASCII فقط في comment)
            comment = f"Pending {signal.order_type} {signal.symbol}"
            comment = comment.encode('ascii', 'ignore').decode('ascii')[:31]  # MT5 يقبل max 31 حرف
            
            # تحديد نوع التعبئة المناسب
            filling_type = symbol_info.filling_mode
            if filling_type & 1:  # ORDER_FILLING_FOK
                type_filling = mt5.ORDER_FILLING_FOK
            elif filling_type & 2:  # ORDER_FILLING_IOC
                type_filling = mt5.ORDER_FILLING_IOC
            else:  # ORDER_FILLING_RETURN (default)
                type_filling = mt5.ORDER_FILLING_RETURN
            
            request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": actual_symbol,
                "volume": lot_size,
                "type": order_type,
                "price": entry_price,
                "sl": signal.stop_loss,
                "tp": signal.take_profits[0] if signal.take_profits else 0,
                "deviation": 20,
                "magic": 234000,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": type_filling,
            }

            # ===== 8. إرسال الطلب =====
            result = mt5.order_send(request)

            if result is None:
                last_error = mt5.last_error()
                error_msg = f'فشل إرسال الأمر المعلق: {last_error}'
                print(f"❌ {error_msg}")
                return {'success': False, 'error': error_msg}

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                error_msg = self._get_error_message(result.retcode, result.comment)
                print(f"❌ رمز الخطأ: {result.retcode} - {error_msg}")
                print(f"   التعليق: {result.comment}")
                return {
                    'success': False,
                    'error': error_msg,
                    'error_code': result.retcode,
                    'retcode': result.retcode
                }

            # ===== 9. حفظ معلومات الأمر المعلق =====
            order_info = {
                'ticket': result.order,
                'signal': signal.__dict__,
                'placed_at': datetime.now().isoformat(),
                'entry_price': entry_price,
                'lot_size': lot_size,
                'order_type': signal.order_type,
                'status': 'pending'
            }

            with self.lock:
                self.active_positions[result.order] = order_info
                self.save_trades()

            # عرض رسالة نجاح
            symbol_display = f"{signal.symbol} ({actual_symbol})" if actual_symbol != signal.symbol else signal.symbol
            print(f"✅ تم وضع أمر معلق {signal.order_type} على {symbol_display}")
            print(f"   التذكرة: {result.order}")
            print(f"   سعر الدخول: {entry_price}")
            print(f"   السعر الحالي: {current_price}")

            return {
                'success': True,
                'ticket': result.order,
                'entry_price': entry_price,
                'current_price': current_price,
                'actual_symbol': actual_symbol,
                'order_info': order_info
            }

        except Exception as e:
            print(f"❌ خطأ في وضع الأمر المعلق: {str(e)}")
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

    def get_symbol_properties(self, symbol: str, verbose: bool = True) -> Optional[Dict]:
        """
        الحصول على خصائص رمز معين من MT5
        
        Args:
            symbol: اسم الرمز (مثل XAUUSD)
            verbose: طباعة التفاصيل
            
        Returns:
            Dict مع جميع خصائص الرمز أو None
        """
        if not self.is_connected:
            print("❌ غير متصل بـ MT5")
            return None

        try:
            # البحث عن الرمز الفعلي في المنصة
            actual_symbol = self.find_symbol_in_platform(symbol)
            if not actual_symbol:
                print(f"❌ الرمز {symbol} غير موجود في المنصة")
                return None

            # الحصول على معلومات الرمز
            symbol_info = mt5.symbol_info(actual_symbol)
            if symbol_info is None:
                print(f"❌ فشل الحصول على معلومات الرمز {actual_symbol}")
                return None

            # تجهيز البيانات
            properties = {
                'symbol': actual_symbol,
                'original_symbol': symbol,
                'description': symbol_info.description if hasattr(symbol_info, 'description') else '',
                'path': symbol_info.path if hasattr(symbol_info, 'path') else '',
                'trade_allowed': symbol_info.trade_allowed,
                'trade_expert': symbol_info.trade_expert if hasattr(symbol_info, 'trade_expert') else False,
                'volume_min': symbol_info.volume_min,
                'volume_max': symbol_info.volume_max,
                'volume_step': symbol_info.volume_step,
                'digits': symbol_info.digits,
                'trade_stops_level': symbol_info.trade_stops_level,
                'spread': symbol_info.spread,
                'point': symbol_info.point,
                'tick_size': symbol_info.trade_tick_size,
                'tick_value': symbol_info.trade_tick_value,
                'contract_size': symbol_info.trade_contract_size,
                'currency_base': symbol_info.currency_base if hasattr(symbol_info, 'currency_base') else '',
                'currency_profit': symbol_info.currency_profit if hasattr(symbol_info, 'currency_profit') else '',
                'currency_margin': symbol_info.currency_margin if hasattr(symbol_info, 'currency_margin') else '',
                'margin_initial': symbol_info.margin_initial if hasattr(symbol_info, 'margin_initial') else 0,
                'margin_maintenance': symbol_info.margin_maintenance if hasattr(symbol_info, 'margin_maintenance') else 0,
                'filling_mode': symbol_info.filling_mode,
                'order_mode': symbol_info.order_mode,
                'visible': symbol_info.visible,
                'timestamp': datetime.now().isoformat()
            }

            # طباعة التقرير
            if verbose:
                print("\n" + "="*70)
                print(f"📊 تقرير خصائص الرمز: {actual_symbol}")
                print("="*70)
                
                if properties['description']:
                    print(f"📝 الوصف: {properties['description']}")
                
                print(f"\n🔧 إعدادات التداول:")
                print(f"   ✅ التداول مسموح: {'نعم' if properties['trade_allowed'] else '❌ لا'}")
                print(f"   🤖 التداول عبر الخبراء: {'نعم' if properties['trade_expert'] else '❌ لا'}")
                print(f"   👁️ الرمز مرئي: {'نعم' if properties['visible'] else '❌ لا'}")
                
                print(f"\n📏 أحجام الصفقات:")
                print(f"   الحد الأدنى: {properties['volume_min']} لوت")
                print(f"   الحد الأقصى: {properties['volume_max']} لوت")
                print(f"   خطوة الحجم: {properties['volume_step']} لوت")
                
                print(f"\n💰 معلومات السعر:")
                print(f"   عدد الأرقام العشرية: {properties['digits']}")
                print(f"   حجم النقطة (Point): {properties['point']}")
                print(f"   حجم الـ Tick: {properties['tick_size']}")
                print(f"   قيمة الـ Tick: {properties['tick_value']}")
                print(f"   حجم العقد: {properties['contract_size']}")
                
                print(f"\n📊 معلومات السوق:")
                print(f"   Spread الحالي: {properties['spread']} نقطة")
                print(f"   Stop Level: {properties['trade_stops_level']} نقطة")
                
                print(f"\n💵 العملات:")
                print(f"   عملة الأساس: {properties['currency_base']}")
                print(f"   عملة الربح: {properties['currency_profit']}")
                print(f"   عملة الهامش: {properties['currency_margin']}")
                
                if properties['margin_initial'] > 0:
                    print(f"\n💳 الهامش:")
                    print(f"   الهامش الأولي: {properties['margin_initial']}")
                    print(f"   هامش الصيانة: {properties['margin_maintenance']}")
                
                # معلومات أنواع التعبئة
                filling_modes = []
                if properties['filling_mode'] & 1:
                    filling_modes.append("FOK")
                if properties['filling_mode'] & 2:
                    filling_modes.append("IOC")
                if properties['filling_mode'] & 4:
                    filling_modes.append("RETURN")
                
                print(f"\n⚙️ أوضاع التعبئة المدعومة:")
                print(f"   {', '.join(filling_modes) if filling_modes else 'غير محدد'}")
                
                print("="*70 + "\n")

            return properties

        except Exception as e:
            print(f"❌ خطأ في الحصول على خصائص الرمز: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def save_symbol_properties(self, symbol: str) -> bool:
        """حفظ خصائص الرمز في ملف JSON"""
        try:
            properties = self.get_symbol_properties(symbol, verbose=False)
            if not properties:
                return False

            # قراءة الملف الحالي
            if os.path.exists(self.symbols_info_file):
                with open(self.symbols_info_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {}

            # إضافة/تحديث الرمز
            data[properties['symbol']] = properties

            # حفظ الملف
            with open(self.symbols_info_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

            print(f"✅ تم حفظ خصائص الرمز {symbol} في {self.symbols_info_file}")
            return True

        except Exception as e:
            print(f"❌ خطأ في حفظ خصائص الرمز: {str(e)}")
            return False

    def get_all_symbols_properties(self, save_to_file: bool = True) -> Dict:
        """
        الحصول على خصائص جميع الرموز المتاحة
        
        Args:
            save_to_file: حفظ في ملف JSON
            
        Returns:
            Dict مع خصائص جميع الرموز
        """
        if not self.is_connected:
            print("❌ غير متصل بـ MT5")
            return {}

        try:
            all_symbols = mt5.symbols_get()
            if not all_symbols:
                print("❌ لم يتم العثور على رموز")
                return {}

            print(f"🔍 جاري فحص {len(all_symbols)} رمز...")
            
            results = {}
            for symbol_info in all_symbols:
                symbol_name = symbol_info.name
                properties = self.get_symbol_properties(symbol_name, verbose=False)
                if properties:
                    results[symbol_name] = properties

            print(f"✅ تم الحصول على خصائص {len(results)} رمز")

            # حفظ في ملف
            if save_to_file:
                with open(self.symbols_info_file, 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False, indent=4)
                print(f"✅ تم حفظ البيانات في {self.symbols_info_file}")

            return results

        except Exception as e:
            print(f"❌ خطأ في الحصول على خصائص الرموز: {str(e)}")
            return {}

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
