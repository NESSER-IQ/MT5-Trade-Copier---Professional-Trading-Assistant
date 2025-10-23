# 📊 نظام فحص خصائص الرموز في MT5
**التاريخ**: 22 أكتوبر 2025

---

## ✨ الميزات الجديدة

تم إضافة نظام شامل للتحقق من خصائص الرموز في MT5 مع:
- ✅ فحص تلقائي لأي رمز
- ✅ عرض تفصيلي لجميع الخصائص
- ✅ حفظ البيانات في ملف JSON
- ✅ واجهة مستخدم مدمجة
- ✅ دعم فحص جميع الرموز دفعة واحدة

---

## 📋 الخصائص المفحوصة

### **1. إعدادات التداول**
- `trade_allowed` - التداول مسموح
- `trade_expert` - التداول عبر الخبراء مسموح
- `visible` - الرمز مرئي في Market Watch

### **2. أحجام الصفقات**
- `volume_min` - الحد الأدنى للصفقة (مثل 0.01 لوت)
- `volume_max` - الحد الأقصى للصفقة (مثل 100 لوت)
- `volume_step` - خطوة الحجم (مثل 0.01)

### **3. معلومات السعر**
- `digits` - عدد الأرقام العشرية (مثل 2 للذهب، 5 للفوركس)
- `point` - حجم النقطة (0.01 أو 0.00001)
- `tick_size` - حجم الـ Tick
- `tick_value` - قيمة الـ Tick
- `contract_size` - حجم العقد

### **4. معلومات السوق**
- `spread` - السبريد الحالي بالنقاط
- `trade_stops_level` - المسافة الدنيا للـ SL/TP

### **5. العملات**
- `currency_base` - عملة الأساس
- `currency_profit` - عملة الربح
- `currency_margin` - عملة الهامش

### **6. الهامش**
- `margin_initial` - الهامش الأولي
- `margin_maintenance` - هامش الصيانة

### **7. أوضاع التعبئة**
- `filling_mode` - الأنواع المدعومة (FOK, IOC, RETURN)

---

## 🔧 واجهة البرمجة (API)

### **1. فحص رمز واحد**
```python
from mt5_manager import MT5Manager

manager = MT5Manager()
manager.connect(login, password, server)

# فحص رمز مع طباعة التفاصيل
properties = manager.get_symbol_properties("XAUUSD", verbose=True)

# فحص رمز بدون طباعة
properties = manager.get_symbol_properties("EURUSD", verbose=False)

# النتيجة: Dict مع جميع الخصائص
print(properties['trade_allowed'])  # True/False
print(properties['volume_min'])     # 0.01
print(properties['digits'])          # 2
```

### **2. حفظ خصائص رمز**
```python
# حفظ في data/symbols_info.json
manager.save_symbol_properties("XAUUSD")
```

### **3. فحص جميع الرموز**
```python
# فحص جميع الرموز المتاحة وحفظها
all_properties = manager.get_all_symbols_properties(save_to_file=True)

# النتيجة: Dict[symbol_name, properties]
print(f"عدد الرموز: {len(all_properties)}")
```

---

## 🖥️ الواجهة الرسومية

### **تبويب جديد: "📊 خصائص الرموز"**

#### **المكونات:**
1. **حقل إدخال الرمز**
   - أدخل اسم الرمز (XAUUSD, EURUSD, إلخ)

2. **أزرار التحكم**
   - `🔍 فحص الرمز` - فحص الرمز المدخل
   - `💾 حفظ` - حفظ الخصائص في ملف
   - `📋 فحص جميع الرموز` - فحص كل الرموز المتاحة
   - `📂 فتح ملف الخصائص` - فتح الملف المحفوظ

3. **منطقة النتائج**
   - عرض تفصيلي لجميع خصائص الرمز
   - تنسيق واضح مع رموز تعبيرية
   - دعم النسخ

---

## 📄 مثال على التقرير

```
======================================================================
📊 تقرير خصائص الرمز: XAUUSD
======================================================================
📝 الوصف: Gold vs US Dollar

🔧 إعدادات التداول:
   ✅ التداول مسموح: نعم ✓
   🤖 التداول عبر الخبراء: نعم ✓
   👁️ الرمز مرئي: نعم ✓

📏 أحجام الصفقات:
   الحد الأدنى: 0.01 لوت
   الحد الأقصى: 100.0 لوت
   خطوة الحجم: 0.01 لوت

💰 معلومات السعر:
   عدد الأرقام العشرية: 2
   حجم النقطة (Point): 0.01
   حجم الـ Tick: 0.01
   قيمة الـ Tick: 1.0
   حجم العقد: 100.0

📊 معلومات السوق:
   Spread الحالي: 30 نقطة
   Stop Level: 0 نقطة

💵 العملات:
   عملة الأساس: XAU
   عملة الربح: USD
   عملة الهامش: USD

⚙️ أوضاع التعبئة المدعومة:
   FOK, IOC

⏰ وقت الفحص:
   2025-10-22T15:30:45.123456
======================================================================
```

---

## 📂 ملف الحفظ: `data/symbols_info.json`

