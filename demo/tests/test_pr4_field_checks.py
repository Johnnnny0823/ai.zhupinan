"""Date warnings and mandatory per-field review before extraction becomes a case."""
import json
from copy import deepcopy

import pytest
from demo.server import config, llm


@pytest.mark.parametrize('excerpt', ['115/03/05', '115.3.5', '115-03-05', '民國115年3月5日', '一一五年三月五日'])
def test_non_gregorian_dates_have_individual_warning(excerpt):
    from demo.server.documents import field_warning
    assert field_warning(excerpt, False)


@pytest.mark.parametrize('excerpt', ['2026/03/05', '2026-03-05', '2026年03月05日'])
def test_plain_gregorian_date_is_not_flagged(excerpt):
    from demo.server.documents import field_warning
    assert field_warning(excerpt, False) is None


def test_scan_and_missing_excerpt_are_flagged():
    from demo.server.documents import field_warning
    assert field_warning('2026-03-05', True)
    assert field_warning('', False)


def extract(client, monkeypatch, evidence='115/03/05'):
    text = '【合成示範】\n入國日期：' + evidence + '\n許可迄日：2029/03/04\n'
    monkeypatch.setattr(llm, 'call', lambda *_args, **_kwargs: json.dumps({
        'doc_type': '入國通報受理證明書',
        'workers': [{'entry_date': '2026-03-05', 'permit_end': '2029-03-04', 'evidence': {'entry_date': evidence, 'permit_end': '2029/03/04'}}],
    }))
    response = client.post('/api/documents/extract', files={'file': ('sample.txt', text.encode('utf-8'), 'text/plain')})
    assert response.status_code == 200, response.text
    draft = response.json()
    body = {'case_id': 'case-a', 'draft_id': draft['draft_id'], 'document_kind': draft['document_kind'], 'fields': draft['workers'], 'confirmed': True}
    return draft, body


def test_unchanged_flagged_field_requires_its_own_check(clients, monkeypatch):
    client = clients['employer-a']
    before = len(client.get('/api/cases/case-a').json()['tasks'])
    draft, body = extract(client, monkeypatch)
    warnings = {f['field']: f['warning'] for f in draft['fields']}
    assert warnings['entry_date'] and warnings['permit_end'] is None
    assert client.post('/api/documents/confirm', json={**body, 'preview_only': True}).status_code == 200
    refused = client.post('/api/documents/confirm', json=body)
    assert refused.status_code == 422
    assert refused.json()['unchecked'] == ['0:entry_date']
    assert len(client.get('/api/cases/case-a').json()['tasks']) == before
    accepted = client.post('/api/documents/confirm', json={**body, 'checked': ['0:entry_date']})
    assert accepted.status_code == 200, accepted.text


def test_edited_flagged_date_is_human_confirmed_and_recomputed(clients, monkeypatch):
    client = clients['employer-a']
    _, body = extract(client, monkeypatch)
    body = deepcopy(body)
    body['fields'][0]['entry_date'] = '2026-03-06'
    accepted = client.post('/api/documents/confirm', json=body)
    assert accepted.status_code == 200, accepted.text
    tasks = [client.get('/api/tasks/' + tid).json()['task'] for tid in accepted.json()['task_ids']]
    permit = next(t for t in tasks if t['rule_key'].startswith('apply_permit:'))
    assert permit['calc_trace']['event_date'] == '2026-03-06'
    assert permit['due_date'] == '2026-03-23'


def test_each_worker_requires_the_matching_checked_key(clients, monkeypatch):
    client = clients['employer-a']
    _, body = extract(client, monkeypatch)
    # A key for another worker/field must not acknowledge the flagged entry date.
    refused = client.post('/api/documents/confirm', json={**body, 'checked': ['1:entry_date', '0:permit_end']})
    assert refused.status_code == 422 and refused.json()['unchecked'] == ['0:entry_date']


def test_fabricated_excerpt_is_removed_and_requires_review(clients, monkeypatch):
    client = clients['employer-a']
    monkeypatch.setattr(llm, 'call', lambda *_a, **_kw: json.dumps({'doc_type': '住宿地點變更', 'workers': [{'event_date': '2026-03-05', 'evidence': {'event_date': 'not in this document'}}]}))
    draft = client.post('/api/documents/extract', files={'file': ('x.txt', '【合成示範】住宿變更'.encode('utf-8'), 'text/plain')}).json()
    assert draft['fields'][0]['source_excerpt'] == ''
    assert '原文' in draft['fields'][0]['warning']
    body = {'case_id': 'case-a', 'draft_id': draft['draft_id'], 'document_kind': draft['document_kind'], 'fields': draft['workers'], 'confirmed': True}
    refused = client.post('/api/documents/confirm', json=body)
    assert refused.status_code == 422 and refused.json()['unchecked'] == ['0:event_date']


def test_synthetic_scan_checks_each_worker(clients):
    client = clients['employer-a']
    raw = (config.WEB / 'samples/住宿地點變更_掃描.png').read_bytes()
    draft = client.post('/api/documents/extract', files={'file': ('scan.png', raw, 'image/png')}, data={'mode': 'stored'}).json()
    body = {'case_id': 'case-a', 'draft_id': draft['draft_id'], 'document_kind': draft['document_kind'], 'fields': draft['workers'], 'confirmed': True, 'checked': ['0:event_date']}
    refused = client.post('/api/documents/confirm', json=body)
    assert refused.status_code == 422 and refused.json()['unchecked'] == ['1:event_date']
    assert all('掃描' in field['warning'] for field in draft['fields'])
    body['checked'].append('1:event_date')
    assert client.post('/api/documents/confirm', json=body).status_code == 200
