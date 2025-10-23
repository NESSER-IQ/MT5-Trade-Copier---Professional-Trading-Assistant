import customtkinter as ctk
from tkinter import filedialog, messagebox
import asyncio
import threading
from typing import Optional
import json
import csv
import re
import traceback
from datetime import datetime
from config import Config
from telegram_client import TelegramSignalClient
from mt5_manager import MT5Manager
from signal_parser import Signal
from encryption import CredentialManager
from daily_report_manager import DailyReportManager
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import os

# تعيين المظهر
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class ToastNotification:
    """نظام إشعارات Toast غير معيق - يظهر في الزاوية العلوية اليسرى"""

    def __init__(self, parent, message: str, type: str = "info", duration: int = 3000):
        """
        parent: النافذة الأم
        message: نص الرسالة
        type: نوع الإشعار (success, error, warning, info)
        duration: مدة العرض بالميلي ثانية
        """
        self.parent = parent
        self.duration = duration

        # ألوان حسب النوع
        colors = {
            "success": ("#155724", "#d4edda", "#4CAF50"),  # background, border, icon
            "error": ("#721c24", "#f8d7da", "#f44336"),
            "warning": ("#856404", "#fff3cd", "#FFA726"),
            "info": ("#004085", "#cce5ff", "#2196F3")
        }

        bg_color, border_color, icon_color = colors.get(type, colors["info"])

        # رموز حسب النوع
        icons = {
            "success": "✅",
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️"
        }
        icon = icons.get(type, "ℹ️")

        # إنشاء نافذة Toast
        self.toast = ctk.CTkFrame(
            parent,
            fg_color=bg_color,
            border_color=icon_color,
            border_width=2,
            corner_radius=10
        )

        # المحتوى
        content_frame = ctk.CTkFrame(self.toast, fg_color="transparent")
        content_frame.pack(padx=15, pady=10, fill="both", expand=True)

        # الأيقونة
        icon_label = ctk.CTkLabel(
            content_frame,
            text=icon,
            font=("Arial", 18),
            text_color=icon_color
        )
        icon_label.pack(side="left", padx=(0, 10))

        # النص
        msg_label = ctk.CTkLabel(
            content_frame,
            text=message,
            font=("Arial", 12),
            text_color="white",
            wraplength=300,
            justify="right"
        )
        msg_label.pack(side="left", fill="x", expand=True)

        # زر الإغلاق
        close_btn = ctk.CTkButton(
            content_frame,
            text="✕",
            width=25,
            height=25,
            fg_color="transparent",
            hover_color=border_color,
            command=self.hide,
            font=("Arial", 14, "bold")
        )
        close_btn.pack(side="right", padx=(10, 0))

        # وضع Toast في الأعلى يمين
        self.toast.place(relx=1.0, rely=0.0, x=-20, y=20, anchor="ne")

        # إخفاء تلقائي
        if duration > 0:
            parent.after(duration, self.hide)

    def hide(self):
        """إخفاء الإشعار بتأثير"""
        try:
            self.toast.place_forget()
            self.toast.destroy()
        except:
            pass


