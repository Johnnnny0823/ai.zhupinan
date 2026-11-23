"""Download and load the PaddleOCR mobile models before the demo."""
import subprocess

from .server.config import HERE, OCR_MODELS_PATH, OCR_PYTHON


def main():
    if not OCR_PYTHON.is_file():
        raise SystemExit('請先建立 .venv-ocr，並安裝 demo/requirements-ocr.txt。')
    OCR_MODELS_PATH.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [str(OCR_PYTHON), str(HERE / 'ocr_worker.py'), '--prepare'],
        cwd=OCR_MODELS_PATH, check=True, timeout=600,
    )
    print('PaddleOCR models prepared.')


if __name__ == '__main__':
    main()
