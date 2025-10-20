import os
from dotenv import load_dotenv
import json

load_dotenv()

class Config:
    # Telegram Configuration
    API_ID = os.getenv('API_ID', '')
    API_HASH = os.getenv('API_HASH', '')
    PHONE_NUMBER = os.getenv('PHONE_NUMBER', '')

    # MT5 Configuration
    MT5_LOGIN = os.getenv('MT5_LOGIN', '')
    MT5_PASSWORD = os.getenv('MT5_PASSWORD', '')
    MT5_SERVER = os.getenv('MT5_SERVER', '')

    # Database files
    CHANNELS_FILE = 'data/channels.json'
    SIGNALS_FILE = 'data/signals.json'
    PATTERNS_FILE = 'data/patterns.json'
    SETTINGS_FILE = 'data/settings.json'

    # Default Settings
    DEFAULT_SETTINGS = {
        'auto_trade': True,
        'auto_connect_mt5': True,
        'max_risk_per_trade': 2.0,
        'default_lot_size': 0.01,
        'enable_trailing_stop': True,
        'enable_notifications': True
    }

    @staticmethod
    def load_settings():
        try:
            with open(Config.SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return Config.DEFAULT_SETTINGS

    @staticmethod
    def save_settings(settings):
        os.makedirs('data', exist_ok=True)
        with open(Config.SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