### **الهيكل:**
```json
{
    "XAUUSD": {
        "symbol": "XAUUSD",
        "original_symbol": "XAUUSD",
        "description": "Gold vs US Dollar",
        "trade_allowed": true,
        "trade_expert": true,
        "volume_min": 0.01,
        "volume_max": 100.0,
        "volume_step": 0.01,
        "digits": 2,
        "trade_stops_level": 0,
        "spread": 30,
        "point": 0.01,
        "tick_size": 0.01,
        "tick_value": 1.0,
        "contract_size": 100.0,
        "currency_base": "XAU",
        "currency_profit": "USD",
        "currency_margin": "USD",
        "margin_initial": 0.0,
        "margin_maintenance": 0.0,
        "filling_mode": 3,
        "order_mode": 127,
        "visible": true,
        "timestamp": "2025-10-22T15:30:45.123456"
    },
    "EURUSD": {
        // ... خصائص EURUSD
    }
}
```

---

## 🧪 الاختبار

### **تشغيل الاختبار:**
```bash
python test_symbol_properties.py
```

### **الاختبارات المضمنة:**
1. ✅ فحص رمز واحد (XAUUSD) مع طباعة كاملة
2. ✅ فحص رموز متعددة (EURUSD, GBPUSD, USDJPY)
3. ✅ حفظ الخصائص في ملف
4. ✅ التحقق من وجود الملف وقراءته

---

## 💡 حالات الاستخدام

### **1. التحقق قبل التداول**
```python
# فحص إذا كان التداول مسموح
props = manager.get_symbol_properties("XAUUSD", verbose=False)
if props and props['trade_allowed']:
    print("✅ يمكن التداول")
else:
    print("❌ التداول غير مسموح")
```

### **2. حساب حجم اللوت المناسب**
```python
props = manager.get_symbol_properties("EURUSD", verbose=False)
if props:
    min_lot = props['volume_min']
    max_lot = props['volume_max']
    step = props['volume_step']
    
    # اختر حجم صحيح
    desired_lot = 0.15
    actual_lot = round(desired_lot / step) * step
    actual_lot = max(min_lot, min(actual_lot, max_lot))
```

### **3. التحقق من Stop Level**
```python
props = manager.get_symbol_properties("GBPUSD", verbose=False)
if props:
    stops_level = props['trade_stops_level']
    point = props['point']
    
    min_distance = stops_level * point
    print(f"المسافة الدنيا للـ SL/TP: {min_distance}")
```

### **4. معرفة أنواع التعبئة المدعومة**
```python
props = manager.get_symbol_properties("USDJPY", verbose=False)
if props:
    filling = props['filling_mode']
    
    if filling & 1:
        print("✅ يدعم FOK")
    if filling & 2:
        print("✅ يدعم IOC")
    if filling & 4:
        print("✅ يدعم RETURN")
```

---

## 📁 الملفات المضافة/المعدلة

### **1. `mt5_manager.py`**
- ✅ إضافة `symbols_info_file` في __init__
- ✅ دالة `get_symbol_properties()` - فحص رمز واحد
- ✅ دالة `save_symbol_properties()` - حفظ رمز
- ✅ دالة `get_all_symbols_properties()` - فحص جميع الرموز

### **2. `main_gui.py`**
- ✅ إضافة تبويب "📊 خصائص الرموز"
- ✅ دالة `build_symbols_tab()` - بناء الواجهة
- ✅ دالة `check_symbol_properties()` - فحص رمز
- ✅ دالة `save_current_symbol_properties()` - حفظ
- ✅ دالة `check_all_symbols()` - فحص الكل
- ✅ دالة `open_symbols_file()` - فتح الملف

### **3. `test_symbol_properties.py`** (جديد)
- ✅ اختبارات شاملة للنظام

### **4. `data/symbols_info.json`** (يُنشأ تلقائياً)
- ✅ ملف JSON لحفظ الخصائص

---

## 🎯 الفوائد

### **للمطور:**
- ✅ معرفة قيود الرمز قبل التداول
- ✅ تجنب الأخطاء الناتجة عن أحجام خاطئة
- ✅ معرفة أنواع الأوامر المدعومة
- ✅ حساب الهامش المطلوب

### **للتشخيص:**
- ✅ معرفة سبب رفض الأوامر
- ✅ التحقق من إعدادات الرمز
- ✅ مقارنة الرموز المختلفة
- ✅ توثيق إعدادات الحساب

### **للأتمتة:**
- ✅ اختيار type_filling المناسب تلقائياً
- ✅ التحقق من أحجام اللوت تلقائياً
- ✅ تطبيق Stop Level تلقائياً
- ✅ التكيف مع رموز مختلفة

---

## 🚀 الاستخدام السريع

### **من الواجهة:**
1. افتح التطبيق
2. اذهب لتبويب "📊 خصائص الرموز"
3. أدخل الرمز (مثل XAUUSD)
4. اضغط "🔍 فحص الرمز"
5. اضغط "💾 حفظ" لحفظ الخصائص

### **من الكود:**
```python
from mt5_manager import MT5Manager

manager = MT5Manager()
manager.auto_connect()

# فحص رمز
props = manager.get_symbol_properties("XAUUSD")

# حفظ
manager.save_symbol_properties("XAUUSD")

# فحص الكل
all_props = manager.get_all_symbols_properties()
```

---

## 🎉 الخلاصة

تم إضافة نظام شامل ومتكامل لفحص وتوثيق خصائص الرموز في MT5 مع:
- ✅ واجهة برمجية سهلة
- ✅ واجهة مستخدم بديهية
- ✅ حفظ تلقائي في JSON
- ✅ تقارير مفصلة
- ✅ اختبارات شاملة

**الآن يمكنك معرفة كل شيء عن أي رمز بضغطة زر!** 🚀
