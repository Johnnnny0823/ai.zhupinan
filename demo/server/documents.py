"""Per-date review reasons; document prose is never a confidence score."""
import re
import unicodedata

DATE_FIELDS = ('entry_date', 'permit_start', 'permit_end', 'event_date', 'notify_date')
YEAR_DATE = re.compile(r'(?<!\d)(\d{1,4})\s*(?:年|[/.\-])\s*\d{1,2}')
CHINESE_DATE = re.compile(r'[〇零一二三四五六七八九十百]+\s*(?:年|月|日|[/.\-])')


def field_warning(excerpt: str | None, is_image: bool) -> str | None:
    source = unicodedata.normalize('NFKC', excerpt or '').strip()
    reasons = []
    if is_image:
        reasons.append('掃描文件，請對照原件核對')
    if CHINESE_DATE.search(source):
        reasons.append('國字日期，請核對換算')
    year = YEAR_DATE.search(source)
    if '民國' in source or (year and int(year.group(1)) < 1911):
        reasons.append('民國年已換算為西元，請核對')
    if not source:
        reasons.append('找不到原文片段，請核對')
    return '；'.join(reasons) or None
