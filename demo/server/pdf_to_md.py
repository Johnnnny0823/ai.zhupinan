"""PDFToMD conversion for public synthetic forms, in memory."""
import re


def markdown_table(rows):
    if not rows or not rows[0]:
        return ''
    width = len(rows[0])

    def cells(row):
        values = [re.sub(r'\s+', ' ', str(cell or '')).strip().replace('|', r'\|') for cell in row]
        return '| ' + ' | '.join(values[:width] + [''] * max(0, width - len(values))) + ' |'

    return '\n'.join([cells(rows[0]), cells(['---'] * width), *(cells(row) for row in rows[1:])])


def convert(document):
    result = ['# 合成公文']
    for number, page in enumerate(document, 1):
        result.append(f'## 第 {number} 頁')
        detected = [(table.bbox, markdown_table(table.extract())) for table in page.find_tables().tables]
        tables = [(bbox, text) for bbox, text in detected if text]
        blocks = []
        for x0, y0, x1, y1, text, _, kind in page.get_text('blocks', sort=True):
            if kind != 0:
                continue
            center_x, center_y = (x0 + x1) / 2, (y0 + y1) / 2
            if any(box[0] <= center_x <= box[2] and box[1] <= center_y <= box[3] for box, _ in tables):
                continue
            if text.strip():
                blocks.append((y0, x0, text.strip()))
        blocks.extend((box[1], box[0], text) for box, text in tables)
        result.extend(text for _, _, text in sorted(blocks))
    return '\n\n'.join(result) + '\n'


def from_scan_pages(pages):
    return "# 合成公文\n\n" + "\n\n".join(f"## 第 {number} 頁\n\n{text}" for number, text in enumerate(pages, 1)) + "\n"
