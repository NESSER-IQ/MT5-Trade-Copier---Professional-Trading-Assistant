#!/usr/bin/env python3
"""
سكريبت لاستبدال جميع استخدامات messagebox بـ show_toast
"""

import re

# قراءة الملف
with open('main_gui.py', 'r', encoding='utf-8') as f:
    content = f.read()

# نسخة احتياطية
with open('main_gui.py.backup', 'w', encoding='utf-8') as f:
    f.write(content)

# الاستبدالات
replacements = [
    # showinfo
    (r'messagebox\.showinfo\("قريباً", "هذه الميزة قيد التطوير"\)',
     r'self.show_toast("هذه الميزة قيد التطوير", "info")'),

    (r'messagebox\.showinfo\(["\']نجح["\'], ([^)]+)\)',
     r'self.show_toast(\1, "success")'),

    (r'messagebox\.showinfo\(["\']تنبيه["\'], ([^)]+)\)',
     r'self.show_toast(\1, "warning")'),

    # showerror
    (r'messagebox\.showerror\(["\']خطأ["\'], ([^)]+)\)',
     r'self.show_toast(\1, "error")'),

    # حالات خاصة متعددة الأسطر
    (r'messagebox\.showinfo\(\s*"نجح",\s*f"تم الاتصال بـ MT5 بنجاح\\n"\s*f"الحساب: \{login_int\}\\n"\s*f"الخادم: \{server\}"\s*\)',
     r'self.show_toast(f"تم الاتصال بـ MT5\\nالحساب: {login_int}", "success")'),

    (r'messagebox\.showerror\(\s*"خطأ",\s*"فشل الاتصال التلقائي بـ MT5\\n"\s*"يرجى التحقق من البيانات المحفوظة"\s*\)',
     r'self.show_toast("فشل الاتصال التلقائي بـ MT5", "error")'),
]

# تطبيق الاستبدالات
for pattern, replacement in replacements:
    content = re.sub(pattern, replacement, content)

# حفظ الملف
with open('main_gui.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ تم استبدال messagebox بنجاح!")
print("📁 تم إنشاء نسخة احتياطية: main_gui.py.backup")
