# 🔧 إصلاح: الأوامر المعلقة مع السعر القريب
**التاريخ**: 22 أكتوبر 2025

---

## 🐛 المشكلة

عند استلام أمر معلق مثل:
```
Gold sell limit 

Entry 4078
Sl 4093
Tp 4068
Tp 4056
Tp 4046
```

كان البوت يرفض الأمر برسالة:
```
❌ فشل تنفيذ الصفقة: SELL LIMIT يجب أن يكون أعلى من السعر الحالي (4078.32)
```

### **السبب:**
- سعر الدخول: **4078.0**
- السعر الحالي: **4078.32**
- الفرق: **0.32 نقطة** فقط!

التحقق القديم كان صارماً جداً:
```python
if signal.order_type == 'SELL_LIMIT' and entry_price <= current_price:
    return {'success': False, 'error': '...'}
```

هذا يعني أن `4078.0 <= 4078.32` → `True` → رفض الأمر ❌

---

## ✅ الحل المطبق

### **1. إضافة هامش تسامح (Price Tolerance)**

```python
# حساب الفرق المسموح به (0.1% من السعر أو 20 نقطة، أيهما أكبر)
price_tolerance = max(entry_price * 0.001, symbol_info.point * 20)
```

**مثال للذهب (XAUUSD):**
- سعر الدخول: 4078
- الهامش: `max(4078 * 0.001, 0.1 * 20)` = `max(4.078, 2.0)` = **4.078 نقطة**

### **2. تحديث التحقق من الأسعار**

#### **قبل:**
```python
if signal.order_type == 'SELL_LIMIT' and entry_price <= current_price:
    return {'success': False, 'error': '...'}
```

#### **بعد:**
```python
if signal.order_type == 'SELL_LIMIT':
    if entry_price < current_price - price_tolerance:
        return {'success': False, 'error': '...'}
```

**النتيجة:**
```python
# سعر الدخول: 4078.0
# السعر الحالي: 4078.32
# الهامش: 4.08

# التحقق: 4078.0 < (4078.32 - 4.08)?
# التحقق: 4078.0 < 4074.24?
# النتيجة: False → ✅ مقبول!
```

---

## 📊 التحقق الجديد لجميع الأنواع

### **BUY LIMIT:**
```python
if entry_price > current_price + price_tolerance:
    return {'success': False, 'error': '...'}
```
- يسمح بفرق صغير فوق السعر الحالي
- مثال: إذا كان السعر الحالي 4078، يمكن وضع BUY LIMIT عند 4076-4082

### **SELL LIMIT:**
```python
if entry_price < current_price - price_tolerance:
    return {'success': False, 'error': '...'}
```
- يسمح بفرق صغير تحت السعر الحالي
- مثال: إذا كان السعر الحالي 4078، يمكن وضع SELL LIMIT عند 4074-4082

### **BUY STOP:**
```python
if entry_price < current_price - price_tolerance:
    return {'success': False, 'error': '...'}
```

### **SELL STOP:**
```python
if entry_price > current_price + price_tolerance:
    return {'success': False, 'error': '...'}
```

---

## 🔍 معلومات تشخيصية محسّنة

### **إضافة طباعة تفصيلية:**
```python
print(f"📊 معلومات الأمر المعلق:")
print(f"   الرمز: {actual_symbol}")
print(f"   النوع: {signal.order_type}")
print(f"   سعر الدخول: {entry_price}")
print(f"   السعر الحالي: {current_price}")
print(f"   الفرق: {abs(entry_price - current_price):.2f}")
```

### **تحسين رسائل الخطأ:**
```python
if result is None:
    last_error = mt5.last_error()
    error_msg = f'فشل إرسال الأمر المعلق: {last_error}'
    print(f"❌ {error_msg}")
    return {'success': False, 'error': error_msg}

if result.retcode != mt5.TRADE_RETCODE_DONE:
    error_msg = self._get_error_message(result.retcode, result.comment)
    print(f"❌ رمز الخطأ: {result.retcode} - {error_msg}")
    print(f"   التعليق: {result.comment}")
    # ...
```

---

## 🧪 الاختبار

### **الحالة الإشكالية:**
```
سعر الدخول: 4078.0
السعر الحالي: 4078.32
الفرق: 0.32 نقطة
```

### **قبل الإصلاح:**
```
❌ SELL LIMIT يجب أن يكون أعلى من السعر الحالي (4078.32)
```

### **بعد الإصلاح:**
```
✅ السعر مقبول - سيتم إرسال الأمر
⚠️ ملاحظة: السعر قريب جداً، قد يتم تنفيذه فوراً
```

---

## 💡 ملاحظات مهمة

### **1. السعر القريب جداً:**
إذا كان الفرق بين سعر الدخول والسعر الحالي أقل من الهامش:
- ✅ سيتم قبول الأمر
- ⚠️ قد يتم تنفيذه فوراً من MT5
- 🎯 هذا سلوك طبيعي ومقبول

### **2. الهامش الديناميكي:**
```python
price_tolerance = max(entry_price * 0.001, symbol_info.point * 20)
```
- **0.1%** من السعر (يتكيف مع الأصول المختلفة)
- **20 نقطة** كحد أدنى
- يعمل بشكل جيد للذهب، الفوركس، المؤشرات

### **3. MT5 Terminal:**
- إذا كان السعر قريب جداً، MT5 قد يحول الأمر لأمر فوري (MARKET)
- هذا سلوك طبيعي من MT5 وليس خطأ

---

## 📁 الملفات المعدلة

### **`mt5_manager.py`**
- ✅ إضافة `price_tolerance` ديناميكي
- ✅ تحديث التحقق من الأسعار لجميع الأنواع
- ✅ إضافة معلومات تشخيصية
- ✅ تحسين رسائل الخطأ

### **`test_close_price.py`** (جديد)
- ✅ اختبار الحالة الإشكالية
- ✅ محاكاة السعر القريب
- ✅ عرض تحليل تفصيلي

---

## 🎯 النتيجة

الآن يمكن وضع أوامر معلقة حتى لو كان السعر قريباً جداً من السعر الحالي:

```
Entry: 4078.0
Current: 4078.32
Difference: 0.32 points

قبل: ❌ رفض
بعد: ✅ قبول (مع تحذير)
```

**الفائدة:**
- ✅ مرونة أكثر في قبول الأوامر
- ✅ تقليل الرفض الخاطئ
- ✅ معلومات تشخيصية أفضل
- ✅ تجربة مستخدم محسّنة

---

## 🚀 الاستخدام

الآن يمكنك إرسال أوامر معلقة حتى لو كان السعر قريباً:

```
Gold sell limit

Entry 4078
Sl 4093
Tp 4068
Tp 4056
Tp 4046
```

**سيتم:**
1. ✅ التعرف على الإشارة
2. ✅ التحقق من السعر (مع هامش)
3. ✅ إرسال الأمر إلى MT5
4. 🎯 تنفيذه عند الوصول للسعر (أو فوراً إذا كان قريباً جداً)
