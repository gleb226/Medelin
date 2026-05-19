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
MONGO_URI = os.getenv('MONGO_URI', 'mongodb+srv://gleb:07072010hm@medelin.wjuh91p.mongodb.net/medelin?retryWrites=true&w=majority&appName=Medelin').strip()
MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', 'medelin').strip()
BOT_TOKEN = os.getenv('BOT_TOKEN', '8684857785:AAHITZYDCqgxbabIWfdywhdnujkJfXLK6vU')
PORTMONE_TOKEN = os.getenv('PORTMONE_TOKEN', '1661751239:TEST:hRj7-XMjG-WBt7-R3JP').strip()
PAYMENT_TOKEN = os.getenv('PAYMENT_TOKEN', PORTMONE_TOKEN).strip()
MONOBANK_TOKEN = os.getenv('MONOBANK_TOKEN', 'uqYTPdIGKcmMP4TbSg1gs-tGTz5A54KcVe2fDbt08lls').strip()
NP_API_KEY = os.getenv('NP_API_KEY', '2106edabf72d6a696805f3275872f465').strip()
LIQPAY_PUBLIC_KEY = os.getenv('LIQPAY_PUBLIC_KEY', 'sandbox_i96717270086')
LIQPAY_PRIVATE_KEY = os.getenv('LIQPAY_PRIVATE_KEY', 'sandbox_p5St5vAd0nvxPniHWJXEgnP1nXcOsfUSTMu1xXHV')
WORK_START_HOUR = int(os.getenv('WORK_START_HOUR', '8'))
WORK_END_HOUR = int(os.getenv('WORK_END_HOUR', '22'))
BOSS_IDS = os.getenv('BOSS_IDS', '513546547').split(',')
WEB_APP_URL = os.getenv('WEB_APP_URL', 'https://medelin.onrender.com').strip()
