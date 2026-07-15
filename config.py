import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

API_ID = int(os.getenv('API_ID', '0'))
API_HASH = os.getenv('API_HASH', '')
PHONE = os.getenv('PHONE', '')
ADMIN_IDS: list[int] = [
    int(x.strip()) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip().isdigit()
]

SOCKS5_HOST = os.getenv('SOCKS5_HOST', '')
SOCKS5_PORT = int(os.getenv('SOCKS5_PORT', '1080'))
SOCKS5_USER = os.getenv('SOCKS5_USER', '')
SOCKS5_PASSWORD = os.getenv('SOCKS5_PASSWORD', '')

MTPROTO_SERVER = os.getenv('MTPROTO_SERVER', '')
MTPROTO_PORT = int(os.getenv('MTPROTO_PORT', '443'))
MTPROTO_SECRET = os.getenv('MTPROTO_SECRET', '')

SESSION_DIR = os.path.join(os.path.dirname(__file__), 'sessions')
os.makedirs(SESSION_DIR, exist_ok=True)
SESSION_FILE = os.path.join(SESSION_DIR, 'client')
