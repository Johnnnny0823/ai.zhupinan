"""Read the monthly public-law catalog independently of deadline-rule inputs."""
import json
from pathlib import Path

SNAPSHOT = Path(__file__).with_name('law_data') / 'current.json'
SOURCES = {
    'A0030020': '訴願法',
    'A0030055': '行政程序法',
    'L0050018': '受聘僱外國人健康檢查管理辦法',
    'N0090001': '就業服務法',
    'N0090027': '雇主聘僱外國人許可及管理辦法',
    'N0090028': '私立就業服務機構收費項目及金額標準',
}


def source_url(code):
    return f'https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode={code}'


def read_snapshot(path=None):
    path = path or SNAPSHOT
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding='utf-8'))
    if data['format'] != 1 or set(data['laws']) != set(SOURCES):
        raise ValueError('Invalid public law snapshot')
    return data


def snapshot_articles(snapshot):
    if snapshot is None:
        from validation.scripts.qa import load_articles

        return load_articles()
    return [
        {'law': law['name'], 'no': article['no'], 'text': article['text'],
         'source_url': law['source_url'], 'revision': law['revision']}
        for law in snapshot['laws'].values() for article in law['articles']
    ]


def snapshot_versions(snapshot):
    if snapshot is None:
        return None
    return {code: {key: law[key] for key in ('revision', 'source_url', 'sha256')}
            for code, law in snapshot['laws'].items()}
