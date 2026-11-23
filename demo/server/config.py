"""Environment-only configuration; no embedded credentials."""
import os
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
WEB = HERE.parent / 'web'
DEMO_DATA = os.getenv('DEMO_DATA', 'false').lower() == 'true'
DB_PATH = Path(os.getenv('DEMO_DB_PATH', str(HERE / 'data' / 'demo.sqlite3')))
TEMP_PATH = Path(os.getenv('DEMO_TEMP_PATH', str(HERE / 'tmp')))
OCR_DATA_PATH = Path(os.getenv('TESSDATA_PREFIX') or HERE / 'data' / 'tessdata')
PUBLIC_ORIGIN = os.getenv('PUBLIC_ORIGIN', 'http://127.0.0.1:8765').rstrip('/')
COOKIE_SECURE = PUBLIC_ORIGIN.startswith('https://')
SESSION_HOURS = 8

def now():
    return datetime.now(timezone.utc)

def stamp():
    return now().isoformat()

def today():
    return datetime.now(ZoneInfo('Asia/Taipei')).date()
