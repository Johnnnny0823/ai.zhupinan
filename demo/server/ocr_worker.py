"""PaddleOCR worker for allowlisted synthetic scans, using stdin and stdout."""
import json
import os
from pathlib import Path
import sys
from contextlib import redirect_stdout

DETECTOR = 'PP-OCRv5_mobile_det'
RECOGNIZER = 'PP-OCRv5_mobile_rec'


def pipeline(*, prepare):
    os.environ['PADDLE_PDX_CACHE_HOME'] = '.'
    os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'
    os.environ.setdefault('PADDLE_PDX_MODEL_SOURCE', 'BOS')
    from paddleocr import PaddleOCR

    model_dirs = {}
    if not prepare:
        model_dirs = {
            'text_detection_model_dir': str(Path('official_models') / DETECTOR),
            'text_recognition_model_dir': str(Path('official_models') / RECOGNIZER),
        }
    return PaddleOCR(
        text_detection_model_name=DETECTOR, text_recognition_model_name=RECOGNIZER,
        use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False,
        device='cpu', enable_mkldnn=False, cpu_threads=2, **model_dirs,
    )


def main():
    prepare = sys.argv[1:] == ['--prepare']
    with redirect_stdout(sys.stderr):
        recognizer = pipeline(prepare=prepare)
        if prepare:
            return

        import cv2
        import numpy as np

        image = cv2.imdecode(np.frombuffer(sys.stdin.buffer.read(), dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError('Invalid synthetic scan')
        text = '\n'.join(line for page in recognizer.predict(image) for line in page['rec_texts'])
    print(json.dumps({'text': text}, ensure_ascii=True))


if __name__ == '__main__':
    main()
