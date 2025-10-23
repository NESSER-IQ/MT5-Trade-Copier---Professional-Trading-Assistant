# 🔧 إصلاح: Invalid "comment" argument
**التاريخ**: 22 أكتوبر 2025

---

## 🐛 المشكلة

عند محاولة وضع أمر معلق، كان يظهر الخطأ:
```
❌ فشل إرسال الأمر المعلق: (-2, 'Invalid "comment" argument')
```

### **السبب:**
```python
"comment": f"Pending: {signal.order_type} {signal.symbol} from {signal.channel_name}"
```

**المشاكل:**
1. `signal.channel_name` قد يحتوي على **محارف عربية**
2. MT5 يقبل **ASCII فقط** في حقل `comment`
3. MT5 يقبل **حد أقصى 31 حرف** في التعليق
4. إذا كان `channel_name` هو `None` → خطأ

---

## ✅ الحل المطبق

### **1. تنظيف التعليق من المحارف غير الصالحة**

```python
# تنظيف التعليق لتجنب محارف غير صالحة
comment = f"Pending {signal.order_type} {signal.symbol}"
comment = comment.encode('ascii', 'ignore').decode('ascii')[:31]
```

**كيف يعمل:**
```python
# مثال
comment = "Pending SELL_LIMIT XAUUSD from قناة عربية"
# طول: 41 حرف، يحتوي على عربي

# بعد التنظيف
comment = "Pending SELL_LIMIT XAUUSD from"
# طول: 31 حرف، ASCII فقط
```

### **2. تطبيق نفس الإصلاح على الأوامر الفورية (MARKET)**

```python
# في execute_signal() للأوامر الفورية
comment = f"Signal {signal.symbol}"
comment = comment.encode('ascii', 'ignore').decode('ascii')[:31]
```

### **3. إصلاح type_filling الديناميكي**

```python
# تحديد نوع التعبئة المناسب حسب الرمز
filling_type = symbol_info.filling_mode
if filling_type & 1:  # ORDER_FILLING_FOK
    type_filling = mt5.ORDER_FILLING_FOK
elif filling_type & 2:  # ORDER_FILLING_IOC
    type_filling = mt5.ORDER_FILLING_IOC
else:  # ORDER_FILLING_RETURN (default)
    type_filling = mt5.ORDER_FILLING_RETURN
```

**الفائدة:**
- ✅ تجنب خطأ "invalid filling type"
- ✅ يتكيف مع الرموز المختلفة تلقائياً

---

## 🧪 الاختبار

### **قبل:**
```python
comment = "Pending SELL_LIMIT XAUUSD from قناة عربية"
# ❌ خطأ: Invalid "comment" argument
```

### **بعد:**
```python
comment = "Pending SELL_LIMIT XAUUSD from"
# ✅ يعمل: ASCII فقط، 31 حرف
```

---

## 📊 قواعد MT5 للتعليق

### **القيود:**
- ✅ **طول**: حد أقصى **31 حرف**
- ✅ **محارف**: **ASCII فقط** (A-Z, a-z, 0-9, رموز خاصة)
- ❌ **ممنوع**: عربي، صيني، رموز Unicode

### **أمثلة صحيحة:**
```python
"Signal XAUUSD BUY"           # ✅
"Pending BUY_LIMIT Gold"      # ✅
"Auto trade 123"              # ✅
```

### **أمثلة خاطئة:**
```python
"إشارة XAUUSD"                                    # ❌ عربي
"Signal from قناة"                                # ❌ عربي
"This is a very long comment that exceeds 31"    # ❌ طويل جداً
```

---

## 📁 الملفات المعدلة

### **`mt5_manager.py`**

#### **1. دالة `execute_signal()` - الأوامر الفورية:**
```python
# قبل
"comment": f"Signal: {signal.symbol} from {signal.channel_name}"

# بعد
comment = f"Signal {signal.symbol}"
comment = comment.encode('ascii', 'ignore').decode('ascii')[:31]
"comment": comment
```

#### **2. دالة `place_pending_order()` - الأوامر المعلقة:**
```python
# قبل
"comment": f"Pending: {signal.order_type} {signal.symbol} from {signal.channel_name}"

# بعد
comment = f"Pending {signal.order_type} {signal.symbol}"
comment = comment.encode('ascii', 'ignore').decode('ascii')[:31]
"comment": comment
```

#### **3. تحديد type_filling ديناميكياً:**
```python
filling_type = symbol_info.filling_mode
if filling_type & 1:
    type_filling = mt5.ORDER_FILLING_FOK
elif filling_type & 2:
    type_filling = mt5.ORDER_FILLING_IOC
else:
    type_filling = mt5.ORDER_FILLING_RETURN
```

---

## 💡 ملاحظات مهمة

### **1. حذف المعلومات:**
- ✅ تم حذف `from {channel_name}` لتجنب المحارف غير الصالحة
- ✅ المعلومات الأساسية (Symbol, Type) محفوظة
- ✅ يمكن تتبع الأوامر من خلال `magic number = 234000`

### **2. encode/decode:**
```python
.encode('ascii', 'ignore')  # تحويل لـ ASCII، تجاهل المحارف غير الصالحة
.decode('ascii')            # إعادة لـ string
[:31]                       # اقتطاع لـ 31 حرف
```

### **3. بدائل للتتبع:**
- استخدام `magic` لتحديد البوت
- حفظ `channel_name` في قاعدة بيانات محلية
- استخدام `ticket` للربط

---

## 🎯 النتيجة

### **قبل الإصلاح:**
```
❌ فشل إرسال الأمر المعلق: (-2, 'Invalid "comment" argument')
```

### **بعد الإصلاح:**
```
✅ تم وضع أمر معلق SELL_LIMIT على XAUUSD
   التذكرة: 123456789
   سعر الدخول: 4076.0
   السعر الحالي: 4076.0
```

---

## 🚀 الاستخدام

الآن يمكن وضع الأوامر بدون قلق من محارف التعليق:

```python
# أي قناة (عربي/إنجليزي)
signal.channel_name = "قناة التداول العربية"
signal.channel_name = "Trading Channel"
signal.channel_name = None

# جميعها تعمل! ✅
```

**النتيجة:**
- ✅ تعليق آمن: `"Pending SELL_LIMIT XAUUSD"`
- ✅ لا أخطاء في MT5
- ✅ الأوامر تُنفذ بنجاح
