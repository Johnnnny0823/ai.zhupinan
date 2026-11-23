"""Inspect actual formats in memory; scan processing is restricted to known seed bytes."""
import hashlib
import io
import subprocess
import sys
from pathlib import Path
from threading import Lock
from fastapi import HTTPException
from . import config

MAX_BYTES = 15 * 1024 * 1024
PDF_LOCK = Lock()

TEXT_ENCODING_ERROR = '文字檔無法辨識：請另存為 UTF-8 編碼的純文字檔'


def decode_text(raw: bytes) -> str | None:
    encodings = ['utf-8-sig']
    if raw.startswith((b'\xff\xfe', b'\xfe\xff')):
        encodings.append('utf-16')
    encodings.append('cp950')
    for encoding in encodings:
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        if not text or '\0' in text:
            continue
        printable = sum(ch.isprintable() or ch in '\r\n\t' for ch in text)
        if printable / len(text) > 0.97:
            return text
    return None


def inspect(raw, filename, content_type, *, markdown=False):
    if not raw:
        raise HTTPException(400, '檔案沒有內容')
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, '檔案超過 15 MB，請縮小後重試')
    suffix = Path(filename or '').suffix.lower()
    allowed = {'.txt':('text/plain',),'.pdf':('application/pdf',),'.png':('image/png',),'.jpg':('image/jpeg',),'.jpeg':('image/jpeg',)}
    if suffix not in allowed or content_type not in allowed[suffix]:
        raise HTTPException(415, '檔案格式不符：只接受 MIME 與內容相符的 JPG、PNG、PDF、TXT（UTF-8、具BOM的UTF-16、Big5）')
    text, scanned = None, False
    try:
        if suffix == '.pdf':
            import fitz
            if not raw.startswith(b'%PDF-'): raise ValueError()
            with PDF_LOCK, fitz.open(stream=raw, filetype='pdf') as document:
                if document.needs_pass or not 1 <= len(document) <= 10:
                    raise HTTPException(400, 'PDF 須為未加密文件，且不超過 10 頁')
                pages = [page.get_text(sort=markdown) for page in document]
                scanned = any(len(content.strip()) < 20 or page.get_images() for page, content in zip(document, pages))
                if markdown:
                    text = '\n\n'.join(f'## 第 {i} 頁\n\n{content.strip()}' for i, content in enumerate(pages, 1))
                else:
                    text = '\n'.join(pages)
        elif suffix in ('.png','.jpg','.jpeg'):
            from PIL import Image
            with Image.open(io.BytesIO(raw)) as im:
                if im.format != ('PNG' if suffix=='.png' else 'JPEG'): raise ValueError()
                if im.width * im.height > 25_000_000: raise ValueError()
                im.verify()
            scanned = True
        else:
            if raw.startswith((b'%PDF-', b'\x89PNG', b'\xff\xd8')): raise ValueError()
            text = decode_text(raw)
            if text is None:
                raise HTTPException(415, TEXT_ENCODING_ERROR)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(415, '檔案內容損壞，或實際格式與副檔名不符') from None
    if scanned:
        known = {hashlib.sha256(p.read_bytes()).hexdigest() for p in (config.WEB/'samples').glob('*.png')}
        if not config.DEMO_DATA or hashlib.sha256(raw).hexdigest() not in known:
            raise HTTPException(422, '圖片／含圖 PDF 僅允許系統提供的合成範例。真實掃描件已停止處理，不會送出模型。請選合成範例展示。')
    return text, scanned

def read_scan_text(raw):
    """Read a previously validated synthetic scan in memory."""
    if any(not (config.OCR_DATA_PATH / filename).is_file() for filename in ('chi_tra.traineddata', 'eng.traineddata')):
        raise HTTPException(503, '尚未安裝本機 OCR 語言資料。請安裝後重試，或切換預存示範結果。')

    # The native OCR engine uses a relative data path so Windows can read the
    # language files even when the project directory contains non-ASCII text.
    try:
        result = subprocess.run(
            [sys.executable, str(Path(__file__).with_name('ocr_worker.py'))],
            input=raw, capture_output=True, cwd=config.OCR_DATA_PATH, timeout=30, check=True,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
        text = result.stdout.decode('utf-8').strip()
    except (OSError, subprocess.SubprocessError, UnicodeError) as error:
        raise HTTPException(503, '本機 OCR 暫時無法讀取，請檢查語言資料，或切換預存示範結果。') from error
    if not text:
        raise HTTPException(422, '本機 OCR 沒有讀到文字。請核對原件，或切換預存示範結果。')
    return text


async def read_upload(file):
    try:
        raw = await file.read(MAX_BYTES+1)
        if len(raw)>MAX_BYTES:
            raise HTTPException(413, '檔案超過 15 MB，請縮小後重試')
        return raw
    finally:
        await file.close()

def clean_runtime():
    """Only private runtime folders, never source/seed files."""
    import shutil
    for path in (config.TEMP_PATH,config.HERE/'uploads',config.HERE/'cache'):
        if path.exists():
            for p in path.iterdir():
                if p.is_dir(): shutil.rmtree(p)
                else: p.unlink()


def text_digest(text: str) -> str:
    """Match synthetic text across LF/CRLF checkouts without ignoring content changes."""
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()
