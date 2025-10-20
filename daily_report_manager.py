"""
نظام إدارة التقارير اليومية
يحفظ الإشارات والصفقات كل 24 ساعة بشكل منظم
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path


class DailyReportManager:
    def __init__(self, reports_dir: str = 'data/daily_reports'):
        self.reports_dir = reports_dir
        self.ensure_directories()

    def ensure_directories(self):
        """إنشاء المجلدات المطلوبة"""
        Path(self.reports_dir).mkdir(parents=True, exist_ok=True)
        Path(f"{self.reports_dir}/signals").mkdir(exist_ok=True)
        Path(f"{self.reports_dir}/trades").mkdir(exist_ok=True)
        Path(f"{self.reports_dir}/summary").mkdir(exist_ok=True)

    def get_today_date(self) -> str:
        """الحصول على تاريخ اليوم بصيغة YYYY-MM-DD"""
        return datetime.now().strftime('%Y-%m-%d')

    def get_report_filename(self, report_type: str, date: str = None) -> str:
        """الحصول على اسم ملف التقرير"""
        if date is None:
            date = self.get_today_date()
        return f"{self.reports_dir}/{report_type}/{date}.json"

    def save_signal(self, signal_data: dict):
        """حفظ إشارة في التقرير اليومي"""
        filename = self.get_report_filename('signals')

        # تحميل التقرير الحالي أو إنشاء جديد
        report = self.load_report('signals') or {
            'date': self.get_today_date(),
            'total_signals': 0,
            'signals_by_channel': {},
            'signals': []
        }

        # إضافة الإشارة
        report['signals'].append({
            **signal_data,
            'received_at': datetime.now().isoformat()
        })

        report['total_signals'] += 1

        # تحديث إحصائيات القناة
        channel = signal_data.get('channel_name', 'Unknown')
        if channel not in report['signals_by_channel']:
            report['signals_by_channel'][channel] = {
                'count': 0,
                'symbols': {}
            }

        report['signals_by_channel'][channel]['count'] += 1

        # تحديث إحصائيات الرمز
        symbol = signal_data.get('symbol', 'Unknown')
        if symbol not in report['signals_by_channel'][channel]['symbols']:
            report['signals_by_channel'][channel]['symbols'][symbol] = 0
        report['signals_by_channel'][channel]['symbols'][symbol] += 1

        # حفظ التقرير
        self.save_report('signals', report)

    def save_trade(self, trade_data: dict):
        """حفظ صفقة في التقرير اليومي"""
        filename = self.get_report_filename('trades')

        # تحميل التقرير الحالي أو إنشاء جديد
        report = self.load_report('trades') or {
            'date': self.get_today_date(),
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_profit': 0.0,
            'total_loss': 0.0,
            'trades_by_channel': {},
            'trades': []
        }

        # إضافة الصفقة
        trade_info = {
            **trade_data,
            'executed_at': trade_data.get('opened_at', datetime.now().isoformat())
        }

        report['trades'].append(trade_info)
        report['total_trades'] += 1

        # حساب الأرباح/الخسائر
        profit = trade_data.get('profit', 0.0)
        if profit > 0:
            report['winning_trades'] += 1
            report['total_profit'] += profit
        elif profit < 0:
            report['losing_trades'] += 1
            report['total_loss'] += abs(profit)

        # تحديث إحصائيات القناة
        channel = trade_data.get('signal', {}).get('channel_name', 'Unknown')
        if channel not in report['trades_by_channel']:
            report['trades_by_channel'][channel] = {
                'count': 0,
                'winning': 0,
                'losing': 0,
                'profit': 0.0,
                'loss': 0.0
            }

        report['trades_by_channel'][channel]['count'] += 1
        if profit > 0:
            report['trades_by_channel'][channel]['winning'] += 1
            report['trades_by_channel'][channel]['profit'] += profit
        elif profit < 0:
            report['trades_by_channel'][channel]['losing'] += 1
            report['trades_by_channel'][channel]['loss'] += abs(profit)

        # حفظ التقرير
        self.save_report('trades', report)

    def save_report(self, report_type: str, data: dict):
        """حفظ التقرير"""
        filename = self.get_report_filename(report_type)

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"❌ خطأ في حفظ التقرير: {e}")

    def load_report(self, report_type: str, date: str = None) -> Optional[dict]:
        """تحميل تقرير"""
        filename = self.get_report_filename(report_type, date)

        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"❌ خطأ في تحميل التقرير: {e}")

        return None

    def generate_daily_summary(self) -> dict:
        """إنشاء ملخص يومي شامل"""
        signals_report = self.load_report('signals') or {}
        trades_report = self.load_report('trades') or {}

        total_signals = signals_report.get('total_signals', 0)
        total_trades = trades_report.get('total_trades', 0)
        winning_trades = trades_report.get('winning_trades', 0)
        losing_trades = trades_report.get('losing_trades', 0)
        total_profit = trades_report.get('total_profit', 0.0)
        total_loss = trades_report.get('total_loss', 0.0)

        net_profit = total_profit - total_loss
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        summary = {
            'date': self.get_today_date(),
            'generated_at': datetime.now().isoformat(),
            'signals': {
                'total': total_signals,
                'by_channel': signals_report.get('signals_by_channel', {})
            },
            'trades': {
                'total': total_trades,
                'winning': winning_trades,
                'losing': losing_trades,
                'win_rate': round(win_rate, 2)
            },
            'profit_loss': {
                'total_profit': round(total_profit, 2),
                'total_loss': round(total_loss, 2),
                'net_profit': round(net_profit, 2)
            },
            'performance_by_channel': {}
        }

        # إضافة أداء كل قناة
        for channel, data in trades_report.get('trades_by_channel', {}).items():
            channel_win_rate = (data['winning'] / data['count'] * 100) if data['count'] > 0 else 0
            channel_net = data['profit'] - data['loss']

            summary['performance_by_channel'][channel] = {
                'signals': signals_report.get('signals_by_channel', {}).get(channel, {}).get('count', 0),
                'trades': data['count'],
                'winning': data['winning'],
                'losing': data['losing'],
                'win_rate': round(channel_win_rate, 2),
                'profit': round(data['profit'], 2),
                'loss': round(data['loss'], 2),
                'net_profit': round(channel_net, 2)
            }

        # حفظ الملخص
        self.save_report('summary', summary)

        return summary

    def get_weekly_summary(self) -> dict:
        """الحصول على ملخص أسبوعي"""
        today = datetime.now()
        week_data = {
            'start_date': (today - timedelta(days=6)).strftime('%Y-%m-%d'),
            'end_date': today.strftime('%Y-%m-%d'),
            'daily_summaries': [],
            'totals': {
                'signals': 0,
                'trades': 0,
                'winning': 0,
                'losing': 0,
                'profit': 0.0,
                'loss': 0.0
            }
        }

        for i in range(7):
            date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
            summary = self.load_report('summary', date)

            if summary:
                week_data['daily_summaries'].append(summary)
                week_data['totals']['signals'] += summary['signals']['total']
                week_data['totals']['trades'] += summary['trades']['total']
                week_data['totals']['winning'] += summary['trades']['winning']
                week_data['totals']['losing'] += summary['trades']['losing']
                week_data['totals']['profit'] += summary['profit_loss']['total_profit']
                week_data['totals']['loss'] += summary['profit_loss']['total_loss']

        week_data['totals']['net_profit'] = round(
            week_data['totals']['profit'] - week_data['totals']['loss'], 2
        )
        week_data['totals']['win_rate'] = round(
            (week_data['totals']['winning'] / week_data['totals']['trades'] * 100)
            if week_data['totals']['trades'] > 0 else 0, 2
        )

        return week_data

    def export_to_csv(self, report_type: str, date: str = None) -> str:
        """تصدير التقرير إلى CSV"""
        import csv

        report = self.load_report(report_type, date)
        if not report:
            return None

        date_str = date or self.get_today_date()
        csv_filename = f"{self.reports_dir}/{report_type}_{date_str}.csv"

        try:
            if report_type == 'signals':
                with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as f:
                    if report.get('signals'):
                        writer = csv.DictWriter(f, fieldnames=report['signals'][0].keys())
                        writer.writeheader()
                        writer.writerows(report['signals'])

            elif report_type == 'trades':
                with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as f:
                    if report.get('trades'):
                        # تسطيح البيانات للـ CSV
                        flattened_trades = []
                        for trade in report['trades']:
                            flat_trade = {
                                'ticket': trade.get('ticket'),
                                'symbol': trade.get('signal', {}).get('symbol'),
                                'action': trade.get('signal', {}).get('action'),
                                'channel': trade.get('signal', {}).get('channel_name'),
                                'entry_price': trade.get('entry_price'),
                                'lot_size': trade.get('lot_size'),
                                'profit': trade.get('profit', 0),
                                'status': trade.get('status'),
                                'opened_at': trade.get('opened_at'),
                                'closed_at': trade.get('closed_at', '')
                            }
                            flattened_trades.append(flat_trade)

                        if flattened_trades:
                            writer = csv.DictWriter(f, fieldnames=flattened_trades[0].keys())
                            writer.writeheader()
                            writer.writerows(flattened_trades)

            return csv_filename

        except Exception as e:
            print(f"❌ خطأ في تصدير CSV: {e}")
            return None

    def cleanup_old_reports(self, days_to_keep: int = 30):
        """حذف التقارير القديمة (أقدم من X يوم)"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        deleted_count = 0

        for report_type in ['signals', 'trades', 'summary']:
            report_dir = f"{self.reports_dir}/{report_type}"

            if os.path.exists(report_dir):
                for filename in os.listdir(report_dir):
                    if filename.endswith('.json'):
                        file_path = os.path.join(report_dir, filename)
                        file_date = datetime.fromtimestamp(os.path.getmtime(file_path))

                        if file_date < cutoff_date:
                            try:
                                os.remove(file_path)
                                deleted_count += 1
                            except Exception as e:
                                print(f"⚠️ خطأ في حذف {file_path}: {e}")

        print(f"✅ تم حذف {deleted_count} تقرير قديم")
        return deleted_count


if __name__ == "__main__":
    # اختبار النظام
    manager = DailyReportManager()

    # اختبار حفظ إشارة
    test_signal = {
        'symbol': 'XAUUSD',
        'action': 'BUY',
        'entry_price': 2050.0,
        'take_profits': [2055, 2060, 2065],
        'stop_loss': 2045.0,
        'channel_name': 'Test Channel'
    }
    manager.save_signal(test_signal)

    # اختبار حفظ صفقة
    test_trade = {
        'ticket': 12345,
        'entry_price': 2050.5,
        'lot_size': 0.1,
        'profit': 15.50,
        'status': 'closed',
        'signal': test_signal
    }
    manager.save_trade(test_trade)

    # إنشاء ملخص
    summary = manager.generate_daily_summary()
    print(json.dumps(summary, indent=2, ensure_ascii=False))
