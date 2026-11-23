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
OCR_MODELS_PATH = HERE / 'data' / 'paddle_models'
OCR_PYTHON = Path(os.getenv('DEMO_OCR_PYTHON') or ROOT / '.venv-ocr' / (
    'Scripts/python.exe' if os.name == 'nt' else 'bin/python'
))
QDRANT_URL = os.getenv('DEMO_QDRANT_URL', '')
CLAUDE_MODEL = os.getenv('DEMO_CLAUDE_MODEL') or 'claude-sonnet-5-5'
GEMINI_CROSSCHECK = os.getenv('DEMO_GEMINI_CROSSCHECK') == '1'
LAW_VECTOR_PATH = HERE / 'data' / 'qdrant'
LAW_EMBEDDING_CACHE = HERE / 'data' / 'law_embeddings'
PUBLIC_ORIGIN = os.getenv('PUBLIC_ORIGIN', 'http://127.0.0.1:8765').rstrip('/')
COOKIE_SECURE = PUBLIC_ORIGIN.startswith('https://')
SESSION_HOURS = 8

def now():
    return datetime.now(timezone.utc)

def stamp():
    return now().isoformat()

def today():
    return datetime.now(ZoneInfo('Asia/Taipei')).date()
