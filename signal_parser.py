import re
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Signal:
    symbol: str
    action: str  # BUY or SELL
    entry_price: Optional[float] = None
    entry_price_range: Optional[Tuple[float, float]] = None  # للدخول بنطاق
    take_profits: List[float] = None
    stop_loss: Optional[float] = None
    timestamp: str = None
    channel_name: str = None
    raw_message: str = None
    status: str = "pending"  # pending, executed, failed
    order_type: str = "MARKET"  # MARKET, BUY_LIMIT, SELL_LIMIT, BUY_STOP, SELL_STOP

    def __post_init__(self):
        if self.take_profits is None:
            self.take_profits = []
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

class SignalParser:
    def __init__(self):
        # قائمة رموز الأصول الشائعة
        self.symbols = [
            # الذهب
            'XAUUSD', 'GOLD', 'XAUUSD_GOLD', 'XAU',
            # الفضة
            'XAGUSD', 'SILVER', 'XAG',
            # العملات الرئيسية
            'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD',
            # العملات المتقاطعة
            'EURJPY', 'GBPJPY', 'EURGBP', 'AUDJPY', 'NZDJPY', 'CADJPY',
            'EURAUD', 'EURCHF', 'GBPAUD', 'GBPCHF',
            # العملات الرقمية
            'BTCUSD', 'ETHUSD', 'XRPUSD', 'LTCUSD', 'BCHUSD', 'ADAUSD',
            'BTC', 'ETH', 'XRP', 'LTC',
            # المؤشرات
            'US30', 'US100', 'US500', 'NAS100', 'NASDAQ', 'SPX500', 'DJI30',
            'GER30', 'UK100', 'JPN225',
            # النفط
            'OIL', 'USOIL', 'UKOIL', 'CRUDE', 'WTI', 'BRENT'
        ]

        # أنماط مخصصة يمكن للمستخدم إضافتها
        self.custom_patterns = []

    def normalize_symbol(self, symbol: str) -> str:
        """توحيد رمز الأصل"""
        symbol = symbol.upper().strip()

        # تحويل الرموز المختلفة لنفس الأصل
        if 'GOLD' in symbol or 'XAU' in symbol:
            return 'XAUUSD'
        elif 'BTC' in symbol:
            return 'BTCUSD'

        # إزالة الرموز الخاصة
        symbol = re.sub(r'[#🔵_-]', '', symbol)

        return symbol

    def extract_symbol(self, text: str) -> Optional[str]:
        """استخراج رمز الأصل من النص"""
        text_upper = text.upper()

        # إزالة الرموز الخاصة من النص للبحث
        cleaned_text = re.sub(r'[#@_\-]', ' ', text_upper)

        for symbol in self.symbols:
            # البحث عن الرمز في النص (مع وبدون رموز خاصة)
            pattern = r'\b' + re.escape(symbol) + r'\b'
            if re.search(pattern, text_upper) or re.search(pattern, cleaned_text):
                return self.normalize_symbol(symbol)

            # البحث عن الرمز حتى لو كان ملتصقاً بكلمات أخرى
            # مثل: #XAUUSD_SELL أو XAUUSD_BUY
            if symbol in text_upper or symbol in cleaned_text:
                return self.normalize_symbol(symbol)

        # محاولة إيجاد أنماط عامة مثل XXXYYY
        currency_pattern = r'([A-Z]{6,7})'
        matches = re.findall(currency_pattern, cleaned_text)
        if matches:
            for match in matches:
                # تحقق أن الكلمة ليست BUY أو SELL
                if match not in ['BUY', 'SELL', 'BUYING', 'SELLING']:
                    return self.normalize_symbol(match)

        return None

    def extract_action(self, text: str) -> Tuple[Optional[str], str]:
        """استخراج نوع الصفقة ونوع الأمر (شراء/بيع + فوري/معلق)
        
        Returns:
            Tuple[Optional[str], str]: (action, order_type)
            - action: 'BUY' أو 'SELL'
            - order_type: 'MARKET', 'BUY_LIMIT', 'SELL_LIMIT', 'BUY_STOP', 'SELL_STOP'
        """
        text_upper = text.upper()

        # أنماط الأوامر المعلقة (مرتبة حسب الأولوية - الأطول أولاً)
        # استخدام أنماط محددة جداً لتجنب التطابق مع SL/TP
        if re.search(r'\bBUY\s+LIMIT\b', text_upper):
            return 'BUY', 'BUY_LIMIT'
        elif re.search(r'\bSELL\s+LIMIT\b', text_upper):
            return 'SELL', 'SELL_LIMIT'
        elif re.search(r'\bBUY\s+STOP\b', text_upper):
            return 'BUY', 'BUY_STOP'
        elif re.search(r'\bSELL\s+STOP\b', text_upper):
            return 'SELL', 'SELL_STOP'

        # أنماط الشراء الفوري
        buy_patterns = [
            r'\bBUY\b', r'\bLONG\b', r'\bCALL\b', r'\bBUYING\b',
            r'🟢', r'⬆️', r'📈', r'🔼'
        ]

        # أنماط البيع الفوري
        sell_patterns = [
            r'\bSELL\b', r'\bSHORT\b', r'\bPUT\b', r'\bSELLING\b',
            r'🔴', r'⬇️', r'📉', r'🔽'
        ]

        for pattern in buy_patterns:
            if re.search(pattern, text_upper) or pattern in text:
                return 'BUY', 'MARKET'

        for pattern in sell_patterns:
            if re.search(pattern, text_upper) or pattern in text:
                return 'SELL', 'MARKET'

        return None, 'MARKET'

    def extract_numbers(self, text: str) -> List[float]:
        """استخراج جميع الأرقام من النص"""
        # نمط لاستخراج الأرقام (بما في ذلك الفاصلة العشرية)
        pattern = r'(\d+[\.,]?\d*)'
        matches = re.findall(pattern, text)

        numbers = []
        for match in matches:
            try:
                # تحويل الفاصلة إلى نقطة
                num = float(match.replace(',', ''))
                numbers.append(num)
            except ValueError:
                continue

        return numbers

    def filter_valid_prices(self, numbers: List[float], symbol: str) -> List[float]:
        """تصفية الأسعار المنطقية فقط حسب نوع الأصل"""
        if not numbers:
            return []

        valid_prices = []

        for num in numbers:
            # تجاهل النسب المئوية والأرقام الصغيرة جداً
            if num <= 100:
                continue

            # تصفية حسب نوع الأصل
            if symbol in ['XAUUSD', 'GOLD', 'XAU']:
                # الذهب عادة بين 1000-10000
                if 1000 <= num <= 10000:
                    valid_prices.append(num)
            elif symbol in ['BTCUSD', 'BTC']:
                # البيتكوين عادة بين 1000-200000
                if 1000 <= num <= 200000:
                    valid_prices.append(num)
            elif symbol in ['EURUSD', 'GBPUSD', 'AUDUSD', 'NZDUSD']:
                # العملات الرئيسية عادة بين 0.5-2.0
                if 0.5 <= num <= 2.0:
                    valid_prices.append(num)
            elif symbol in ['USDJPY', 'EURJPY', 'GBPJPY']:
                # الين الياباني بين 50-200
                if 50 <= num <= 200:
                    valid_prices.append(num)
            elif symbol in ['US30', 'NAS100', 'US100', 'SPX500']:
                # المؤشرات
                if 1000 <= num <= 50000:
                    valid_prices.append(num)
            elif symbol in ['OIL', 'USOIL', 'UKOIL', 'WTI', 'BRENT']:
                # النفط بين 20-200
                if 20 <= num <= 200:
                    valid_prices.append(num)
            else:
                # أصول أخرى: نقبل أي رقم معقول > 100
                if num > 100:
                    valid_prices.append(num)

        return valid_prices

    def extract_entry_price(self, text: str, symbol: str) -> Tuple[Optional[float], Optional[Tuple[float, float]]]:
        """استخراج سعر الدخول (قد يكون سعر واحد أو نطاق)"""
        lines = text.split('\n')

        # البحث عن سعر الدخول في السطر الأول أو بعد NOW/Price
        for line in lines[:3]:  # نبحث في أول 3 أسطر
            line_upper = line.upper()

            # نمط: SYMBOL ACTION NOW PRICE
            if 'NOW' in line_upper or 'PRICE' in line_upper or '@' in line:
                numbers = self.extract_numbers(line)

                if len(numbers) == 1:
                    return numbers[0], None
                elif len(numbers) == 2:
                    # نطاق دخول (مثل: 3333-3330 أو 3333 - 3330)
                    return None, (min(numbers), max(numbers))

        # إذا لم نجد "NOW"، نبحث عن رقم بعد نوع الصفقة مباشرة
        all_numbers = self.extract_numbers(text)
        if all_numbers:
            return all_numbers[0], None

        return None, None

    def extract_take_profits(self, text: str, symbol: str) -> List[float]:
        """استخراج جميع مستويات أخذ الربح"""
        take_profits = []
        lines = text.split('\n')

        for line in lines:
            line_upper = line.upper()

            # تجاهل السطور التي تحتوي على نسب مئوية أو كلمات غير متعلقة بـ TP
            if '%' in line or 'SURE' in line_upper or 'SIGNAL' in line_upper:
                continue

            # تجاهل السطور التي تحتوي على SL
            if 'SL' in line_upper and 'TP' not in line_upper:
                continue

            # البحث عن أنماط TP المختلفة
            tp_patterns = [
                'TP', 'TAKE PROFIT', 'TARGET', 'T.P', 'PROFIT',
                'TAKE-PROFIT', 'TAKEPROFIT', 'T P', 'TP:', 'TP-',
                'OBJETIVO', 'GOAL'  # دعم لغات أخرى (أزلنا التكرار)
            ]

            # البحث عن TP في السطر
            has_tp = any(pattern in line_upper for pattern in tp_patterns)

            if has_tp:
                numbers = self.extract_numbers(line)
                # تصفية الأرقام المنطقية فقط
                valid_numbers = self.filter_valid_prices(numbers, symbol)

                if valid_numbers:
                    # نأخذ آخر رقم صالح في السطر (عادة هو السعر)
                    take_profits.append(valid_numbers[-1])

        # إذا لم نجد TP بالطريقة التقليدية، نبحث عن أنماط رقمية
        if not take_profits:
            # نبحث عن أرقام متتالية قد تكون أهداف
            all_numbers = self.extract_numbers(text)
            valid_numbers = self.filter_valid_prices(all_numbers, symbol)

            if len(valid_numbers) >= 3:  # على الأقل: دخول، tp، sl
                # نأخذ الأرقام الوسطى كأهداف محتملة
                potential_tps = valid_numbers[1:-1]  # كل الأرقام ما عدا الأول والأخير
                if potential_tps:
                    take_profits = sorted(potential_tps)

        return sorted(take_profits) if take_profits else []

    def extract_stop_loss(self, text: str, symbol: str) -> Optional[float]:
        """استخراج وقف الخسارة"""
        lines = text.split('\n')

        for line in lines:
            line_upper = line.upper()

            # تجاهل السطور التي تحتوي على نسب مئوية
            if '%' in line or 'SURE' in line_upper or 'SIGNAL' in line_upper:
                continue

            # تجاهل السطور التي تحتوي على TP فقط بدون SL
            if 'TP' in line_upper and not any(sl in line_upper for sl in ['SL', 'STOP']):
                continue

            # البحث عن أنماط SL المختلفة
            sl_patterns = [
                r'\bSL\b', r'\bSTOP\sLOSS\b', r'\bSTOP\b', r'\bS\.L\b', r'\bSTOPLOSS\b',
                r'\bSTOP-LOSS\b', r'\bS\sL\b', r'\bSL:', r'\bSL-', r'\bSTOP:',
            ]

            # البحث باستخدام regex لتجنب التطابقات الخاطئة
            has_sl = any(re.search(pattern, line_upper) for pattern in sl_patterns)

            if has_sl:
                # استخراج الأرقام من السطر
                numbers = self.extract_numbers(line)
                valid_numbers = self.filter_valid_prices(numbers, symbol)

                if valid_numbers:
                    # نأخذ آخر رقم صالح (عادة يكون SL)
                    return valid_numbers[-1]

        # إذا لم نجد SL بالطريقة التقليدية
        # نأخذ آخر رقم صالح في الرسالة (عادة يكون SL)
        all_numbers = self.extract_numbers(text)
        valid_numbers = self.filter_valid_prices(all_numbers, symbol)

        if len(valid_numbers) >= 2:
            return valid_numbers[-1]  # آخر رقم صالح

        return None

    def parse(self, message_text: str, channel_name: str = None) -> Optional[Signal]:
        """تحليل رسالة التليجرام واستخراج الإشارة - محسّن"""
        try:
            # استخراج المكونات الأساسية
            symbol = self.extract_symbol(message_text)
            if not symbol:
                return None  # يجب أن يكون هناك رمز على الأقل

            action, order_type = self.extract_action(message_text)
            if not action:
                return None  # يجب أن يكون هناك نوع صفقة

            entry_price, entry_range = self.extract_entry_price(message_text, symbol)
            take_profits = self.extract_take_profits(message_text, symbol)
            stop_loss = self.extract_stop_loss(message_text, symbol)

            # التحقق الصارم من المتطلبات الأساسية
            if not take_profits:
                return None

            if not stop_loss:
                return None

            if not (entry_price or entry_range):
                return None

            # تحديد سعر المرجع
            reference_price = entry_price if entry_price else sum(entry_range) / 2
            
            # تصفية TPs لإزالة TPs غير المنطقية
            if action == 'BUY':
                # في BUY: نبقي TPs >= Entry فقط
                filtered_tps = [tp for tp in take_profits if tp >= reference_price]
                # إذا كان أول TP يساوي Entry، نحتفظ به كنقطة تأكيد
                if filtered_tps and filtered_tps[0] == reference_price:
                    # نبحث عن TPs أعلى
                    higher_tps = [tp for tp in take_profits if tp > reference_price]
                    if higher_tps:
                        # نستخدم TPs الأعلى فقط
                        filtered_tps = sorted(higher_tps)
                take_profits = filtered_tps
            else:  # SELL
                # في SELL: نبقي TPs <= Entry فقط
                filtered_tps = [tp for tp in take_profits if tp <= reference_price]
                if filtered_tps and filtered_tps[0] == reference_price:
                    # نبحث عن TPs أقل
                    lower_tps = [tp for tp in take_profits if tp < reference_price]
                    if lower_tps:
                        # نستخدم TPs الأقل فقط
                        filtered_tps = sorted(lower_tps, reverse=True)
                take_profits = filtered_tps
            
            # التأكد من وجود TPs بعد التصفية
            if not take_profits:
                print(f"⚠️ لا توجد TPs صالحة بعد التصفية للإشارة {symbol} {action}")
                return None

            # التحقق الصارم من صحة البيانات
            if not self.validate_signal_data(symbol, action, entry_price, entry_range,
                                            take_profits, stop_loss):
                return None

            # إنشاء كائن الإشارة
            signal = Signal(
                symbol=symbol,
                action=action,
                entry_price=entry_price,
                entry_price_range=entry_range,
                take_profits=take_profits,
                stop_loss=stop_loss,
                channel_name=channel_name,
                raw_message=message_text,
                order_type=order_type  # إضافة نوع الأمر
            )

            return signal

        except Exception as e:
            # يمكن الاحتفاظ بهذا print للتطوير فقط
            import traceback
            traceback.print_exc()
            return None

    def validate_signal_data(self, symbol: str, action: str, entry_price: Optional[float],
                           entry_range: Optional[Tuple[float, float]],
                           take_profits: List[float], stop_loss: float) -> bool:
        """التحقق من صحة بيانات الإشارة - محسّن"""

        # يجب أن يكون هناك سعر دخول أو نطاق دخول
        if not entry_price and not entry_range:
            return False

        # يجب أن يكون هناك على الأقل TP واحد
        if not take_profits:
            return False

        # يجب أن يكون هناك SL
        if not stop_loss:
            return False

        # التحقق من منطقية الأسعار
        reference_price = entry_price if entry_price else sum(entry_range) / 2

        if action == 'BUY':
            # في الشراء: TP يجب أن يكون أعلى من أو يساوي سعر الدخول، SL أقل
            # نسمح بـ TP = Entry (بعض الإشارات تستخدم Entry كأول TP)
            if not all(tp >= reference_price for tp in take_profits):
                print(f"⚠️ تحذير: بعض TPs أقل من سعر الدخول في صفقة BUY")
                # نقوم بتصفية TPs الصحيحة فقط
                valid_tps = [tp for tp in take_profits if tp >= reference_price]
                if not valid_tps:
                    return False
            
            if stop_loss >= reference_price:
                print(f"⚠️ SL ({stop_loss}) يجب أن يكون أقل من Entry ({reference_price}) في BUY")
                return False
                
        else:  # SELL
            # في البيع: TP يجب أن يكون أقل من أو يساوي سعر الدخول، SL أعلى
            if not all(tp <= reference_price for tp in take_profits):
                print(f"⚠️ تحذير: بعض TPs أعلى من سعر الدخول في صفقة SELL")
                # نقوم بتصفية TPs الصحيحة فقط
                valid_tps = [tp for tp in take_profits if tp <= reference_price]
                if not valid_tps:
                    return False
            
            if stop_loss <= reference_price:
                print(f"⚠️ SL ({stop_loss}) يجب أن يكون أعلى من Entry ({reference_price}) في SELL")
                return False

        return True

    def add_custom_pattern(self, pattern: Dict):
        """إضافة نمط مخصص للتحليل"""
        self.custom_patterns.append(pattern)

    def test_parser(self):
        """اختبار المحلل على الأنماط المختلفة"""
        test_messages = [
            """BTCUSD buy NOW 117200
TP 117500
TP 117700
TP 117900
SL 116700""",

            """GOLD sell NOW 3343   - 45
TP 3340
TP 3337
TP 3333
SL 3351""",

            """🔵XAUUSD_GOLD BUY 3331
🔳TP : 3335.00
🔳TP : 3338.00
🔳TP : 3343.00
❌SL : 3321.000""",

            """XAUUSD BUY NOW
Price Open @ 3333- 3330
Take profit 1 🔼@ 3337
Take profit 2 🔼@ 3342
Take profit 3 🔼@ 3350
➕Stop loss @ 3325"""
        ]

        print("🧪 اختبار محلل الإشارات:\n")
        for i, msg in enumerate(test_messages, 1):
            print(f"--- اختبار {i} ---")
            signal = self.parse(msg, f"TestChannel{i}")
            if signal:
                print(f"✅ نجح: {signal.symbol} {signal.action}")
                print(f"   الدخول: {signal.entry_price or signal.entry_price_range}")
                print(f"   أخذ الربح: {signal.take_profits}")
                print(f"   وقف الخسارة: {signal.stop_loss}")
            else:
                print("❌ فشل التحليل")
            print()


if __name__ == "__main__":
    parser = SignalParser()
    parser.test_parser()
