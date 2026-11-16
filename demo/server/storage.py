"""Inspect actual formats in memory; scan processing is restricted to known seed bytes."""
import hashlib
import io
from pathlib import Path
from fastapi import HTTPException
from . import config

MAX_BYTES = 15 * 1024 * 1024

def inspect(raw, filename, content_type):
    if not raw:
        raise HTTPException(400, '檔案沒有內容')
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, '檔案超過 15 MB，請縮小後重試')
    suffix = Path(filename or '').suffix.lower()
    allowed = {'.txt':('text/plain',),'.pdf':('application/pdf',),'.png':('image/png',),'.jpg':('image/jpeg',),'.jpeg':('image/jpeg',)}
    if suffix not in allowed or content_type not in allowed[suffix]:
        raise HTTPException(415, '檔案格式不符：只接受 MIME 與內容相符的 JPG、PNG、PDF、UTF-8 TXT')
    text, scanned = None, False
    try:
        if suffix == '.pdf':
            import fitz
            if not raw.startswith(b'%PDF-'): raise ValueError()
            with fitz.open(stream=raw, filetype='pdf') as document:
                if document.needs_pass or not 1 <= len(document) <= 10:
                    raise HTTPException(400, 'PDF 須為未加密文件，且不超過 10 頁')
                text = '\n'.join(p.get_text() for p in document)
                scanned = any(len(p.get_text().strip()) < 20 or p.get_images() for p in document)
        elif suffix in ('.png','.jpg','.jpeg'):
            from PIL import Image
            with Image.open(io.BytesIO(raw)) as im:
                if im.format != ('PNG' if suffix=='.png' else 'JPEG'): raise ValueError()
                if im.width * im.height > 25_000_000: raise ValueError()
                im.verify()
            scanned = True
        else:
            if raw.startswith((b'%PDF-', b'\x89PNG', b'\xff\xd8')) or b'\0' in raw: raise ValueError()
            text = raw.decode('utf-8-sig')
            if any(ord(ch)<32 and ch not in '\r\n\t' for ch in text): raise ValueError()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(415, '檔案內容損壞，或實際格式與副檔名不符') from None
    if scanned:
        known = {hashlib.sha256(p.read_bytes()).hexdigest() for p in (config.WEB/'samples').glob('*.png')}
        if not config.DEMO_DATA or hashlib.sha256(raw).hexdigest() not in known:
            raise HTTPException(422, '圖片／含圖 PDF 僅允許系統提供的合成範例。真實掃描件已停止處理，不會送出模型。請選合成範例展示。')
    return text, scanned

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
