"""Fetch the allowed MOJ public law pages and atomically replace the RAG snapshot."""
import argparse
import hashlib
import json
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from demo.law_catalog import SNAPSHOT, SOURCES, read_snapshot, source_url

MAX_BYTES = 2 * 1024 * 1024
STAMP = re.compile(r'民國\s*(\d{1,3})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日')
NUMBER = re.compile(r'第\s*(\d+(?:[－-]\d+)?)\s*條')


def parse_page(code, html):
    page = BeautifulSoup(html, 'html.parser')
    title = page.select_one('#hlLawName')
    date = page.select_one('#trLNNDate td')
    law = page.select_one('#pnLawFla')
    if title is None or title.get_text(strip=True) != SOURCES[code] or date is None or law is None:
        raise ValueError(f'{code} source identity or layout mismatch')
    revision = STAMP.search(date.get_text(' ', strip=True))
    if revision is None:
        raise ValueError(f'{code} missing revision date')
    revision = '民國 {:03d} 年 {:02d} 月 {:02d} 日'.format(*map(int, revision.groups()))
    entries = []
    articles = law.select('.law-article')
    seen = set()
    for article in articles:
        row = article.find_parent('div', class_='row')
        heading = row.select_one('.col-no a') if row else None
        match = NUMBER.fullmatch(heading.get_text(' ', strip=True)) if heading else None
        if match is None:
            raise ValueError(f'{code} missing article number')
        number = f'第{match[1].replace("－", "-")}條'
        lines = article.find_all('div', class_=re.compile(r'^line-\d+'))
        text = '\n'.join(line.get_text(strip=True) for line in lines) if lines else article.get_text('\n', strip=True)
        if not text.strip() or number in seen:
            raise ValueError(f'{code} duplicate or empty article {number}')
        seen.add(number)
        entries.append({'no': number, 'text': text})
    if not entries or entries[0]['no'] != '第1條':
        raise ValueError(f'{code} incomplete article list')
    checksum = hashlib.sha256(json.dumps(entries, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return {'name': SOURCES[code], 'source_url': source_url(code), 'revision': revision,
            'sha256': checksum, 'articles': entries}


def fetch_one(client, code):
    with client.stream('GET', source_url(code)) as response:
        response.raise_for_status()
        if 'text/html' not in response.headers.get('content-type', ''):
            raise ValueError(f'{code} unexpected content type')
        data = bytearray()
        for part in response.iter_bytes(chunk_size=65536):
            data.extend(part)
            if len(data) > MAX_BYTES:
                raise ValueError(f'{code} response exceeded the size limit')
    return parse_page(code, data.decode('utf-8-sig'))


def validate_completeness(laws, previous):
    pinned = Path(__file__).resolve().parent.parent / 'validation' / 'laws'
    for code, law in laws.items():
        old = (previous or {}).get('laws', {}).get(code)
        if old:
            minimum = len(old['articles'])
            previous_revision = tuple(map(int, STAMP.fullmatch(old['revision']).groups()))
            new_revision = tuple(map(int, STAMP.fullmatch(law['revision']).groups()))
            if new_revision < previous_revision:
                raise ValueError(f'{code} returned an older revision')
        else:
            minimum = len(re.findall(r'^## 第 [\d-]+ 條', (pinned / f'{code}.txt').read_text(encoding='utf-8'), re.M))
        if len(law['articles']) < max(1, minimum * 0.9):
            raise ValueError(f'{code} too many missing articles; review source changes before replacing the snapshot')


def sync(destination, *, index=False):
    previous = read_snapshot(destination)
    with httpx.Client(timeout=20, follow_redirects=False, headers={'User-Agent': 'Zhupinan-Law-Snapshot/1.0'}) as client:
        with ThreadPoolExecutor(max_workers=3) as executor:
            laws = dict(zip(SOURCES, executor.map(lambda code: fetch_one(client, code), SOURCES), strict=True))
    validate_completeness(laws, previous)
    snapshot = {'format': 1, 'laws': laws}
    if index:
        from demo.law_catalog import snapshot_articles
        from demo.server.law_vectors import build_index

        build_index(snapshot_articles(snapshot))
    if snapshot == previous:
        print('Official law snapshot checked; no content changes.')
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as pending_dir:
        pending = Path(pending_dir) / destination.name
        pending.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
        pending.replace(destination)
    print(f'Captured {len(laws)} official laws and {sum(len(law["articles"]) for law in laws.values())} articles.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--index', action='store_true', help='Build the Qdrant collection before publishing the snapshot.')
    args = parser.parse_args()
    sync(SNAPSHOT, index=args.index)


if __name__ == '__main__':
    main()