class TelegramMT5GUI:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("MT5 Trade Copier - Professional Trading Assistant")
        self.root.geometry("1400x900")
        
        # منع مشكلة الشفافية
        self.root.attributes('-alpha', 1.0)
        
        # معالج لإغلاق التطبيق بشكل صحيح
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # المتغيرات
        self.telegram_client: Optional[TelegramSignalClient] = None
        self.mt5_manager = MT5Manager()
        self.config = Config()
        self.credential_manager = CredentialManager()
        self.report_manager = DailyReportManager()
        self.loop = None
        self.loop_thread = None
        
        # علم للتحقق من إيقاف التطبيق
        self._is_closing = False

        # البيانات
        self.received_signals = []
        self.signals_file = 'data/signals_history.json'

        # قائمة للرسائل المرفوضة (لتتبع الرسائل غير المفيدة)
        self.rejected_messages = []

        # نظام إدارة الصفقات المعلقة
        self.pending_trades = []  # قائمة الصفقات التي فشل تنفيذها
        self.max_retry_attempts = 3  # عدد محاولات إعادة التنفيذ

        # تحميل بيانات الاعتماد المحفوظة
        self.load_saved_credentials()

        # بدء حلقة asyncio
        self.start_event_loop()

        # بناء الواجهة
        self.build_ui()

        # تحديث دوري للبيانات
        self.schedule_updates()

        # جدولة التقارير اليومية
        self.schedule_daily_report()
        
        # جدولة تنظيف الذاكرة الدوري
        self.schedule_memory_cleanup()

        # محاولة الاتصال التلقائي بـ MT5 عند بدء التطبيق
        self.root.after(1000, self.auto_connect_on_startup)

    def show_toast(self, message: str, type: str = "info", duration: int = 3000):
        """عرض إشعار Toast غير معيق"""
        try:
            ToastNotification(self.root, message, type, duration)
        except Exception as e:
            print(f"خطأ في عرض Toast: {e}")

    def start_event_loop(self):
        """بدء حلقة asyncio في thread منفصل"""
        def run_loop(loop):
            asyncio.set_event_loop(loop)
            loop.run_forever()

        self.loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(target=run_loop, args=(self.loop,), daemon=True)
        self.loop_thread.start()

    def build_ui(self):
        """بناء الواجهة الرسومية"""
        # شريط الحالة العلوي
        self.create_status_bar()

        # الإطار الرئيسي مع التبويبات
        self.tabview = ctk.CTkTabview(self.root)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # إضافة التبويبات
        self.tab_dashboard = self.tabview.add("لوحة التحكم")
        self.tab_live_messages = self.tabview.add("📨 الرسائل الحية")
        self.tab_settings = self.tabview.add("الإعدادات")
        self.tab_channels = self.tabview.add("القنوات")
        self.tab_signals = self.tabview.add("الإشارات")
        self.tab_positions = self.tabview.add("الصفقات المفتوحة")
        self.tab_patterns = self.tabview.add("أنماط الرسائل")
        self.tab_symbols = self.tabview.add("📊 خصائص الرموز")

        # بناء محتوى كل تبويب
        self.build_dashboard_tab()
        self.build_live_messages_tab()
        self.build_settings_tab()
        self.build_channels_tab()
        self.build_signals_tab()
        self.build_positions_tab()
        self.build_patterns_tab()
        self.build_symbols_tab()

        # قائمة الرسائل الحية
        self.live_messages = []
        self.max_live_messages = 50  # الحد الأقصى للرسائل المعروضة

    def create_status_bar(self):
        """إنشاء شريط الحالة"""
        status_frame = ctk.CTkFrame(self.root, height=60)
        status_frame.pack(fill="x", padx=10, pady=10)

        # حالة التليجرام
        telegram_frame = ctk.CTkFrame(status_frame)
        telegram_frame.pack(side="left", padx=20, pady=10)

        ctk.CTkLabel(telegram_frame, text="التليجرام:", font=("Arial", 14, "bold")).pack(side="left", padx=5)
        self.telegram_status_label = ctk.CTkLabel(
            telegram_frame, text="⚪ غير متصل",
            font=("Arial", 13), text_color="gray"
        )
        self.telegram_status_label.pack(side="left", padx=5)

        # حالة MT5
        mt5_frame = ctk.CTkFrame(status_frame)
        mt5_frame.pack(side="left", padx=20, pady=10)

        ctk.CTkLabel(mt5_frame, text="MT5:", font=("Arial", 14, "bold")).pack(side="left", padx=5)
        self.mt5_status_label = ctk.CTkLabel(
            mt5_frame, text="⚪ غير متصل",
            font=("Arial", 13), text_color="gray"
        )
        self.mt5_status_label.pack(side="left", padx=5)

        # الرصيد
        balance_frame = ctk.CTkFrame(status_frame)
        balance_frame.pack(side="right", padx=20, pady=10)

        ctk.CTkLabel(balance_frame, text="الرصيد:", font=("Arial", 14, "bold")).pack(side="left", padx=5)
        self.balance_label = ctk.CTkLabel(
            balance_frame, text="$0.00",
            font=("Arial", 13, "bold"), text_color="green"
        )
        self.balance_label.pack(side="left", padx=5)

        # حالة التداول التلقائي
        auto_trade_frame = ctk.CTkFrame(status_frame)
        auto_trade_frame.pack(side="right", padx=20, pady=10)

        ctk.CTkLabel(auto_trade_frame, text="التداول التلقائي:", font=("Arial", 14, "bold")).pack(side="left", padx=5)
        self.auto_trade_status_label = ctk.CTkLabel(
            auto_trade_frame, text="🤖 مفعّل",
            font=("Arial", 13), text_color="green"
        )
        self.auto_trade_status_label.pack(side="left", padx=5)

    def build_live_messages_tab(self):
        """بناء تبويب الرسائل الحية"""
        # شريط الأدوات العلوي
        toolbar = ctk.CTkFrame(self.tab_live_messages)
        toolbar.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            toolbar, text="📨 الرسائل الحية من القنوات",
            font=("Arial", 18, "bold")
        ).pack(side="left", padx=10)

        # أزرار التحكم
        ctk.CTkButton(
            toolbar, text="🔄 تحديث",
            command=self.refresh_live_messages, width=100,
            fg_color="#4CAF50", hover_color="#45a049"
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            toolbar, text="🗑️ مسح الكل",
            command=self.clear_live_messages, width=100,
            fg_color="#f44336", hover_color="#da190b"
        ).pack(side="right", padx=5)

        # إطار قابل للتمرير للرسائل
        self.live_messages_scroll = ctk.CTkScrollableFrame(
            self.tab_live_messages,
            height=650,
            fg_color="#1a1a1a"
        )
        self.live_messages_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # رسالة ترحيبية
        welcome_frame = ctk.CTkFrame(self.live_messages_scroll, fg_color="#2b2b2b")
        welcome_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            welcome_frame,
            text="🎯 جاهز لاستقبال الرسائل!",
            font=("Arial", 16, "bold"),
            text_color="#4CAF50"
        ).pack(pady=20)

        ctk.CTkLabel(
            welcome_frame,
            text="سيتم عرض جميع الرسائل الواردة من القنوات المراقبة هنا\nمع تحليل تفصيلي لكل إشارة",
            font=("Arial", 12),
            text_color="gray"
        ).pack(pady=(0, 20))

    def build_dashboard_tab(self):
        """بناء لوحة التحكم - محسّنة مع عرض الصفقات المعلقة"""
        # الإطار العلوي - بطاقات المعلومات
        cards_frame = ctk.CTkFrame(self.tab_dashboard)
        cards_frame.pack(fill="x", padx=10, pady=10)

        # بطاقة الصفقات - محسّنة
        trades_card = ctk.CTkFrame(cards_frame, width=200, fg_color="#1a1a1a", corner_radius=12)
        trades_card.pack(side="left", padx=8, pady=10, fill="both", expand=True)

        # أيقونة
        ctk.CTkLabel(trades_card, text="📈", font=("Arial", 24)).pack(pady=(15, 0))
        ctk.CTkLabel(trades_card, text="إجمالي الصفقات", font=("Arial", 12), text_color="#aaa").pack(pady=(5, 2))
        self.total_trades_label = ctk.CTkLabel(
            trades_card, text="0", font=("Arial", 36, "bold"), text_color="#3b8ed0"
        )
        self.total_trades_label.pack(pady=(2, 15))

        # بطاقة الأرباح - محسّنة
        profit_card = ctk.CTkFrame(cards_frame, width=200, fg_color="#1a1a1a", corner_radius=12)
        profit_card.pack(side="left", padx=8, pady=10, fill="both", expand=True)

        ctk.CTkLabel(profit_card, text="💰", font=("Arial", 24)).pack(pady=(15, 0))
        ctk.CTkLabel(profit_card, text="أرباح اليوم", font=("Arial", 12), text_color="#aaa").pack(pady=(5, 2))
        self.profit_label = ctk.CTkLabel(
            profit_card, text="$0.00", font=("Arial", 36, "bold"), text_color="#4CAF50"
        )
        self.profit_label.pack(pady=(2, 15))

        # بطاقة معدل النجاح - محسّنة
        winrate_card = ctk.CTkFrame(cards_frame, width=200, fg_color="#1a1a1a", corner_radius=12)
        winrate_card.pack(side="left", padx=8, pady=10, fill="both", expand=True)

        ctk.CTkLabel(winrate_card, text="🎯", font=("Arial", 24)).pack(pady=(15, 0))
        ctk.CTkLabel(winrate_card, text="معدل النجاح", font=("Arial", 12), text_color="#aaa").pack(pady=(5, 2))
        self.winrate_label = ctk.CTkLabel(
            winrate_card, text="0%", font=("Arial", 36, "bold"), text_color="#f59e42"
        )
        self.winrate_label.pack(pady=(2, 15))

        # بطاقة الصفقات المعلقة - محسّنة
        pending_card = ctk.CTkFrame(cards_frame, width=200, fg_color="#2d1f1f", corner_radius=12, border_width=2, border_color="#FFA726")
        pending_card.pack(side="left", padx=8, pady=10, fill="both", expand=True)

        ctk.CTkLabel(pending_card, text="⏳", font=("Arial", 24)).pack(pady=(15, 0))
        ctk.CTkLabel(pending_card, text="صفقات معلقة", font=("Arial", 12), text_color="#aaa").pack(pady=(5, 2))
        self.pending_trades_label = ctk.CTkLabel(
            pending_card, text="0", font=("Arial", 36, "bold"), text_color="#FFA726"
        )
        self.pending_trades_label.pack(pady=(2, 15))

        # بطاقة القنوات - محسّنة
        channels_card = ctk.CTkFrame(cards_frame, width=200, fg_color="#1a1a1a", corner_radius=12)
        channels_card.pack(side="left", padx=8, pady=10, fill="both", expand=True)

        ctk.CTkLabel(channels_card, text="📡", font=("Arial", 24)).pack(pady=(15, 0))
        ctk.CTkLabel(channels_card, text="القنوات النشطة", font=("Arial", 12), text_color="#aaa").pack(pady=(5, 2))
        self.active_channels_label = ctk.CTkLabel(
            channels_card, text="0", font=("Arial", 36, "bold"), text_color="#9b59b6"
        )
        self.active_channels_label.pack(pady=(2, 15))

        # الإطار الأوسط - الرسومات
        charts_frame = ctk.CTkFrame(self.tab_dashboard)
        charts_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # رسم بياني للأرباح
        self.create_profit_chart(charts_frame)

    def create_profit_chart(self, parent):
        """إنشاء رسم بياني للأرباح - محسّن وأكثر أناقة"""
        # إنشاء إطار للرسم البياني
        chart_frame = ctk.CTkFrame(parent, fg_color="#1a1a1a", corner_radius=10)
        chart_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # عنوان الرسم البياني
        title_frame = ctk.CTkFrame(chart_frame, fg_color="transparent")
        title_frame.pack(fill="x", padx=15, pady=(15, 5))

        ctk.CTkLabel(
            title_frame,
            text="📊 أداء التداول - آخر 7 أيام",
            font=("Arial", 16, "bold"),
            text_color="#64B5F6"
        ).pack(side="left")

        # الرسم البياني
        fig = Figure(figsize=(10, 3.5), facecolor='#1a1a1a', dpi=100)
        ax = fig.add_subplot(111)
        ax.set_facecolor('#0d0d0d')

        # إزالة الإطار
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#555')
        ax.spines['bottom'].set_color('#555')

        # تحسين الشبكة
        ax.grid(True, alpha=0.2, linestyle='--', linewidth=0.5)
        ax.set_axisbelow(True)

        # بيانات تجريبية
        days = ['اليوم-6', 'اليوم-5', 'اليوم-4', 'اليوم-3', 'اليوم-2', 'أمس', 'اليوم']
        profits = [120, 150, -50, 200, 180, 90, 160]

        # ألوان متدرجة
        colors = ['#4CAF50' if p >= 0 else '#F44336' for p in profits]
        bars = ax.bar(days, profits, color=colors, alpha=0.8, edgecolor='white', linewidth=0.5)

        # إضافة قيم فوق الأعمدة
        for bar, profit in zip(bars, profits):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'${profit:.0f}',
                   ha='center', va='bottom' if height > 0 else 'top',
                   color='white', fontsize=9, fontweight='bold')

        # تحسين المحاور
        ax.tick_params(colors='#aaa', labelsize=9)
        ax.set_ylabel('الربح ($)', color='#aaa', fontsize=10)
        ax.set_xlabel('')

        # تحسين الهوامش
        fig.tight_layout(pad=1.5)

        canvas = FigureCanvasTkAgg(fig, chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=(5, 10))

    def build_settings_tab(self):
        """بناء تبويب الإعدادات"""
        # إعدادات التليجرام
        telegram_frame = ctk.CTkFrame(self.tab_settings)
        telegram_frame.pack(fill="x", padx=20, pady=20)

        ctk.CTkLabel(
            telegram_frame, text="إعدادات التليجرام",
            font=("Arial", 16, "bold")
        ).pack(pady=(10, 20))

        # API ID
        ctk.CTkLabel(telegram_frame, text="API ID:", font=("Arial", 13)).pack(anchor="w", padx=20)
        self.api_id_entry = ctk.CTkEntry(telegram_frame, width=400, placeholder_text="أدخل API ID")
        self.api_id_entry.pack(padx=20, pady=5)
        self.api_id_entry.insert(0, Config.API_ID)

        # API Hash
        ctk.CTkLabel(telegram_frame, text="API Hash:", font=("Arial", 13)).pack(anchor="w", padx=20, pady=(10, 0))
        self.api_hash_entry = ctk.CTkEntry(telegram_frame, width=400, placeholder_text="أدخل API Hash")
        self.api_hash_entry.pack(padx=20, pady=5)
        self.api_hash_entry.insert(0, Config.API_HASH)

        # رقم الهاتف
        ctk.CTkLabel(telegram_frame, text="رقم الهاتف:", font=("Arial", 13)).pack(anchor="w", padx=20, pady=(10, 0))
        self.phone_entry = ctk.CTkEntry(telegram_frame, width=400, placeholder_text="+1234567890")
        self.phone_entry.pack(padx=20, pady=5)
        self.phone_entry.insert(0, Config.PHONE_NUMBER)

        # زر الاتصال بالتليجرام
        self.telegram_connect_btn = ctk.CTkButton(
            telegram_frame, text="الاتصال بالتليجرام",
            command=self.connect_telegram, font=("Arial", 13),
            height=40, width=200
        )
        self.telegram_connect_btn.pack(pady=20)

        # إعدادات MT5
        mt5_frame = ctk.CTkFrame(self.tab_settings)
        mt5_frame.pack(fill="x", padx=20, pady=20)

        ctk.CTkLabel(
            mt5_frame, text="إعدادات MT5",
            font=("Arial", 16, "bold")
        ).pack(pady=(10, 20))

        # Login
        ctk.CTkLabel(mt5_frame, text="رقم الحساب:", font=("Arial", 13)).pack(anchor="w", padx=20)
        self.mt5_login_entry = ctk.CTkEntry(mt5_frame, width=400, placeholder_text="أدخل رقم الحساب")
        self.mt5_login_entry.pack(padx=20, pady=5)
        self.mt5_login_entry.insert(0, Config.MT5_LOGIN)

        # Password
        ctk.CTkLabel(mt5_frame, text="كلمة المرور:", font=("Arial", 13)).pack(anchor="w", padx=20, pady=(10, 0))
        self.mt5_password_entry = ctk.CTkEntry(mt5_frame, width=400, show="*", placeholder_text="أدخل كلمة المرور")
        self.mt5_password_entry.pack(padx=20, pady=5)
        self.mt5_password_entry.insert(0, Config.MT5_PASSWORD)

        # Server
        ctk.CTkLabel(mt5_frame, text="الخادم:", font=("Arial", 13)).pack(anchor="w", padx=20, pady=(10, 0))
        self.mt5_server_entry = ctk.CTkEntry(mt5_frame, width=400, placeholder_text="مثال: MetaQuotes-Demo")
        self.mt5_server_entry.pack(padx=20, pady=5)
        self.mt5_server_entry.insert(0, Config.MT5_SERVER)

        # حجم اللوت الافتراضي
        ctk.CTkLabel(mt5_frame, text="حجم اللوت الافتراضي:", font=("Arial", 13)).pack(anchor="w", padx=20, pady=(10, 0))
        self.lot_size_entry = ctk.CTkEntry(mt5_frame, width=400, placeholder_text="0.01")
        self.lot_size_entry.pack(padx=20, pady=5)
        self.lot_size_entry.insert(0, "0.01")

        # إطار الأزرار
        buttons_frame = ctk.CTkFrame(mt5_frame)
        buttons_frame.pack(pady=20)

        # زر الاتصال التلقائي
        self.mt5_auto_connect_btn = ctk.CTkButton(
            buttons_frame, text="🔄 اتصال تلقائي (موصى به)",
            command=self.connect_mt5_auto, font=("Arial", 13),
            height=40, width=250,
            fg_color="#4CAF50", hover_color="#45a049"
        )
        self.mt5_auto_connect_btn.pack(side="left", padx=10)

        # زر الاتصال اليدوي
        self.mt5_connect_btn = ctk.CTkButton(
            buttons_frame, text="الاتصال اليدوي",
            command=self.connect_mt5, font=("Arial", 13),
            height=40, width=200
        )
        self.mt5_connect_btn.pack(side="left", padx=10)

        # زر عرض الرموز المتاحة - جديد
        self.show_symbols_btn = ctk.CTkButton(
            buttons_frame, text="📋 عرض الرموز المتاحة",
            command=self.show_available_symbols, font=("Arial", 13),
            height=40, width=200,
            fg_color="#2196F3", hover_color="#1976D2"
        )
        self.show_symbols_btn.pack(side="left", padx=10)

        # خيارات إضافية
        options_frame = ctk.CTkFrame(self.tab_settings)
        options_frame.pack(fill="x", padx=20, pady=20)

        ctk.CTkLabel(
            options_frame, text="خيارات الاتصال",
            font=("Arial", 16, "bold")
        ).pack(pady=(10, 20))

        # خيار الاتصال التلقائي بـ MT5
        self.auto_connect_var = ctk.BooleanVar(value=True)
        self.auto_connect_checkbox = ctk.CTkCheckBox(
            options_frame,
            text="🔗 الاتصال التلقائي بـ MT5 عند بدء التطبيق",
            variable=self.auto_connect_var,
            font=("Arial", 13)
        )
        self.auto_connect_checkbox.pack(anchor="w", padx=20, pady=10)

        # خيار التداول التلقائي
        self.auto_trade_var = ctk.BooleanVar(value=True)
        self.auto_trade_checkbox = ctk.CTkCheckBox(
            options_frame,
            text="🤖 تفعيل التداول التلقائي (تنفيذ الإشارات تلقائياً)",
            variable=self.auto_trade_var,
            font=("Arial", 13)
        )
        self.auto_trade_checkbox.pack(anchor="w", padx=20, pady=10)

        # معلومات إضافية
        info_label = ctk.CTkLabel(
            options_frame,
            text="ℹ️ عند تفعيل التداول التلقائي، سيتم تنفيذ جميع الإشارات المستلمة من القنوات تلقائياً",
            font=("Arial", 11),
            text_color="gray"
        )
        info_label.pack(anchor="w", padx=20, pady=(0, 10))

        # تحميل القيم المحفوظة
        settings = Config.load_settings()
        self.auto_connect_var.set(settings.get('auto_connect_mt5', True))
        self.auto_trade_var.set(settings.get('auto_trade', True))

        # زر حفظ الإعدادات
        ctk.CTkButton(
            self.tab_settings, text="حفظ الإعدادات",
            command=self.save_settings, font=("Arial", 13),
            height=40, width=200
        ).pack(pady=20)

    def build_channels_tab(self):
        """بناء تبويب القنوات"""
        # إطار الإضافة
        add_frame = ctk.CTkFrame(self.tab_channels)
        add_frame.pack(fill="x", padx=20, pady=20)

        ctk.CTkLabel(
            add_frame, text="إضافة قناة جديدة",
            font=("Arial", 16, "bold")
        ).pack(pady=(10, 10))

        # حقل إدخال القناة
        input_frame = ctk.CTkFrame(add_frame)
        input_frame.pack(pady=10)

        self.channel_entry = ctk.CTkEntry(
            input_frame, width=300,
            placeholder_text="أدخل رابط القناة أو @username"
        )
        self.channel_entry.pack(side="left", padx=10)

        ctk.CTkButton(
            input_frame, text="إضافة",
            command=self.add_channel, width=100
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            input_frame, text="عرض جميع القنوات",
            command=self.show_all_channels, width=150,
            fg_color="#9b59b6", hover_color="#8e44ad"
        ).pack(side="left", padx=5)

        # إطار أزرار التحكم الجماعي
        bulk_actions_frame = ctk.CTkFrame(add_frame)
        bulk_actions_frame.pack(pady=10)

        ctk.CTkButton(
            bulk_actions_frame, text="✅ تفعيل الكل",
            command=self.activate_all_channels, width=120,
            fg_color="#4CAF50", hover_color="#45a049"
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            bulk_actions_frame, text="⏸️ تعطيل الكل",
            command=self.deactivate_all_channels, width=120,
            fg_color="#FF9800", hover_color="#F57C00"
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            bulk_actions_frame, text="🔄 تحديث القائمة",
            command=self.refresh_channels, width=120
        ).pack(side="left", padx=5)

        # قائمة القنوات
        list_frame = ctk.CTkFrame(self.tab_channels)
        list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        ctk.CTkLabel(
            list_frame, text="القنوات المضافة",
            font=("Arial", 16, "bold")
        ).pack(pady=(10, 10))

        # إطار قابل للتمرير للقنوات
        self.channels_scroll = ctk.CTkScrollableFrame(list_frame, height=400)
        self.channels_scroll.pack(fill="both", expand=True, padx=10, pady=10)

    def build_signals_tab(self):
        """بناء تبويب الإشارات"""
        # أزرار الإجراءات
        actions_frame = ctk.CTkFrame(self.tab_signals)
        actions_frame.pack(fill="x", padx=20, pady=20)

        ctk.CTkButton(
            actions_frame, text="تصدير الإشارات (CSV)",
            command=self.export_signals_csv, width=200
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            actions_frame, text="تصدير الإشارات (JSON)",
            command=self.export_signals_json, width=200
        ).pack(side="left", padx=10)

        # زر إعادة محاولة الصفقات المعلقة
        self.retry_pending_btn = ctk.CTkButton(
            actions_frame, text="🔄 إعادة محاولة الصفقات المعلقة",
            command=self.retry_pending_trades, width=250,
            fg_color="#FFA726", hover_color="#FB8C00"
        )
        self.retry_pending_btn.pack(side="left", padx=10)
        
        # عداد الصفقات المعلقة
        self.pending_count_label = ctk.CTkLabel(
            actions_frame, text="معلق: 0", 
            font=("Arial", 12, "bold"),
            text_color="#FFA726"
        )
        self.pending_count_label.pack(side="left", padx=10)

        ctk.CTkButton(
            actions_frame, text="تحديث",
            command=self.refresh_signals, width=100
        ).pack(side="right", padx=10)

        # قائمة الإشارات
        list_frame = ctk.CTkFrame(self.tab_signals)
        list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        ctk.CTkLabel(
            list_frame, text="الإشارات المستلمة",
            font=("Arial", 16, "bold")
        ).pack(pady=(10, 10))

        # إطار قابل للتمرير للإشارات
        self.signals_scroll = ctk.CTkScrollableFrame(list_frame, height=500)
        self.signals_scroll.pack(fill="both", expand=True, padx=10, pady=10)

    def build_positions_tab(self):
        """بناء تبويب الصفقات المفتوحة"""
        # زر التحديث
        ctk.CTkButton(
            self.tab_positions, text="تحديث الصفقات",
            command=self.refresh_positions, width=200
        ).pack(pady=20)

        # قائمة الصفقات
        self.positions_scroll = ctk.CTkScrollableFrame(self.tab_positions, height=600)
        self.positions_scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    def build_patterns_tab(self):
        """بناء تبويب أنماط الرسائل"""
        ctk.CTkLabel(
            self.tab_patterns,
            text="إدارة أنماط الرسائل المخصصة",
            font=("Arial", 16, "bold")
        ).pack(pady=20)

        info_label = ctk.CTkLabel(
            self.tab_patterns,
            text="هنا يمكنك إضافة أنماط مخصصة لتحليل الرسائل من القنوات المختلفة.\n"
                 "النظام يدعم حالياً معظم الأنماط الشائعة تلقائياً.",
            font=("Arial", 12)
        )
        info_label.pack(pady=20)

        # منطقة إضافة نمط جديد
        pattern_frame = ctk.CTkFrame(self.tab_patterns)
        pattern_frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(pattern_frame, text="اسم النمط:", font=("Arial", 13)).pack(anchor="w", padx=20, pady=(10, 5))
        pattern_name_entry = ctk.CTkEntry(pattern_frame, width=400, placeholder_text="مثال: نمط القناة 1")
        pattern_name_entry.pack(padx=20, pady=5)

        ctk.CTkLabel(pattern_frame, text="وصف النمط:", font=("Arial", 13)).pack(anchor="w", padx=20, pady=(10, 5))
        pattern_desc_text = ctk.CTkTextbox(pattern_frame, width=400, height=150)
        pattern_desc_text.pack(padx=20, pady=5)

        ctk.CTkButton(
            pattern_frame, text="إضافة نمط",
            command=lambda: messagebox.showinfo("قريباً", "هذه الميزة قيد التطوير"),
            width=200
        ).pack(pady=20)

    # ===== وظائف التحكم =====

    def connect_telegram(self):
        """الاتصال بالتليجرام"""
        api_id = self.api_id_entry.get().strip()
        api_hash = self.api_hash_entry.get().strip()
        phone = self.phone_entry.get().strip()

        if not all([api_id, api_hash, phone]):
            self.show_toast("يرجى ملء جميع حقول التليجرام", "error")
            return

        # عرض تنبيه بدء الاتصال
        self.show_toast("جاري الاتصال بالتليجرام...", "info", 2000)

        # تشغيل الاتصال في مهمة async
        async def do_connect():
            self.telegram_client = TelegramSignalClient(api_id, api_hash, phone)
            self.telegram_client.set_signal_callback(self.on_signal_received)
            self.telegram_client.set_message_callback(self.on_message_received)
            success = await self.telegram_client.start()

            if success:
                self.root.after(0, lambda: self.telegram_status_label.configure(
                    text="🟢 متصل", text_color="green"
                ))
                self.root.after(0, lambda: self.show_toast("تم الاتصال بالتليجرام بنجاح", "success"))
                self.root.after(0, self.refresh_channels)
            else:
                self.root.after(0, lambda: self.show_toast("فشل الاتصال بالتليجرام", "error"))

        asyncio.run_coroutine_threadsafe(do_connect(), self.loop)

    def connect_mt5(self):
        """الاتصال بـ MT5"""
        login = self.mt5_login_entry.get().strip()
        password = self.mt5_password_entry.get().strip()
        server = self.mt5_server_entry.get().strip()

        if not all([login, password, server]):
            self.show_toast("يرجى ملء جميع حقول MT5", "error")
            return

        try:
            login_int = int(login)
            self.show_toast("جاري الاتصال بـ MT5...", "info", 2000)
            success = self.mt5_manager.connect(login_int, password, server)

            if success:
                self.mt5_status_label.configure(text="🟢 متصل", text_color="green")
                self.update_balance()
                self.show_toast("تم الاتصال بـ MT5 بنجاح", "success")
            else:
                self.show_toast("فشل الاتصال بـ MT5", "error")

        except ValueError:
            self.show_toast("رقم الحساب يجب أن يكون رقماً", "error")

    def show_available_symbols(self):
        """عرض نافذة بالرموز المتاحة في المنصة"""
        if not self.mt5_manager.is_connected:
            self.show_toast("⚠️ يجب الاتصال بـ MT5 أولاً", "warning")
            return

        # إنشاء نافذة جديدة
        symbols_window = ctk.CTkToplevel(self.root)
        symbols_window.title("الرموز المتاحة في MT5")
        symbols_window.geometry("600x700")

        # العنوان
        title_frame = ctk.CTkFrame(symbols_window)
        title_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            title_frame,
            text="📋 الرموز المتاحة في المنصة",
            font=("Arial", 18, "bold")
        ).pack(pady=10)

        # شريط البحث
        search_frame = ctk.CTkFrame(symbols_window)
        search_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(search_frame, text="🔍 بحث:", font=("Arial", 13)).pack(side="left", padx=10)
        search_entry = ctk.CTkEntry(search_frame, width=400, placeholder_text="ابحث عن رمز...")
        search_entry.pack(side="left", padx=10, pady=10)

        # إطار قابل للتمرير للرموز
        symbols_scroll = ctk.CTkScrollableFrame(symbols_window, height=500)
        symbols_scroll.pack(fill="both", expand=True, padx=10, pady=10)

        # دالة لتحديث القائمة
        def update_symbols_list(search_term=""):
            # مسح القائمة الحالية
            for widget in symbols_scroll.winfo_children():
                widget.destroy()

            # الحصول على الرموز
            symbols = self.mt5_manager.get_available_symbols(search_term)

            if not symbols:
                ctk.CTkLabel(
                    symbols_scroll,
                    text="لا توجد رموز متاحة",
                    font=("Arial", 14)
                ).pack(pady=50)
                return

            # عرض عدد الرموز
            count_label = ctk.CTkLabel(
                symbols_scroll,
                text=f"عدد الرموز: {len(symbols)}",
                font=("Arial", 12, "bold"),
                text_color="#4CAF50"
            )
            count_label.pack(pady=5)

            # عرض الرموز
            for symbol in symbols:
                symbol_frame = ctk.CTkFrame(symbols_scroll, fg_color="#2b2b2b")
                symbol_frame.pack(fill="x", padx=5, pady=2)

                ctk.CTkLabel(
                    symbol_frame,
                    text=symbol,
                    font=("Courier New", 12),
                    anchor="w"
                ).pack(side="left", padx=15, pady=8)

        # ربط البحث
        def on_search(*args):
            update_symbols_list(search_entry.get())

        search_entry.bind("<KeyRelease>", on_search)

        # زر التحديث
        refresh_btn = ctk.CTkButton(
            search_frame,
            text="🔄",
            width=40,
            command=lambda: update_symbols_list(search_entry.get()),
            fg_color="#4CAF50",
            hover_color="#45a049"
        )
        refresh_btn.pack(side="left", padx=5)

        # زر مسح الذاكرة المؤقتة
        clear_cache_btn = ctk.CTkButton(
            symbols_window,
            text="🗑️ مسح ذاكرة الرموز المؤقتة",
            command=lambda: [self.mt5_manager.clear_symbol_cache(), self.show_toast("✅ تم المسح", "success")],
            fg_color="#FF5722",
            hover_color="#E64A19"
        )
        clear_cache_btn.pack(pady=10)

        # تحميل الرموز
        update_symbols_list()

    def connect_mt5_auto(self):
        """الاتصال التلقائي بـ MT5"""
        # تعطيل الزر مؤقتاً
        self.mt5_auto_connect_btn.configure(state="disabled", text="⏳ جارٍ الاتصال...")

        try:
            success = self.mt5_manager.connect_auto()

            if success:
                self.mt5_status_label.configure(text="🟢 متصل (تلقائي)", text_color="green")
                self.update_balance()

                # تحديث الحقول بمعلومات الحساب المكتشف
                account_info = self.mt5_manager.account_info
                if account_info:
                    self.mt5_login_entry.delete(0, 'end')
                    self.mt5_login_entry.insert(0, str(account_info.login))
                    self.mt5_server_entry.delete(0, 'end')
                    self.mt5_server_entry.insert(0, account_info.server)

                messagebox.showinfo(
                    "نجح",
                    f"✅ تم الاتصال التلقائي بـ MT5\n\n"
                    f"الحساب: {account_info.login}\n"
                    f"الخادم: {account_info.server}\n"
                    f"الرصيد: {account_info.balance} {account_info.currency}"
                )
            else:
                messagebox.showerror(
                    "خطأ",
                    "❌ فشل الاتصال التلقائي\n\n"
                    "تأكد من:\n"
                    "1. تطبيق MT5 Terminal مفتوح\n"
                    "2. تم تسجيل الدخول في MT5\n"
                    "3. الحساب نشط ومتصل\n\n"
                    "يمكنك استخدام الاتصال اليدوي بدلاً من ذلك."
                )

        except Exception as e:
            messagebox.showerror("خطأ", f"خطأ في الاتصال التلقائي:\n{str(e)}")

        finally:
            # إعادة تفعيل الزر
            self.mt5_auto_connect_btn.configure(state="normal", text="🔄 اتصال تلقائي (موصى به)")

    def save_settings(self):
        """حفظ الإعدادات بشكل مشفر"""
        api_id = self.api_id_entry.get().strip()
        api_hash = self.api_hash_entry.get().strip()
        phone = self.phone_entry.get().strip()

        mt5_login = self.mt5_login_entry.get().strip()
        mt5_password = self.mt5_password_entry.get().strip()
        mt5_server = self.mt5_server_entry.get().strip()

        # حفظ بيانات Telegram بشكل مشفر
        if api_id and api_hash and phone:
            self.credential_manager.save_telegram_credentials(api_id, api_hash, phone)

        # حفظ بيانات MT5 بشكل مشفر
        if mt5_login and mt5_password and mt5_server:
            self.credential_manager.save_mt5_credentials(mt5_login, mt5_password, mt5_server)

        # تحميل الإعدادات الحالية أولاً
        current_settings = Config.load_settings()

        # حفظ الإعدادات الأخرى
        settings = {
            **current_settings,  # الحفاظ على الإعدادات الحالية
            'lot_size': self.lot_size_entry.get().strip(),
            'auto_connect_mt5': self.auto_connect_var.get(),
            'auto_trade': self.auto_trade_var.get()
        }

        Config.save_settings(settings)
        self.show_toast("تم حفظ الإعدادات بشكل مشفر", "success")

    def add_channel(self):
        """إضافة قناة"""
        if not self.telegram_client or not self.telegram_client.is_connected:
            self.show_toast("يجب الاتصال بالتليجرام أولاً", "error")
            return

        channel_id = self.channel_entry.get().strip()
        if not channel_id:
            self.show_toast("يرجى إدخال رابط القناة أو اسم المستخدم", "warning")
            return

        self.show_toast("جاري إضافة القناة...", "info", 2000)

        async def do_add():
            result = await self.telegram_client.add_channel(channel_id)

            if result['success']:
                self.root.after(0, lambda: self.show_toast(f"تمت إضافة القناة: {result['channel']['name']}", "success"))
                self.root.after(0, self.refresh_channels)
                self.root.after(0, lambda: self.channel_entry.delete(0, 'end'))
            else:
                self.root.after(0, lambda: self.show_toast(f"فشل إضافة القناة: {result['error']}", "error"))

        asyncio.run_coroutine_threadsafe(do_add(), self.loop)

    def add_live_message_to_ui(self, message_data: dict, signal: Signal = None):
        """إضافة رسالة جديدة لواجهة الرسائل الحية - محسّنة للأداء"""
        try:
            # التحقق من أن الـ widget موجود وصالح
            if not self.live_messages_scroll or not self.live_messages_scroll.winfo_exists():
                return
            
            # إزالة رسالة الترحيب فقط في المرة الأولى
            if not hasattr(self, '_welcome_removed'):
                try:
                    for widget in self.live_messages_scroll.winfo_children():
                        if widget.winfo_exists():
                            widget.destroy()
                except Exception:
                    pass
                self._welcome_removed = True

            # إضافة الرسالة الجديدة في الأعلى فقط
            new_card = self.create_live_message_card(message_data, signal)
            if new_card and new_card.winfo_exists():
                try:
                    # إضافة البطاقة في الأعلى
                    new_card.pack(fill="x", padx=10, pady=5, side="top", anchor="n")
                    # إضافة للقائمة
                    self.live_messages.insert(0, {'message_data': message_data, 'signal': signal, 'widget': new_card})
                except Exception as e:
                    print(f"خطأ في pack البطاقة: {e}")
                    if new_card.winfo_exists():
                        new_card.destroy()
                    return

            # حذف الرسائل القديمة من الواجهة فقط (تحسين الأداء)
            if len(self.live_messages) > self.max_live_messages:
                old_messages = self.live_messages[self.max_live_messages:]
                for old_msg in old_messages:
                    try:
                        if 'widget' in old_msg and old_msg['widget'] and old_msg['widget'].winfo_exists():
                            old_msg['widget'].destroy()
                    except Exception:
                        pass
                self.live_messages = self.live_messages[:self.max_live_messages]

        except Exception as e:
            print(f"خطأ في إضافة الرسالة للواجهة: {e}")
            import traceback
            traceback.print_exc()

    def create_live_message_card(self, message_data: dict, signal: Signal = None):
        """إنشاء بطاقة رسالة حية بتصميم أنيق"""
        # إطار البطاقة الرئيسي
        card = ctk.CTkFrame(
            self.live_messages_scroll,
            fg_color="#2b2b2b" if signal else "#3d2424",
            corner_radius=10
        )
        # لا نقوم بـ pack هنا، سيتم ذلك في الدالة المستدعية

        # رأس البطاقة
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(15, 10))

        # القناة والوقت
        channel_label = ctk.CTkLabel(
            header,
            text=f"📢 {message_data.get('channel_name', 'Unknown')}",
            font=("Arial", 14, "bold"),
            text_color="#64B5F6"
        )
        channel_label.pack(side="left")

        time_label = ctk.CTkLabel(
            header,
            text=f"🕐 {message_data.get('time', '')}",
            font=("Arial", 11),
            text_color="gray"
        )
        time_label.pack(side="right")

        # محتوى الرسالة
        if signal:
            # إشارة ناجحة - عرض تفصيلي
            self.create_signal_details(card, signal)
        else:
            # رسالة بدون إشارة
            msg_frame = ctk.CTkFrame(card, fg_color="#1a1a1a", corner_radius=5)
            msg_frame.pack(fill="x", padx=15, pady=10)

            ctk.CTkLabel(
                msg_frame,
                text="📝 محتوى الرسالة:",
                font=("Arial", 12, "bold"),
                text_color="#FFA726"
            ).pack(anchor="w", padx=10, pady=(10, 5))

            # نص الرسالة
            msg_text = ctk.CTkTextbox(
                msg_frame,
                height=80,
                font=("Courier New", 11),
                fg_color="#0d0d0d",
                wrap="word"
            )
            msg_text.pack(fill="x", padx=10, pady=(0, 10))
            msg_text.insert("1.0", message_data.get('message_text', ''))
            msg_text.configure(state="disabled")

            # تنبيه
            warning = ctk.CTkLabel(
                msg_frame,
                text="⚠️ لم يتم التعرف على إشارة في هذه الرسالة",
                font=("Arial", 11),
                text_color="#FF5252"
            )
            warning.pack(pady=(5, 5))

            # عرض معلومات التشخيص إذا كانت متوفرة
            if 'diagnostics' in message_data:
                diag = message_data['diagnostics']

                diag_frame = ctk.CTkFrame(msg_frame, fg_color="#0d0d0d", corner_radius=5)
                diag_frame.pack(fill="x", padx=10, pady=(0, 10))

                ctk.CTkLabel(
                    diag_frame,
                    text="🔍 تحليل الرسالة:",
                    font=("Arial", 11, "bold"),
                    text_color="#64B5F6"
                ).pack(anchor="w", padx=10, pady=(10, 5))

                # عرض كل عنصر من التشخيص
                items = [
                    ("الرمز", diag.get('symbol')),
                    ("نوع الصفقة", diag.get('action')),
                    ("سعر الدخول", diag.get('entry_price') or diag.get('entry_range')),
                    ("أهداف الربح", diag.get('take_profits')),
                    ("وقف الخسارة", diag.get('stop_loss'))
                ]

                for label, value in items:
                    item_frame = ctk.CTkFrame(diag_frame, fg_color="transparent")
                    item_frame.pack(fill="x", padx=10, pady=2)

                    icon = "✅" if value else "❌"
                    color = "#4CAF50" if value else "#FF5252"

                    value_text = str(value) if value else "غير موجود"
                    if isinstance(value, list) and value:
                        value_text = ", ".join(map(str, value))
                    elif isinstance(value, tuple) and value:
                        value_text = f"{value[0]} - {value[1]}"

                    ctk.CTkLabel(
                        item_frame,
                        text=f"{icon} {label}: {value_text}",
                        font=("Arial", 10),
                        text_color=color,
                        anchor="w"
                    ).pack(side="left", fill="x", expand=True, pady=3)

        return card

    def create_signal_details(self, parent, signal: Signal):
        """إنشاء تفاصيل الإشارة بشكل جميل"""
        details_frame = ctk.CTkFrame(parent, fg_color="#1a1a1a", corner_radius=5)
        details_frame.pack(fill="x", padx=15, pady=10)

        # الرمز ونوع الصفقة - عنوان كبير
        title_frame = ctk.CTkFrame(details_frame, fg_color="transparent")
        title_frame.pack(fill="x", padx=10, pady=(15, 10))

        symbol_label = ctk.CTkLabel(
            title_frame,
            text=f"🎯 {signal.symbol}",
            font=("Arial", 20, "bold"),
            text_color="#FFD700"
        )
        symbol_label.pack(side="left")

        action_color = "#4CAF50" if signal.action == "BUY" else "#f44336"
        action_emoji = "📈" if signal.action == "BUY" else "📉"
        action_label = ctk.CTkLabel(
            title_frame,
            text=f"{action_emoji} {signal.action}",
            font=("Arial", 18, "bold"),
            text_color=action_color
        )
        action_label.pack(side="right")

        # خط فاصل
        separator = ctk.CTkFrame(details_frame, height=2, fg_color="#333")
        separator.pack(fill="x", padx=10, pady=5)

        # شبكة المعلومات
        info_grid = ctk.CTkFrame(details_frame, fg_color="transparent")
        info_grid.pack(fill="x", padx=10, pady=10)

        # سعر الدخول
        entry_frame = ctk.CTkFrame(info_grid, fg_color="#0d47a1", corner_radius=5)
        entry_frame.pack(side="left", padx=5, pady=5, fill="both", expand=True)

        ctk.CTkLabel(
            entry_frame,
            text="🎫 سعر الدخول",
            font=("Arial", 11, "bold")
        ).pack(pady=(10, 5))

        entry_price_text = ""
        if signal.entry_price:
            entry_price_text = f"{signal.entry_price}"
        elif signal.entry_price_range:
            entry_price_text = f"{signal.entry_price_range[0]}-{signal.entry_price_range[1]}"

        ctk.CTkLabel(
            entry_frame,
            text=entry_price_text,
            font=("Arial", 16, "bold"),
            text_color="#fff"
        ).pack(pady=(0, 10))

        # وقف الخسارة
        sl_frame = ctk.CTkFrame(info_grid, fg_color="#c62828", corner_radius=5)
        sl_frame.pack(side="left", padx=5, pady=5, fill="both", expand=True)

        ctk.CTkLabel(
            sl_frame,
            text="🛑 وقف الخسارة",
            font=("Arial", 11, "bold")
        ).pack(pady=(10, 5))

        ctk.CTkLabel(
            sl_frame,
            text=f"{signal.stop_loss}" if signal.stop_loss else "N/A",
            font=("Arial", 16, "bold"),
            text_color="#fff"
        ).pack(pady=(0, 10))

        # أهداف الربح
        if signal.take_profits:
            tp_container = ctk.CTkFrame(details_frame, fg_color="transparent")
            tp_container.pack(fill="x", padx=10, pady=10)

            ctk.CTkLabel(
                tp_container,
                text="💰 أهداف الربح:",
                font=("Arial", 12, "bold"),
                text_color="#4CAF50"
            ).pack(anchor="w", pady=(0, 5))

            tp_grid = ctk.CTkFrame(tp_container, fg_color="transparent")
            tp_grid.pack(fill="x")

            for i, tp in enumerate(signal.take_profits, 1):
                tp_card = ctk.CTkFrame(tp_grid, fg_color="#1b5e20", corner_radius=5)
                tp_card.pack(side="left", padx=3, pady=3, fill="both", expand=True)

                ctk.CTkLabel(
                    tp_card,
                    text=f"TP{i}",
                    font=("Arial", 10, "bold")
                ).pack(pady=(8, 2))

                ctk.CTkLabel(
                    tp_card,
                    text=f"{tp}",
                    font=("Arial", 13, "bold"),
                    text_color="#fff"
                ).pack(pady=(0, 8))

    async def on_signal_received(self, signal: Signal):
        """معالجة الإشارة المستلمة - محسّنة مع نظام إعادة المحاولة"""
        # حفظ الإشارة
        signal_dict = signal.__dict__
        self.received_signals.append(signal_dict)
        self.save_signals()

        # حفظ في التقرير اليومي
        self.report_manager.save_signal(signal_dict)

        # إنشاء بيانات الرسالة للعرض
        from datetime import datetime
        message_data = {
            'channel_name': signal.channel_name,
            'time': datetime.now().strftime('%H:%M:%S'),
            'message_text': signal.raw_message
        }

        # إضافة للواجهة (بدون حجب)
        self.root.after(0, lambda: self.add_live_message_to_ui(message_data, signal))

        # تنفيذ الصفقة إذا كان التداول التلقائي مفعل
        settings = Config.load_settings()
        if settings.get('auto_trade', True):
            await self._execute_trade_with_retry(signal, signal_dict)

        # تحديث الواجهة (بدون حجب)
        self.root.after(0, self.refresh_signals)

    async def _execute_trade_with_retry(self, signal: Signal, signal_dict: dict, retry_count: int = 0):
        """تنفيذ الصفقة مع نظام إعادة المحاولة الذكي"""
        from datetime import datetime

        try:
            lot_size = float(self.lot_size_entry.get() or 0.01)

            # محاولة التنفيذ الفورية
            result = self.mt5_manager.execute_signal(signal, lot_size)

            if result['success']:
                # ===== نجح التنفيذ =====
                actual_symbol = result.get('actual_symbol', signal.symbol)
                symbol_display = f"{signal.symbol} ({actual_symbol})" if actual_symbol != signal.symbol else signal.symbol

                print(f"✅ تم تنفيذ الصفقة: {symbol_display} {signal.action} - Ticket: {result.get('ticket')}")

                # حفظ الصفقة في التقرير اليومي
                trade_data = {
                    'ticket': result.get('ticket'),
                    'signal': signal_dict,
                    'actual_symbol': actual_symbol,
                    'entry_price': result.get('price'),
                    'lot_size': lot_size,
                    'opened_at': datetime.now().isoformat(),
                    'status': 'executed'
                }
                self.report_manager.save_trade(trade_data)

                # إزالة من قائمة الانتظار
                self.pending_trades = [t for t in self.pending_trades if t['signal'].symbol != signal.symbol]

                # إظهار إشعار نجاح
                success_msg = f"✅ تم فتح صفقة {signal.action} على {symbol_display}"
                self.root.after(0, lambda msg=success_msg: self.show_toast(msg, "success", 4000))
            else:
                # ===== فشل التنفيذ - معالجة ذكية =====
                error_msg = result.get('error', 'خطأ غير معروف')
                error_code = result.get('error_code', 0)
                
                print(f"❌ فشل تنفيذ الصفقة (محاولة {retry_count + 1}/{self.max_retry_attempts}): {error_msg}")

                # ===== معالجة حالات خاصة =====
                # حالة 1: التداول التلقائي معطل (10027)
                if error_code == 10027:
                    print("⚠️ السبب: التداول التلقائي معطل في MT5")
                    
                    # إضافة للقائمة المعلقة بحالة خاصة
                    pending_trade = {
                        'signal': signal,
                        'signal_dict': signal_dict,
                        'lot_size': lot_size,
                        'retry_count': 0,  # إعادة تعيين العداد
                        'last_error': error_msg,
                        'error_code': error_code,
                        'timestamp': datetime.now(),
                        'status': 'awaiting_autotrading',
                        'requires_manual_fix': True
                    }
                    
                    # إضافة فقط إذا لم تكن موجودة
                    if not any(t['signal'].symbol == signal.symbol for t in self.pending_trades):
                        self.pending_trades.append(pending_trade)
                    
                    # إشعار خاص
                    self.root.after(0, lambda: self.show_toast(
                        f"⚠️ صفقة {signal.symbol} في الانتظار - يجب تفعيل التداول التلقائي",
                        "warning", 6000
                    ))
                    
                    # لا نعيد المحاولة تلقائياً - ننتظر التفعيل اليدوي
                    return
                
                # حالة 2: لا توجد أموال كافية (10019)
                elif error_code == 10019:
                    print("⚠️ السبب: لا توجد أموال كافية")
                    self.root.after(0, lambda: self.show_toast(
                        f"❌ صفقة {signal.symbol}: رصيد غير كافٍ",
                        "error", 5000
                    ))
                    # لا نعيد المحاولة - مشكلة دائمة
                    return
                
                # حالة 3: السوق مغلق (10018)
                elif error_code == 10018:
                    print("⚠️ السبب: السوق مغلق")
                    # يمكن إعادة المحاولة لاحقاً
                    if retry_count < self.max_retry_attempts:
                        pending_trade = {
                            'signal': signal,
                            'signal_dict': signal_dict,
                            'lot_size': lot_size,
                            'retry_count': retry_count + 1,
                            'last_error': error_msg,
                            'error_code': error_code,
                            'timestamp': datetime.now(),
                            'status': 'market_closed'
                        }
                        
                        if not any(t['signal'].symbol == signal.symbol for t in self.pending_trades):
                            self.pending_trades.append(pending_trade)
                        
                        self.root.after(0, lambda: self.show_toast(
                            f"⏰ صفقة {signal.symbol}: السوق مغلق - سنحاول لاحقاً",
                            "info", 4000
                        ))
                        
                        # إعادة المحاولة بعد 60 ثانية
                        await asyncio.sleep(60)
                        await self._execute_trade_with_retry(signal, signal_dict, retry_count + 1)
                    return
                
                # ===== حالات عامة - إعادة محاولة عادية =====
                if retry_count < self.max_retry_attempts:
                    # إضافة للقائمة المعلقة
                    pending_trade = {
                        'signal': signal,
                        'signal_dict': signal_dict,
                        'lot_size': lot_size,
                        'retry_count': retry_count + 1,
                        'last_error': error_msg,
                        'error_code': error_code,
                        'timestamp': datetime.now(),
                        'status': 'retrying'
                    }
                    
                    # تحديث أو إضافة
                    existing_idx = next((i for i, t in enumerate(self.pending_trades) 
                                       if t['signal'].symbol == signal.symbol), None)
                    if existing_idx is not None:
                        self.pending_trades[existing_idx] = pending_trade
                    else:
                        self.pending_trades.append(pending_trade)

                    self.root.after(0, lambda: self.show_toast(
                        f"⏳ صفقة {signal.symbol} - محاولة {retry_count + 1}/{self.max_retry_attempts}",
                        "warning", 3000
                    ))

                    # إعادة المحاولة بعد 10 ثوان
                    await asyncio.sleep(10)
                    await self._execute_trade_with_retry(signal, signal_dict, retry_count + 1)
                else:
                    # ===== فشل نهائي =====
                    self.root.after(0, lambda: self.show_toast(
                        f"❌ فشل تنفيذ صفقة {signal.symbol} بعد {self.max_retry_attempts} محاولات",
                        "error", 5000
                    ))

                    # إزالة من قائمة الانتظار
                    self.pending_trades = [t for t in self.pending_trades 
                                          if t['signal'].symbol != signal.symbol]

        except Exception as e:
            error_msg = f"خطأ في تنفيذ الصفقة: {str(e)}"
            print(f"❌ {error_msg}")
            self.root.after(0, lambda: self.show_toast(error_msg, "error", 4000))

    async def on_message_received(self, message_data: dict, signal: Signal = None):
        """معالجة جميع الرسائل الواردة (ناجحة أو فاشلة)"""
        # إضافة الرسالة للواجهة
        self.root.after(0, lambda: self.add_live_message_to_ui(message_data, signal))

    def refresh_channels(self):
        """تحديث قائمة القنوات"""
        if not self.telegram_client:
            return

        # مسح القائمة الحالية
        for widget in self.channels_scroll.winfo_children():
            widget.destroy()

        channels = self.telegram_client.get_channels()

        for channel in channels:
            self.create_channel_card(channel)

    def create_channel_card(self, channel: dict):
        """إنشاء بطاقة قناة"""
        card = ctk.CTkFrame(self.channels_scroll)
        card.pack(fill="x", padx=10, pady=5)

        # معلومات القناة
        info_frame = ctk.CTkFrame(card)
        info_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            info_frame, text=channel['name'],
            font=("Arial", 14, "bold")
        ).pack(anchor="w")

        status_color = "green" if channel['status'] == 'active' else "gray"
        status_text = "🟢 نشطة" if channel['status'] == 'active' else "⚪ معطلة"

        ctk.CTkLabel(
            info_frame, text=status_text,
            font=("Arial", 11), text_color=status_color
        ).pack(anchor="w")

        ctk.CTkLabel(
            info_frame, text=f"عدد الإشارات: {channel.get('signal_count', 0)}",
            font=("Arial", 11)
        ).pack(anchor="w")

        # أزرار التحكم
        actions_frame = ctk.CTkFrame(card)
        actions_frame.pack(side="right", padx=10, pady=10)

        ctk.CTkButton(
            actions_frame, text="تبديل الحالة",
            width=100, height=30,
            command=lambda: self.toggle_channel(channel['id'])
        ).pack(pady=2)

        ctk.CTkButton(
            actions_frame, text="حذف",
            width=100, height=30,
            fg_color="red", hover_color="darkred",
            command=lambda: self.remove_channel(channel['id'])
        ).pack(pady=2)

    def toggle_channel(self, channel_id: int):
        """تبديل حالة القناة"""
        if self.telegram_client:
            self.telegram_client.toggle_channel_status(channel_id)
            self.refresh_channels()

    def remove_channel(self, channel_id: int):
        """حذف قناة"""
        if messagebox.askyesno("تأكيد", "هل أنت متأكد من حذف هذه القناة؟"):
            if self.telegram_client:
                self.telegram_client.remove_channel(channel_id)
                self.refresh_channels()

    def activate_all_channels(self):
        """تفعيل جميع القنوات"""
        if not self.telegram_client:
            messagebox.showerror("خطأ", "يجب الاتصال بالتليجرام أولاً")
            return

        channels = self.telegram_client.get_channels()
        inactive_count = len([ch for ch in channels if ch.get('status') != 'active'])

        if inactive_count == 0:
            messagebox.showinfo("تنبيه", "جميع القنوات مفعلة بالفعل")
            return

        if messagebox.askyesno("تأكيد", f"هل تريد تفعيل {inactive_count} قناة؟"):
            for channel in channels:
                if channel.get('status') != 'active':
                    channel['status'] = 'active'

            self.telegram_client.save_channels()
            self.refresh_channels()
            messagebox.showinfo("نجح", f"تم تفعيل {inactive_count} قناة ✅")

    def deactivate_all_channels(self):
        """تعطيل جميع القنوات"""
        if not self.telegram_client:
            messagebox.showerror("خطأ", "يجب الاتصال بالتليجرام أولاً")
            return

        channels = self.telegram_client.get_channels()
        active_count = len([ch for ch in channels if ch.get('status') == 'active'])

        if active_count == 0:
            messagebox.showinfo("تنبيه", "جميع القنوات معطلة بالفعل")
            return

        if messagebox.askyesno("تأكيد", f"هل تريد تعطيل {active_count} قناة؟"):
            for channel in channels:
                if channel.get('status') == 'active':
                    channel['status'] = 'inactive'

            self.telegram_client.save_channels()
            self.refresh_channels()
            messagebox.showinfo("نجح", f"تم تعطيل {active_count} قناة ⏸️")

    def refresh_signals(self):
        """تحديث قائمة الإشارات والصفقات المعلقة"""
        # مسح القائمة الحالية
        for widget in self.signals_scroll.winfo_children():
            widget.destroy()

        self.load_signals()

        # عرض الصفقات المعلقة أولاً
        if self.pending_trades:
            pending_header = ctk.CTkFrame(self.signals_scroll, fg_color="#2d1f1f", corner_radius=10)
            pending_header.pack(fill="x", padx=10, pady=(10, 5))
            
            ctk.CTkLabel(
                pending_header,
                text=f"⏳ صفقات معلقة ({len(self.pending_trades)})",
                font=("Arial", 16, "bold"),
                text_color="#FFA726"
            ).pack(pady=10)
            
            for pending in self.pending_trades:
                self.create_pending_trade_card(pending)
        
        # عرض الإشارات العادية
        for signal_data in reversed(self.received_signals[-20:]):  # آخر 20 إشارة
            self.create_signal_card(signal_data)
        
        # تحديث العداد
        if hasattr(self, 'pending_count_label'):
            self.pending_count_label.configure(text=f"معلق: {len(self.pending_trades)}")
    
    def create_pending_trade_card(self, pending: dict):
        """إنشاء بطاقة صفقة معلقة"""
        signal = pending['signal']
        
        card = ctk.CTkFrame(self.signals_scroll, fg_color="#3d2424", corner_radius=8, border_width=2, border_color="#FFA726")
        card.pack(fill="x", padx=10, pady=5)

        # الرأس
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(15, 10))

        symbol_label = ctk.CTkLabel(
            header, text=f"⏳ {signal.symbol} - {signal.action}",
            font=("Arial", 14, "bold"),
            text_color="#FFA726"
        )
        symbol_label.pack(side="left")

        # الحالة
        status_text = {
            'awaiting_autotrading': '🔴 ينتظر تفعيل التداول التلقائي',
            'market_closed': '🕐 السوق مغلق',
            'retrying': f'🔄 إعادة محاولة ({pending["retry_count"]}/{self.max_retry_attempts})',
            'pending': '⏳ في الانتظار'
        }.get(pending.get('status'), '⏳ في الانتظار')
        
        status_label = ctk.CTkLabel(
            header, text=status_text,
            font=("Arial", 11),
            text_color="#FFA726"
        )
        status_label.pack(side="right")

        # التفاصيل
        details = ctk.CTkFrame(card, fg_color="transparent")
        details.pack(fill="x", padx=15, pady=5)

        ctk.CTkLabel(
            details, text=f"❌ آخر خطأ: {pending['last_error']}",
            font=("Arial", 10),
            text_color="#FF5252"
        ).pack(anchor="w")
        
        from datetime import datetime
        timestamp = pending.get('timestamp')
        if isinstance(timestamp, datetime):
            time_str = timestamp.strftime('%H:%M:%S')
            ctk.CTkLabel(
                details, text=f"🕐 الوقت: {time_str}",
                font=("Arial", 10),
                text_color="gray"
            ).pack(anchor="w")

        # أزرار الإجراءات
        if pending.get('requires_manual_fix'):
            actions = ctk.CTkFrame(card, fg_color="transparent")
            actions.pack(fill="x", padx=15, pady=(5, 15))
            
            ctk.CTkLabel(
                actions,
                text="⚠️ يتطلب تفعيل التداول التلقائي يدوياً من MT5",
                font=("Arial", 10, "italic"),
                text_color="#FFA726"
            ).pack(anchor="w")
    
    def retry_pending_trades(self):
        """إعادة محاولة جميع الصفقات المعلقة"""
        if not self.pending_trades:
            self.show_toast("لا توجد صفقات معلقة", "info", 2000)
            return
        
        count = len(self.pending_trades)
        
        if not messagebox.askyesno(
            "تأكيد",
            f"هل تريد إعادة محاولة {count} صفقة معلقة؟"
        ):
            return
        
        async def retry_all():
            retried = 0
            for pending in list(self.pending_trades):  # نسخة لتجنب التعديل أثناء التكرار
                try:
                    signal = pending['signal']
                    signal_dict = pending['signal_dict']
                    
                    # إعادة تعيين العداد
                    await self._execute_trade_with_retry(signal, signal_dict, 0)
                    retried += 1
                    
                    # انتظار قصير بين الصفقات
                    await asyncio.sleep(2)
                except Exception as e:
                    print(f"خطأ في إعادة محاولة الصفقة: {e}")
            
            self.root.after(0, lambda: self.show_toast(
                f"تمت إعادة محاولة {retried} صفقة",
                "success", 3000
            ))
            
            # تحديث العرض
            self.root.after(0, self.refresh_signals)
        
        asyncio.run_coroutine_threadsafe(retry_all(), self.loop)

    def create_signal_card(self, signal_data: dict):
        """إنشاء بطاقة إشارة"""
        card = ctk.CTkFrame(self.signals_scroll)
        card.pack(fill="x", padx=10, pady=5)

        # الرأس
        header = ctk.CTkFrame(card)
        header.pack(fill="x", padx=10, pady=5)

        # عرض نوع الأمر (MARKET أو PENDING)
        order_type = signal_data.get('order_type', 'MARKET')
        order_emoji = "⚡" if order_type == "MARKET" else "⏰"
        
        # ترجمة نوع الأمر
        order_type_ar = {
            'MARKET': 'فوري',
            'BUY_LIMIT': 'شراء معلق (Limit)',
            'SELL_LIMIT': 'بيع معلق (Limit)',
            'BUY_STOP': 'شراء معلق (Stop)',
            'SELL_STOP': 'بيع معلق (Stop)'
        }.get(order_type, order_type)
        
        symbol_label = ctk.CTkLabel(
            header, text=f"{order_emoji} {signal_data['symbol']} - {signal_data['action']} ({order_type_ar})",
            font=("Arial", 14, "bold")
        )
        symbol_label.pack(side="left")

        channel_label = ctk.CTkLabel(
            header, text=signal_data.get('channel_name', 'Unknown'),
            font=("Arial", 11)
        )
        channel_label.pack(side="right")

        # التفاصيل
        details = ctk.CTkFrame(card)
        details.pack(fill="x", padx=10, pady=5)

        entry_text = f"الدخول: {signal_data.get('entry_price', 'N/A')}"
        if signal_data.get('entry_price_range'):
            entry_text = f"الدخول: {signal_data['entry_price_range'][0]} - {signal_data['entry_price_range'][1]}"

        ctk.CTkLabel(details, text=entry_text, font=("Arial", 11)).pack(anchor="w")

        tps_text = "TP: " + ", ".join([str(tp) for tp in signal_data.get('take_profits', [])])
        ctk.CTkLabel(details, text=tps_text, font=("Arial", 11), text_color="green").pack(anchor="w")

        sl_text = f"SL: {signal_data.get('stop_loss', 'N/A')}"
        ctk.CTkLabel(details, text=sl_text, font=("Arial", 11), text_color="red").pack(anchor="w")

        # الحالة
        status_color = {"pending": "orange", "executed": "green", "failed": "red"}
        status_text = {"pending": "⏳ بانتظار التنفيذ", "executed": "✅ تم التنفيذ", "failed": "❌ فشل"}

        status = signal_data.get('status', 'pending')
        ctk.CTkLabel(
            card, text=status_text.get(status, status),
            font=("Arial", 11), text_color=status_color.get(status, "gray")
        ).pack(padx=10, pady=5)

    def refresh_positions(self):
        """تحديث الصفقات المفتوحة"""
        # مسح القائمة الحالية
        for widget in self.positions_scroll.winfo_children():
            widget.destroy()

        positions = self.mt5_manager.get_open_positions()

        if not positions:
            ctk.CTkLabel(
                self.positions_scroll,
                text="لا توجد صفقات مفتوحة",
                font=("Arial", 14)
            ).pack(pady=50)
            return

        for pos in positions:
            self.create_position_card(pos)

    def create_position_card(self, pos: dict):
        """إنشاء بطاقة صفقة"""
        card = ctk.CTkFrame(self.positions_scroll)
        card.pack(fill="x", padx=10, pady=5)

        # معلومات الصفقة
        info_frame = ctk.CTkFrame(card)
        info_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            info_frame, text=f"#{pos['ticket']} - {pos['symbol']} {pos['type']}",
            font=("Arial", 14, "bold")
        ).pack(anchor="w")

        ctk.CTkLabel(
            info_frame, text=f"الحجم: {pos['volume']} | الدخول: {pos['price_open']} | الحالي: {pos['price_current']}",
            font=("Arial", 11)
        ).pack(anchor="w")

        ctk.CTkLabel(
            info_frame, text=f"SL: {pos['sl']} | TP: {pos['tp']}",
            font=("Arial", 11)
        ).pack(anchor="w")

        # الربح/الخسارة
        profit_color = "green" if pos['profit'] >= 0 else "red"
        profit_text = f"+${pos['profit']:.2f}" if pos['profit'] >= 0 else f"-${abs(pos['profit']):.2f}"

        ctk.CTkLabel(
            card, text=profit_text,
            font=("Arial", 16, "bold"), text_color=profit_color
        ).pack(side="right", padx=20)

    def export_signals_csv(self):
        """تصدير الإشارات إلى CSV"""
        if not self.received_signals:
            self.show_toast("لا توجد إشارات للتصدير", "warning")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if filename:
            try:
                with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=self.received_signals[0].keys())
                    writer.writeheader()
                    writer.writerows(self.received_signals)

                self.show_toast(f"تم تصدير {len(self.received_signals)} إشارة بنجاح", "success")
            except Exception as e:
                self.show_toast(f"فشل التصدير: {str(e)}", "error")

    def export_signals_json(self):
        """تصدير الإشارات إلى JSON"""
        if not self.received_signals:
            self.show_toast("لا توجد إشارات للتصدير", "warning")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.received_signals, f, indent=4, ensure_ascii=False)

                self.show_toast(f"تم تصدير {len(self.received_signals)} إشارة بنجاح", "success")
            except Exception as e:
                self.show_toast(f"فشل التصدير: {str(e)}", "error")

    def save_signals(self):
        """حفظ الإشارات"""
        try:
            with open(self.signals_file, 'w', encoding='utf-8') as f:
                json.dump(self.received_signals, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"خطأ في حفظ الإشارات: {str(e)}")

    def load_signals(self):
        """تحميل الإشارات"""
        try:
            if os.path.exists(self.signals_file):
                with open(self.signals_file, 'r', encoding='utf-8') as f:
                    self.received_signals = json.load(f)
        except Exception as e:
            print(f"خطأ في تحميل الإشارات: {str(e)}")

    def update_balance(self):
        """تحديث الرصيد (دالة بسيطة للاستخدام المباشر)"""
        self._update_balance_async()

    def schedule_updates(self):
        """جدولة التحديثات الدورية - محسّنة للأداء"""
        self._update_counter = 0  # عداد للتحديثات

        def update():
            if self._is_closing:
                return
                
            try:
                self._update_counter += 1

                if self.mt5_manager.is_connected:
                    # تحديث الرصيد فقط كل 10 ثوان (تقليل الضغط)
                    if self._update_counter % 2 == 0:
                        threading.Thread(
                            target=self._update_balance_async,
                            daemon=True
                        ).start()

                    # تحديث لوحة التحكم فقط كل 15 ثانية
                    if self._update_counter % 3 == 0:
                        threading.Thread(
                            target=self._update_dashboard_async,
                            daemon=True
                        ).start()

                # تحديث حالة التداول التلقائي (سريع، يمكن في main thread)
                self.update_auto_trade_status()

            except Exception as e:
                print(f"⚠️ خطأ في التحديث الدوري: {e}")

            # جدولة التحديث التالي
            if not self._is_closing:
                self.root.after(5000, update)  # كل 5 ثوان

        # بدء التحديثات
        self.root.after(2000, update)  # أول تحديث بعد ثانيتين

    def _update_balance_async(self):
        """تحديث الرصيد في thread منفصل"""
        if self._is_closing:
            return
            
        try:
            account_info = self.mt5_manager.get_account_info()
            if account_info and not self._is_closing:
                self.root.after(0, lambda: self._safe_update_balance(account_info))
        except Exception as e:
            print(f"⚠️ خطأ في تحديث الرصيد: {e}")
    
    def _safe_update_balance(self, account_info):
        """تحديث الرصيد بشكل آمن في main thread"""
        try:
            if self.root.winfo_exists() and hasattr(self, 'balance_label'):
                if self.balance_label.winfo_exists():
                    self.balance_label.configure(text=f"${account_info['balance']:.2f}")
        except Exception as e:
            print(f"⚠️ خطأ في تطبيق تحديث الرصيد: {e}")

    def _update_dashboard_async(self):
        """تحديث لوحة التحكم في thread منفصل"""
        if self._is_closing:
            return
            
        try:
            stats = self.mt5_manager.get_today_statistics()
            if not self._is_closing:
                # تحديث في main thread
                self.root.after(0, lambda: self._apply_dashboard_updates(stats))
        except Exception as e:
            print(f"⚠️ خطأ في تحديث لوحة التحكم: {e}")

    def _apply_dashboard_updates(self, stats: dict):
        """تطبيق تحديثات لوحة التحكم في main thread - محسّنة"""
        if self._is_closing:
            return
            
        try:
            # التحقق من وجود الـ widgets قبل التحديث
            if self.root.winfo_exists():
                if hasattr(self, 'total_trades_label') and self.total_trades_label.winfo_exists():
                    self.total_trades_label.configure(text=str(stats['total_trades']))
                
                if hasattr(self, 'profit_label') and self.profit_label.winfo_exists():
                    self.profit_label.configure(
                        text=f"${stats['total_profit']:.2f}",
                        text_color="green" if stats['total_profit'] >= 0 else "red"
                    )
                
                if hasattr(self, 'winrate_label') and self.winrate_label.winfo_exists():
                    self.winrate_label.configure(text=f"{stats['win_rate']:.1f}%")

                # تحديث عدد الصفقات المعلقة
                pending_count = len(self.pending_trades)
                if hasattr(self, 'pending_trades_label') and self.pending_trades_label.winfo_exists():
                    self.pending_trades_label.configure(text=str(pending_count))

                if self.telegram_client:
                    channels = self.telegram_client.get_channels()
                    active = len([ch for ch in channels if ch['status'] == 'active'])
                    if hasattr(self, 'active_channels_label') and self.active_channels_label.winfo_exists():
                        self.active_channels_label.configure(text=str(active))
        except Exception as e:
            print(f"⚠️ خطأ في تطبيق تحديثات لوحة التحكم: {e}")

    def schedule_memory_cleanup(self):
        """جدولة تنظيف الذاكرة الدوري لمنع تراكم الـ widgets"""
        def cleanup():
            if self._is_closing:
                return
                
            try:
                # تنظيف الرسائل القديمة جداً من الذاكرة
                if len(self.live_messages) > 100:
                    # حذف أقدم 50 رسالة من الذاكرة
                    old_messages = self.live_messages[100:]
                    for old_msg in old_messages:
                        try:
                            if 'widget' in old_msg and old_msg['widget']:
                                if old_msg['widget'].winfo_exists():
                                    old_msg['widget'].destroy()
                        except Exception:
                            pass
                    self.live_messages = self.live_messages[:100]
                    print(f"� تم تنظيف الذاكرة - الرسائل المتبقية: {len(self.live_messages)}")
                
                # تحديث الواجهة لمنع الشفافية
                try:
                    if self.root.winfo_exists():
                        self.root.update_idletasks()
                        # التأكد من عدم تحول النافذة للشفافية
                        if self.root.attributes('-alpha') < 1.0:
                            self.root.attributes('-alpha', 1.0)
                except Exception as e:
                    print(f"تحذير في تحديث الواجهة: {e}")
                
            except Exception as e:
                print(f"⚠️ خطأ في تنظيف الذاكرة: {e}")
            
            # إعادة الجدولة كل 5 دقائق
            if not self._is_closing:
                self.root.after(300000, cleanup)  # 5 دقائق = 300000 ميلي ثانية
        
        # بدء التنظيف بعد 5 دقائق من التشغيل
        self.root.after(300000, cleanup)

    def on_closing(self):
        """معالج إغلاق التطبيق بشكل آمن"""
        if messagebox.askokcancel("خروج", "هل أنت متأكد من الخروج؟"):
            self._is_closing = True
            print("⏳ جارٍ إغلاق البرنامج...")

            # إيقاف الاتصالات
            if self.telegram_client and self.telegram_client.is_connected:
                try:
                    future = asyncio.run_coroutine_threadsafe(
                        self.telegram_client.disconnect(),
                        self.loop
                    )
                    future.result(timeout=3)
                    print("✅ تم إغلاق اتصال Telegram")
                except Exception as e:
                    print(f"⚠️ تحذير: مشكلة في إغلاق Telegram: {e}")

            if self.mt5_manager.is_connected:
                try:
                    self.mt5_manager.disconnect()
                    print("✅ تم إغلاق اتصال MT5")
                except Exception as e:
                    print(f"⚠️ تحذير: مشكلة في إغلاق MT5: {e}")

            # إيقاف حلقة asyncio
            if self.loop and self.loop.is_running():
                try:
                    self.loop.call_soon_threadsafe(self.loop.stop)
                except Exception as e:
                    print(f"⚠️ تحذير: مشكلة في إيقاف حلقة asyncio: {e}")

            # إغلاق النافذة
            try:
                self.root.quit()
                self.root.destroy()
            except Exception as e:
                print(f"⚠️ تحذير: مشكلة في إغلاق النافذة: {e}")
            
            print("✅ تم إغلاق البرنامج بنجاح")

    def update_auto_trade_status(self):
        """تحديث حالة التداول التلقائي في شريط الحالة"""
        settings = Config.load_settings()
        auto_trade_enabled = settings.get('auto_trade', True)

        if auto_trade_enabled:
            self.auto_trade_status_label.configure(
                text="🤖 مفعّل",
                text_color="green"
            )
        else:
            self.auto_trade_status_label.configure(
                text="⏸️ معطّل",
                text_color="orange"
            )

    def run(self):
        """تشغيل التطبيق"""
        self.root.mainloop()

    def on_close(self):
        """معالجة إغلاق النافذة - استبدلت بـ on_closing"""
        self.on_closing()

    def load_saved_credentials(self):
        """تحميل بيانات الاعتماد المحفوظة"""
        # تحميل بيانات Telegram
        telegram_creds = self.credential_manager.get_telegram_credentials()
        if telegram_creds:
            Config.API_ID = telegram_creds.get('api_id', '')
            Config.API_HASH = telegram_creds.get('api_hash', '')
            Config.PHONE_NUMBER = telegram_creds.get('phone', '')
            print("✅ تم تحميل بيانات Telegram المحفوظة")

        # تحميل بيانات MT5
        mt5_creds = self.credential_manager.get_mt5_credentials()
        if mt5_creds:
            Config.MT5_LOGIN = mt5_creds.get('login', '')
            Config.MT5_PASSWORD = mt5_creds.get('password', '')
            Config.MT5_SERVER = mt5_creds.get('server', '')
            print("✅ تم تحميل بيانات MT5 المحفوظة")

    def auto_connect_on_startup(self):
        """محاولة الاتصال التلقائي بـ MT5 عند بدء التطبيق"""
        # التحقق من تفعيل الاتصال التلقائي في الإعدادات
        settings = Config.load_settings()
        if not settings.get('auto_connect_mt5', True):
            print("ℹ️ الاتصال التلقائي بـ MT5 معطل في الإعدادات")
            return

        # التحقق من وجود بيانات MT5 المحفوظة
        mt5_creds = self.credential_manager.get_mt5_credentials()

        if mt5_creds and mt5_creds.get('login') and mt5_creds.get('password') and mt5_creds.get('server'):
            # محاولة الاتصال اليدوي بالبيانات المحفوظة
            print("🔄 محاولة الاتصال بـ MT5 باستخدام البيانات المحفوظة...")

            try:
                login = int(mt5_creds['login'])
                password = mt5_creds['password']
                server = mt5_creds['server']

                success = self.mt5_manager.connect(login, password, server)

                if success:
                    self.mt5_status_label.configure(text="🟢 متصل (تلقائي)", text_color="green")
                    self.update_balance()
                    print(f"✅ تم الاتصال التلقائي بـ MT5 - الحساب: {login}")
                else:
                    # إذا فشل الاتصال اليدوي، نجرب الاتصال التلقائي
                    print("⚠️ فشل الاتصال بالبيانات المحفوظة، جاري محاولة الاتصال التلقائي...")
                    self.try_auto_connector()
            except Exception as e:
                print(f"⚠️ خطأ في الاتصال بالبيانات المحفوظة: {e}")
                self.try_auto_connector()
        else:
            # إذا لم توجد بيانات محفوظة، نجرب الاتصال التلقائي
            print("🔄 لا توجد بيانات MT5 محفوظة، جاري محاولة الاتصال التلقائي...")
            self.try_auto_connector()

    def try_auto_connector(self):
        """محاولة الاتصال التلقائي بالحساب المفتوح في MT5"""
        try:
            success = self.mt5_manager.connect_auto()

            if success:
                self.mt5_status_label.configure(text="🟢 متصل (تلقائي)", text_color="green")
                self.update_balance()

                # تحديث الحقول بمعلومات الحساب المكتشف
                account_info = self.mt5_manager.account_info
                if account_info:
                    self.mt5_login_entry.delete(0, 'end')
                    self.mt5_login_entry.insert(0, str(account_info.login))
                    self.mt5_server_entry.delete(0, 'end')
                    self.mt5_server_entry.insert(0, account_info.server)

                print(f"✅ تم الاتصال التلقائي بـ MT5 بنجاح")
            else:
                print("ℹ️ لم يتم العثور على حساب MT5 مفتوح - يمكنك الاتصال يدوياً")

        except Exception as e:
            print(f"⚠️ خطأ في محاولة الاتصال التلقائي: {e}")

    def show_all_channels(self):
        """عرض جميع القنوات التي انضم لها المستخدم"""
        if not self.telegram_client or not self.telegram_client.is_connected:
            messagebox.showerror("خطأ", "يجب الاتصال بالتليجرام أولاً")
            return

        # إنشاء نافذة جديدة
        channels_window = ctk.CTkToplevel(self.root)
        channels_window.title("جميع القنوات")
        channels_window.geometry("900x700")

        # قاموس لتخزين checkboxes القنوات
        self.channel_checkboxes = {}
        self.all_channels_data = []

        # العنوان
        title_frame = ctk.CTkFrame(channels_window)
        title_frame.pack(fill="x", padx=20, pady=20)

        ctk.CTkLabel(
            title_frame,
            text="اختر القنوات التي تريد مراقبتها",
            font=("Arial", 18, "bold")
        ).pack(side="left")

        # أزرار التحديث
        buttons_frame = ctk.CTkFrame(title_frame)
        buttons_frame.pack(side="right")

        ctk.CTkButton(
            buttons_frame,
            text="تحديث",
            command=lambda: self.load_all_channels(channels_scroll, channels_window),
            width=80
        ).pack(side="right", padx=5)

        # شريط التحكم بالتحديد
        selection_frame = ctk.CTkFrame(channels_window)
        selection_frame.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkButton(
            selection_frame,
            text="✓ تحديد الكل",
            command=self.select_all_channels,
            width=120,
            fg_color="#2196F3",
            hover_color="#1976D2"
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            selection_frame,
            text="✗ إلغاء تحديد الكل",
            command=self.deselect_all_channels,
            width=150,
            fg_color="#607D8B",
            hover_color="#455A64"
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            selection_frame,
            text="تحديد القنوات فقط",
            command=lambda: self.select_channels_only(True),
            width=140,
            fg_color="#00BCD4",
            hover_color="#0097A7"
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            selection_frame,
            text="تحديد المجموعات فقط",
            command=lambda: self.select_channels_only(False),
            width=150,
            fg_color="#009688",
            hover_color="#00796B"
        ).pack(side="left", padx=5)

        # زر إضافة المحددة
        ctk.CTkButton(
            selection_frame,
            text="➕ إضافة المحددة",
            command=lambda: self.add_selected_channels(channels_scroll, channels_window),
            width=140,
            fg_color="green",
            hover_color="darkgreen",
            font=("Arial", 13, "bold")
        ).pack(side="right", padx=5)

        # عداد المحددة
        self.selected_count_label = ctk.CTkLabel(
            selection_frame,
            text="المحدد: 0",
            font=("Arial", 12, "bold")
        )
        self.selected_count_label.pack(side="right", padx=10)

        # منطقة القنوات
        channels_scroll = ctk.CTkScrollableFrame(channels_window, height=450)
        channels_scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # تحميل القنوات
        self.load_all_channels(channels_scroll, channels_window)

    def load_all_channels(self, scroll_frame, channels_window):
        """تحميل جميع القنوات في الإطار"""
        # مسح المحتوى الحالي
        for widget in scroll_frame.winfo_children():
            widget.destroy()

        # مسح القاموس
        self.channel_checkboxes = {}
        self.all_channels_data = []

        # عرض رسالة تحميل
        loading_label = ctk.CTkLabel(
            scroll_frame,
            text="⏳ جارٍ تحميل القنوات...",
            font=("Arial", 14)
        )
        loading_label.pack(pady=50)

        # تحميل القنوات في thread منفصل
        async def do_load():
            channels = await self.telegram_client.get_all_joined_channels()

            # تحديث الواجهة
            self.root.after(0, lambda: self.display_all_channels(scroll_frame, channels))

        asyncio.run_coroutine_threadsafe(do_load(), self.loop)

    def display_all_channels(self, scroll_frame, channels):
        """عرض القنوات في الواجهة"""
        # مسح رسالة التحميل
        for widget in scroll_frame.winfo_children():
            widget.destroy()

        if not channels:
            ctk.CTkLabel(
                scroll_frame,
                text="لم يتم العثور على قنوات",
                font=("Arial", 14)
            ).pack(pady=50)
            return

        # حفظ بيانات القنوات
        self.all_channels_data = channels

        # عرض القنوات
        for channel in channels:
            self.create_selectable_channel_card_with_checkbox(scroll_frame, channel)

        # تحديث العداد
        self.update_selected_count()

    def create_selectable_channel_card(self, parent, channel):
        """إنشاء بطاقة قناة قابلة للاختيار"""
        card = ctk.CTkFrame(parent)
        card.pack(fill="x", padx=10, pady=5)

        # معلومات القناة
        info_frame = ctk.CTkFrame(card)
        info_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        # الاسم
        name_text = channel['name']
        if channel.get('username'):
            name_text += f" (@{channel['username']})"

        ctk.CTkLabel(
            info_frame,
            text=name_text,
            font=("Arial", 13, "bold")
        ).pack(anchor="w")

        # النوع
        type_text = "📢 قناة" if channel['is_channel'] else "👥 مجموعة"
        if channel.get('participants_count'):
            type_text += f" | {channel['participants_count']} عضو"

        ctk.CTkLabel(
            info_frame,
            text=type_text,
            font=("Arial", 11)
        ).pack(anchor="w")

        # الحالة
        if channel['is_monitored']:
            status_label = ctk.CTkLabel(
                info_frame,
                text="✅ تتم مراقبتها",
                font=("Arial", 11),
                text_color="green"
            )
        else:
            status_label = ctk.CTkLabel(
                info_frame,
                text="⚪ غير مراقبة",
                font=("Arial", 11),
                text_color="gray"
            )
        status_label.pack(anchor="w")

        # زر الإضافة/الإزالة
        actions_frame = ctk.CTkFrame(card)
        actions_frame.pack(side="right", padx=10, pady=10)

        if channel['is_monitored']:
            ctk.CTkButton(
                actions_frame,
                text="إزالة",
                width=100,
                fg_color="red",
                hover_color="darkred",
                command=lambda: self.remove_channel_and_refresh(channel['id'], parent)
            ).pack()
        else:
            ctk.CTkButton(
                actions_frame,
                text="إضافة للمراقبة",
                width=120,
                fg_color="green",
                hover_color="darkgreen",
                command=lambda: self.add_channel_by_id_and_refresh(
                    channel['id'],
                    channel['name'],
                    channel.get('username'),
                    parent
                )
            ).pack()

    def add_channel_by_id_and_refresh(self, channel_id, channel_name, username, scroll_frame):
        """إضافة قناة بالـ ID وتحديث العرض"""
        async def do_add():
            result = await self.telegram_client.add_channel_by_id(channel_id, channel_name, username)

            if result['success']:
                self.root.after(0, lambda: messagebox.showinfo("نجح", f"تمت إضافة القناة: {channel_name}"))
                self.root.after(0, lambda: self.load_all_channels(scroll_frame))
                self.root.after(0, self.refresh_channels)
            else:
                self.root.after(0, lambda: messagebox.showerror("خطأ", f"فشل إضافة القناة: {result['error']}"))

        asyncio.run_coroutine_threadsafe(do_add(), self.loop)

    def remove_channel_and_refresh(self, channel_id, scroll_frame):
        """حذف قناة وتحديث العرض"""
        if self.telegram_client:
            self.telegram_client.remove_channel(channel_id)
            self.load_all_channels(scroll_frame)
            self.refresh_channels()

    def create_selectable_channel_card_with_checkbox(self, parent, channel):
        """إنشاء بطاقة قناة مع checkbox للتحديد الجماعي"""
        card = ctk.CTkFrame(parent)
        card.pack(fill="x", padx=10, pady=5)

        # Checkbox للتحديد
        checkbox_var = ctk.BooleanVar(value=False)
        checkbox = ctk.CTkCheckBox(
            card,
            text="",
            variable=checkbox_var,
            width=30,
            command=self.update_selected_count
        )
        checkbox.pack(side="left", padx=(10, 5))

        # حفظ checkbox في القاموس
        self.channel_checkboxes[channel['id']] = {
            'var': checkbox_var,
            'channel': channel,
            'checkbox': checkbox
        }

        # معلومات القناة
        info_frame = ctk.CTkFrame(card)
        info_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        # الاسم
        name_text = channel['name']
        if channel.get('username'):
            name_text += f" (@{channel['username']})"

        ctk.CTkLabel(
            info_frame,
            text=name_text,
            font=("Arial", 13, "bold")
        ).pack(anchor="w")

        # النوع
        type_text = "📢 قناة" if channel['is_channel'] else "👥 مجموعة"
        if channel.get('participants_count'):
            type_text += f" | {channel['participants_count']} عضو"

        ctk.CTkLabel(
            info_frame,
            text=type_text,
            font=("Arial", 11)
        ).pack(anchor="w")

        # الحالة
        if channel['is_monitored']:
            status_label = ctk.CTkLabel(
                info_frame,
                text="✅ تتم مراقبتها",
                font=("Arial", 11),
                text_color="green"
            )
            # تعطيل checkbox للقنوات المراقبة بالفعل
            checkbox.configure(state="disabled")
            checkbox_var.set(False)
        else:
            status_label = ctk.CTkLabel(
                info_frame,
                text="⚪ غير مراقبة",
                font=("Arial", 11),
                text_color="gray"
            )
        status_label.pack(anchor="w")

    def select_all_channels(self):
        """تحديد جميع القنوات غير المراقبة"""
        for channel_id, data in self.channel_checkboxes.items():
            if not data['channel']['is_monitored']:
                data['var'].set(True)
        self.update_selected_count()

    def deselect_all_channels(self):
        """إلغاء تحديد جميع القنوات"""
        for data in self.channel_checkboxes.values():
            data['var'].set(False)
        self.update_selected_count()

    def select_channels_only(self, is_channel):
        """تحديد القنوات أو المجموعات فقط"""
        for channel_id, data in self.channel_checkboxes.items():
            channel = data['channel']
            if not channel['is_monitored']:
                if channel['is_channel'] == is_channel:
                    data['var'].set(True)
                else:
                    data['var'].set(False)
        self.update_selected_count()

    def update_selected_count(self):
        """تحديث عداد القنوات المحددة"""
        if not hasattr(self, 'selected_count_label'):
            return

        count = sum(1 for data in self.channel_checkboxes.values()
                   if data['var'].get() and not data['channel']['is_monitored'])

        self.selected_count_label.configure(text=f"المحدد: {count}")

    def add_selected_channels(self, scroll_frame, channels_window):
        """إضافة جميع القنوات المحددة"""
        selected_channels = [
            data['channel']
            for data in self.channel_checkboxes.values()
            if data['var'].get() and not data['channel']['is_monitored']
        ]

        if not selected_channels:
            messagebox.showinfo("تنبيه", "لم يتم تحديد أي قنوات")
            return

        count = len(selected_channels)

        if not messagebox.askyesno(
            "تأكيد",
            f"هل تريد إضافة {count} قناة/مجموعة للمراقبة؟"
        ):
            return

        # إضافة القنوات
        async def do_add_multiple():
            added = 0
            failed = 0

            for channel in selected_channels:
                result = await self.telegram_client.add_channel_by_id(
                    channel['id'],
                    channel['name'],
                    channel.get('username')
                )

                if result['success']:
                    added += 1
                else:
                    failed += 1

            # عرض النتيجة
            self.root.after(0, lambda: messagebox.showinfo(
                "نتيجة الإضافة",
                f"✅ تمت إضافة: {added}\n❌ فشلت: {failed}"
            ))

            # تحديث القوائم
            self.root.after(0, self.refresh_channels)
            self.root.after(0, lambda: self.load_all_channels(scroll_frame, channels_window))

        asyncio.run_coroutine_threadsafe(do_add_multiple(), self.loop)

    def refresh_live_messages(self):
        """تحديث عرض الرسائل الحية - محسّن لمنع الأخطاء"""
        try:
            # التحقق من أن الـ widget موجود
            if not self.live_messages_scroll or not self.live_messages_scroll.winfo_exists():
                return
            
            # مسح القائمة بشكل آمن
            for widget in self.live_messages_scroll.winfo_children():
                try:
                    if widget.winfo_exists():
                        widget.destroy()
                except Exception:
                    pass

            # إعادة عرض الرسائل
            if self.live_messages:
                for msg in self.live_messages:
                    try:
                        new_card = self.create_live_message_card(msg['message_data'], msg['signal'])
                        if new_card and new_card.winfo_exists():
                            new_card.pack(fill="x", padx=10, pady=5)
                    except Exception as e:
                        print(f"خطأ في إعادة عرض رسالة: {e}")
            else:
                # رسالة ترحيبية
                try:
                    welcome_frame = ctk.CTkFrame(self.live_messages_scroll, fg_color="#2b2b2b")
                    welcome_frame.pack(fill="x", padx=10, pady=10)

                    ctk.CTkLabel(
                        welcome_frame,
                        text="🎯 لا توجد رسائل حتى الآن",
                        font=("Arial", 16, "bold"),
                        text_color="#4CAF50"
                    ).pack(pady=20)
                except Exception:
                    pass
        except Exception as e:
            print(f"خطأ في refresh_live_messages: {e}")

    def clear_live_messages(self):
        """مسح جميع الرسائل"""
        if messagebox.askyesno("تأكيد", "هل تريد مسح جميع الرسائل؟"):
            # حذف الـ widgets بشكل آمن
            for msg in self.live_messages:
                try:
                    if 'widget' in msg and msg['widget']:
                        if msg['widget'].winfo_exists():
                            msg['widget'].destroy()
                except Exception:
                    pass
            
            # مسح القائمة
            self.live_messages = []
            
            # إعادة تعيين علم الترحيب
            if hasattr(self, '_welcome_removed'):
                delattr(self, '_welcome_removed')
            
            # تحديث العرض
            self.refresh_live_messages()

    def show_notification(self, title: str, message: str, is_error: bool = False):
        """إظهار إشعار للمستخدم"""
        if is_error:
            messagebox.showerror(title, message)
        else:
            messagebox.showinfo(title, message)

    def is_useful_message(self, message_text: str) -> bool:
        """فحص إذا كانت الرسالة مفيدة (تحتوي على إشارة تداول)"""
        # قائمة بالكلمات المفتاحية التي تشير لرسالة غير مفيدة
        useless_patterns = [
            # رسائل الأرباح المحققة
            r'profit.*achieved', r'target.*hit', r'tp.*reached', r'تم.*الهدف',
            r'حقق.*ربح', r'وصل.*الهدف', r'نجح.*الصفقة',

            # رسائل النتائج
            r'result.*today', r'today.*result', r'\d+\s*pips', r'نتائج.*اليوم',
            r'اليوم.*ربح', r'إجمالي.*الربح',

            # رسائل التحفيز والترويج
            r'join.*vip', r'subscribe', r'اشترك', r'انضم.*vip', r'للاشتراك',
            r'premium', r'contact.*admin', r'للتواصل',

            # رسائل التحديثات
            r'update', r'تحديث', r'analysis', r'تحليل.*السوق',

            # رسائل التهنئة
            r'congratulation', r'congrats', r'مبروك', r'تهانينا',

            # رسائل بدون محتوى مفيد
            r'^[\W\s]*$',  # رسائل فارغة أو رموز فقط
        ]

        # فحص كل نمط
        message_upper = message_text.upper()
        for pattern in useless_patterns:
            if re.search(pattern, message_upper, re.IGNORECASE):
                return False

        # يجب أن تحتوي على كلمات مفتاحية أساسية
        required_keywords = [
            # الرمز
            r'\b(GOLD|XAUUSD|BTC|EUR|GBP|USD|OIL|NAS)\b',
            # نوع الصفقة
            r'\b(BUY|SELL|LONG|SHORT)\b',
        ]

        has_required = all(
            re.search(pattern, message_upper, re.IGNORECASE)
            for pattern in required_keywords
        )

        return has_required

    def schedule_daily_report(self):
        """جدولة حفظ التقرير اليومي"""
        def generate_and_schedule():
            # إنشاء التقرير اليومي
            try:
                summary = self.report_manager.generate_daily_summary()
                print(f"✅ تم إنشاء التقرير اليومي: {summary.get('date')}")

                # تصدير إلى CSV
                signals_csv = self.report_manager.export_to_csv('signals')
                trades_csv = self.report_manager.export_to_csv('trades')

                if signals_csv:
                    print(f"📄 تم تصدير الإشارات: {signals_csv}")
                if trades_csv:
                    print(f"📄 تم تصدير الصفقات: {trades_csv}")

                # حذف التقارير القديمة (أقدم من 30 يوم)
                self.report_manager.cleanup_old_reports(days_to_keep=30)

            except Exception as e:
                print(f"❌ خطأ في إنشاء التقرير اليومي: {e}")

            # إعادة الجدولة لنفس الوقت غداً (24 ساعة)
            self.root.after(24 * 60 * 60 * 1000, generate_and_schedule)

        # بدء الجدولة (سيتم التنفيذ أول مرة بعد 24 ساعة)
        # يمكن تغييرها لتنفيذ فوري: self.root.after(1000, generate_and_schedule)
        self.root.after(24 * 60 * 60 * 1000, generate_and_schedule)

    def build_symbols_tab(self):
        """بناء تبويب خصائص الرموز"""
        # الإطار الرئيسي
        main_frame = ctk.CTkFrame(self.tab_symbols)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # العنوان
        title_frame = ctk.CTkFrame(main_frame)
        title_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            title_frame,
            text="📊 فحص خصائص الرموز في MT5",
            font=("Arial", 18, "bold")
        ).pack(pady=10)

        # إطار الإدخال
        input_frame = ctk.CTkFrame(main_frame)
        input_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            input_frame,
            text="أدخل رمز الأصل (مثل: XAUUSD, EURUSD):",
            font=("Arial", 12)
        ).pack(pady=5)

        symbol_input_frame = ctk.CTkFrame(input_frame)
        symbol_input_frame.pack(pady=5)

        self.symbol_entry = ctk.CTkEntry(
            symbol_input_frame,
            placeholder_text="XAUUSD",
            width=200,
            font=("Arial", 14)
        )
        self.symbol_entry.pack(side="left", padx=5)

        ctk.CTkButton(
            symbol_input_frame,
            text="🔍 فحص الرمز",
            command=self.check_symbol_properties,
            font=("Arial", 12, "bold"),
            fg_color="#2196F3",
            hover_color="#1976D2"
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            symbol_input_frame,
            text="💾 حفظ",
            command=self.save_current_symbol_properties,
            font=("Arial", 12, "bold"),
            fg_color="#4CAF50",
            hover_color="#45a049"
        ).pack(side="left", padx=5)

        # أزرار إضافية
        action_frame = ctk.CTkFrame(input_frame)
        action_frame.pack(pady=10)

        ctk.CTkButton(
            action_frame,
            text="📋 فحص جميع الرموز",
            command=self.check_all_symbols,
            font=("Arial", 12),
            width=180
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            action_frame,
            text="📂 فتح ملف الخصائص",
            command=self.open_symbols_file,
            font=("Arial", 12),
            width=180
        ).pack(side="left", padx=5)

        # إطار النتائج
        results_frame = ctk.CTkFrame(main_frame)
        results_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            results_frame,
            text="النتائج:",
            font=("Arial", 14, "bold")
        ).pack(anchor="w", padx=10, pady=5)

        # منطقة عرض النتائج مع scroll
        self.symbols_results_text = ctk.CTkTextbox(
            results_frame,
            font=("Courier New", 11),
            wrap="word"
        )
        self.symbols_results_text.pack(fill="both", expand=True, padx=10, pady=10)

        # متغير لتخزين آخر نتيجة
        self.last_symbol_properties = None

    def check_symbol_properties(self):
        """فحص خصائص الرمز المدخل"""
        if not self.mt5_manager or not self.mt5_manager.is_connected:
            self.show_toast("يجب الاتصال بـ MT5 أولاً", "warning")
            return

        symbol = self.symbol_entry.get().strip().upper()
        if not symbol:
            self.show_toast("الرجاء إدخال رمز الأصل", "warning")
            return

        # مسح النتائج السابقة
        self.symbols_results_text.delete("1.0", "end")
        self.symbols_results_text.insert("1.0", "⏳ جاري فحص الرمز...\n")
        self.root.update()

        # الحصول على الخصائص
        properties = self.mt5_manager.get_symbol_properties(symbol, verbose=False)
        
        if not properties:
            self.symbols_results_text.delete("1.0", "end")
            self.symbols_results_text.insert("1.0", f"❌ فشل الحصول على خصائص الرمز {symbol}\n")
            self.symbols_results_text.insert("end", "تأكد من:\n")
            self.symbols_results_text.insert("end", "  1. الرمز موجود في المنصة\n")
            self.symbols_results_text.insert("end", "  2. الاتصال بـ MT5 نشط\n")
            self.show_toast(f"لم يتم العثور على الرمز {symbol}", "error")
            return

        # حفظ النتيجة
        self.last_symbol_properties = properties

        # عرض النتائج
        self.symbols_results_text.delete("1.0", "end")
        
        output = []
        output.append("=" * 70)
        output.append(f"📊 تقرير خصائص الرمز: {properties['symbol']}")
        output.append("=" * 70)
        
        if properties['description']:
            output.append(f"📝 الوصف: {properties['description']}")
        
        output.append(f"\n🔧 إعدادات التداول:")
        output.append(f"   ✅ التداول مسموح: {'نعم ✓' if properties['trade_allowed'] else '❌ لا'}")
        output.append(f"   🤖 التداول عبر الخبراء: {'نعم ✓' if properties['trade_expert'] else '❌ لا'}")
        output.append(f"   👁️ الرمز مرئي: {'نعم ✓' if properties['visible'] else '❌ لا'}")
        
        output.append(f"\n📏 أحجام الصفقات:")
        output.append(f"   الحد الأدنى: {properties['volume_min']} لوت")
        output.append(f"   الحد الأقصى: {properties['volume_max']} لوت")
        output.append(f"   خطوة الحجم: {properties['volume_step']} لوت")
        
        output.append(f"\n💰 معلومات السعر:")
        output.append(f"   عدد الأرقام العشرية: {properties['digits']}")
        output.append(f"   حجم النقطة (Point): {properties['point']}")
        output.append(f"   حجم الـ Tick: {properties['tick_size']}")
        output.append(f"   قيمة الـ Tick: {properties['tick_value']}")
        output.append(f"   حجم العقد: {properties['contract_size']}")
        
        output.append(f"\n📊 معلومات السوق:")
        output.append(f"   Spread الحالي: {properties['spread']} نقطة")
        output.append(f"   Stop Level: {properties['trade_stops_level']} نقطة")
        
        output.append(f"\n💵 العملات:")
        output.append(f"   عملة الأساس: {properties['currency_base']}")
        output.append(f"   عملة الربح: {properties['currency_profit']}")
        output.append(f"   عملة الهامش: {properties['currency_margin']}")
        
        if properties['margin_initial'] > 0:
            output.append(f"\n💳 الهامش:")
            output.append(f"   الهامش الأولي: {properties['margin_initial']}")
            output.append(f"   هامش الصيانة: {properties['margin_maintenance']}")
        
        # معلومات أنواع التعبئة
        filling_modes = []
        if properties['filling_mode'] & 1:
            filling_modes.append("FOK")
        if properties['filling_mode'] & 2:
            filling_modes.append("IOC")
        if properties['filling_mode'] & 4:
            filling_modes.append("RETURN")
        
        output.append(f"\n⚙️ أوضاع التعبئة المدعومة:")
        output.append(f"   {', '.join(filling_modes) if filling_modes else 'غير محدد'}")
        
        output.append(f"\n⏰ وقت الفحص:")
        output.append(f"   {properties['timestamp']}")
        
        output.append("=" * 70)
        
        self.symbols_results_text.insert("1.0", "\n".join(output))
        self.show_toast(f"تم فحص الرمز {symbol} بنجاح", "success")

    def save_current_symbol_properties(self):
        """حفظ خصائص الرمز الحالي"""
        if not self.last_symbol_properties:
            self.show_toast("لا توجد بيانات للحفظ، افحص رمز أولاً", "warning")
            return

        symbol = self.last_symbol_properties['symbol']
        success = self.mt5_manager.save_symbol_properties(symbol)
        
        if success:
            self.show_toast(f"تم حفظ خصائص {symbol}", "success")
        else:
            self.show_toast("فشل حفظ الخصائص", "error")

    def check_all_symbols(self):
        """فحص جميع الرموز المتاحة"""
        if not self.mt5_manager or not self.mt5_manager.is_connected:
            self.show_toast("يجب الاتصال بـ MT5 أولاً", "warning")
            return

        # تأكيد
        import tkinter.messagebox as messagebox
        confirm = messagebox.askyesno(
            "تأكيد",
            "هل تريد فحص جميع الرموز؟\nقد يستغرق هذا عدة دقائق."
        )
        
        if not confirm:
            return

        self.symbols_results_text.delete("1.0", "end")
        self.symbols_results_text.insert("1.0", "⏳ جاري فحص جميع الرموز...\n")
        self.symbols_results_text.insert("end", "هذا قد يستغرق بعض الوقت...\n")
        self.root.update()

        # الحصول على جميع الخصائص
        results = self.mt5_manager.get_all_symbols_properties(save_to_file=True)
        
        if results:
            self.symbols_results_text.delete("1.0", "end")
            output = f"✅ تم فحص {len(results)} رمز بنجاح!\n\n"
            output += f"📂 تم حفظ البيانات في: data/symbols_info.json\n\n"
            output += "الرموز المفحوصة:\n"
            for symbol in list(results.keys())[:50]:  # أول 50 رمز
                output += f"  • {symbol}\n"
            
            if len(results) > 50:
                output += f"\n... و {len(results) - 50} رمز آخر\n"
            
            self.symbols_results_text.insert("1.0", output)
            self.show_toast(f"تم فحص {len(results)} رمز", "success")
        else:
            self.symbols_results_text.delete("1.0", "end")
            self.symbols_results_text.insert("1.0", "❌ فشل فحص الرموز\n")
            self.show_toast("فشل فحص الرموز", "error")

    def open_symbols_file(self):
        """فتح ملف الخصائص"""
        import os
        import subprocess
        
        file_path = 'data/symbols_info.json'
        
        if not os.path.exists(file_path):
            self.show_toast("الملف غير موجود، افحص رمز أولاً", "warning")
            return
        
        try:
            # فتح الملف بالبرنامج الافتراضي
            os.startfile(file_path)
            self.show_toast("تم فتح الملف", "success")
        except Exception as e:
            self.show_toast(f"فشل فتح الملف: {str(e)}", "error")


if __name__ == "__main__":
    import os
    os.makedirs('data', exist_ok=True)

    app = TelegramMT5GUI()
    app.run()
