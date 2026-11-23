"""OCR worker. The process starts in the language data directory."""
import sys

import fitz


def main():
    pixmap = fitz.Pixmap(sys.stdin.buffer.read())
    if pixmap.alpha:
        pixmap = fitz.Pixmap(pixmap, 0)
    pdf = pixmap.pdfocr_tobytes(language='chi_tra+eng', tessdata='.')
    with fitz.open(stream=pdf, filetype='pdf') as document:
        text = document[0].get_text(sort=True)
    sys.stdout.buffer.write(text.encode('utf-8'))


if __name__ == '__main__':
    main()
