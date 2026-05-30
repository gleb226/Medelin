from pathlib import Path
import os
from dotenv import load_dotenv
BASE_DIR = Path(__file__).resolve().parents[2]
env_candidates = [BASE_DIR.parent / '.env', BASE_DIR / '.env']
for env_path in env_candidates:
    if env_path.exists():
        load_dotenv(env_path, override=True, encoding='utf-8')
APP_DIR = BASE_DIR / 'app'
DB_DIR = APP_DIR / 'databases'
USERS_DB_PATH = DB_DIR / 'users.db'
ORDERS_DB_PATH = DB_DIR / 'orders.db'
MENU_DB_PATH = DB_DIR / 'menu.db'
ERRORS_DB_PATH = DB_DIR / 'errors.db'
LOGS_DB_PATH = DB_DIR / 'logs.db'
ADMINS_DB_PATH = DB_DIR / 'admins.db'
SALES_DB_PATH = DB_DIR / 'sales.db'
DB_DIR.mkdir(parents=True, exist_ok=True)
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/medelin').strip()
MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', 'medelin').strip()
BOT_TOKEN = os.getenv('BOT_TOKEN', '').strip()
PORTMONE_TOKEN = os.getenv('PORTMONE_TOKEN', '').strip()
PAYMENT_TOKEN = os.getenv('PAYMENT_TOKEN', PORTMONE_TOKEN).strip()

if not PAYMENT_TOKEN and PORTMONE_TOKEN:
    PAYMENT_TOKEN = PORTMONE_TOKEN
MONOBANK_TOKEN = os.getenv('MONOBANK_TOKEN', '').strip()
NP_API_KEY = os.getenv('NP_API_KEY', '').strip()
LIQPAY_PUBLIC_KEY = os.getenv('LIQPAY_PUBLIC_KEY', '').strip()
LIQPAY_PRIVATE_KEY = os.getenv('LIQPAY_PRIVATE_KEY', '').strip()
WORK_START_HOUR = int(os.getenv('WORK_START_HOUR', '8'))
WORK_END_HOUR = int(os.getenv('WORK_END_HOUR', '22'))
BOSS_IDS = [x.strip() for x in os.getenv('BOSS_IDS', '').split(',') if x.strip()]
WEB_APP_URL = os.getenv('WEB_APP_URL', 'https://medelin.onrender.com').strip()
ADMIN_PANEL_PASSWORD = os.getenv('ADMIN_PANEL_PASSWORD', '0707').strip()
