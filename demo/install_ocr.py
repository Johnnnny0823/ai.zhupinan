"""Install the fixed Tesseract language models used by the synthetic demo."""
import hashlib
import tempfile
from pathlib import Path
from urllib.request import urlopen

from .server.config import OCR_DATA_PATH

REVISION = '65727574dfcd264acbb0c3e07860e4e9e9b22185'
URL = f'https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/{REVISION}/'
MODELS = {
    'chi_tra.traineddata': '529c5b5797d64b126065cd55f2bb4c7fd7b15790798091b1ff259941a829330b',
    'eng.traineddata': '7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2',
}


def main():
    OCR_DATA_PATH.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=OCR_DATA_PATH) as temp:
        for filename, digest in MODELS.items():
            target = OCR_DATA_PATH / filename
            if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == digest:
                continue
            with urlopen(URL + filename, timeout=30) as response:
                data = response.read(8 * 1024 * 1024)
            if hashlib.sha256(data).hexdigest() != digest:
                raise SystemExit(f'OCR model verification failed: {filename}')
            pending = Path(temp) / filename
            pending.write_bytes(data)
            pending.replace(target)
    print('OCR language data installed and verified.')


if __name__ == '__main__':
    main()
