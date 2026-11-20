"""給移工本人的母語提醒：只放事項與日期、依帳號隔離、模型翻譯要通過日期核對。"""
import pytest
from demo.server import llm
from demo.server.samples import SAMPLES


def entry_tasks(client):
    """以預存模式確認入國合成文件，取得一組含健檢期間的待辦。"""
    draft = client.post('/api/documents/extract', files={'file': ('sample.txt', SAMPLES['entry']['text'].encode(), 'text/plain')}, data={'mode': 'stored'}).json()
    body = {'case_id': 'case-a', 'draft_id': draft['draft_id'], 'document_kind': draft['document_kind'], 'fields': draft['workers'],
            'checked': [f"{f['worker_index']}:{f['field']}" for f in draft['fields'] if f['warning']], 'confirmed': True}
    r = client.post('/api/documents/confirm', json=body)
    assert r.status_code == 200, r.text
    return client.get('/api/cases/case-a').json()['tasks']


def pick(tasks, prefix):
    return next(t for t in tasks if t['rule_key'].startswith(prefix))


@pytest.mark.parametrize('lang,word', [('id', 'Pemeriksaan kesehatan berkala'), ('vi', 'Khám sức khỏe định kỳ'), ('en', 'Regular health check')])
def test_stored_notice_has_dates_and_hotline_only(clients, lang, word):
    c = clients['employer-a']
    task = pick(entry_tasks(c), 'health_6m')
    r = c.post(f"/api/tasks/{task['id']}/worker-notice", json={'lang': lang, 'mode': 'stored'})
    assert r.status_code == 200, r.text
    data = r.json()
    assert word in data['text'] and task['start_date'] in data['text'] and task['due_date'] in data['text'] and '1955' in data['text']
    assert task['due_date'] in data['zh']
    for leaked in ('DEMO-A01', 'PERSON', '移工代號', 'employer-a'):
        assert leaked not in data['text'] and leaked not in data['zh']


def test_employer_only_task_is_not_sent_to_worker(clients):
    c = clients['employer-a']
    task = pick(entry_tasks(c), 'apply_permit')
    assert c.post(f"/api/tasks/{task['id']}/worker-notice", json={'lang': 'id'}).status_code == 409


def test_other_employer_and_officer_cannot_generate(clients):
    task = pick(entry_tasks(clients['employer-a']), 'health_6m')
    assert clients['employer-b'].post(f"/api/tasks/{task['id']}/worker-notice", json={'lang': 'id'}).status_code == 404
    assert clients['officer'].post(f"/api/tasks/{task['id']}/worker-notice", json={'lang': 'id'}).status_code == 403


def test_live_translation_must_keep_dates(clients, monkeypatch):
    c = clients['employer-a']
    task = pick(entry_tasks(c), 'health_6m')
    good = f'{{"text": "Periksa antara {task["start_date"]} dan {task["due_date"]}. Hubungi 1955."}}'
    monkeypatch.setattr(llm, 'call', lambda *a, **k: good)
    r = c.post(f"/api/tasks/{task['id']}/worker-notice", json={'lang': 'id', 'mode': 'live'})
    assert r.status_code == 200 and '核對' in r.json()['mode']
    monkeypatch.setattr(llm, 'call', lambda *a, **k: '{"text": "Periksa sebelum 2099-01-01. Hubungi 1955."}')
    assert c.post(f"/api/tasks/{task['id']}/worker-notice", json={'lang': 'id', 'mode': 'live'}).status_code == 422


def test_live_translation_reports_model_failure(clients, monkeypatch):
    c = clients['employer-a']
    task = pick(entry_tasks(c), 'health_6m')
    def boom(*a, **k): raise llm.LLMError('找不到 Claude CLI')
    monkeypatch.setattr(llm, 'call', boom)
    assert c.post(f"/api/tasks/{task['id']}/worker-notice", json={'lang': 'vi', 'mode': 'live'}).status_code == 502


def test_unknown_language_rejected(clients):
    task = pick(entry_tasks(clients['employer-a']), 'health_6m')
    assert clients['employer-a'].post(f"/api/tasks/{task['id']}/worker-notice", json={'lang': 'fr'}).status_code == 422
