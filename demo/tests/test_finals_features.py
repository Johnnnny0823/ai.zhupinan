"""Finals demo regression checks for the LINE cadence and local document pipeline."""
import io
import json
from datetime import date, timedelta

import fitz
from PIL import Image

from demo.server import config, db, llm, notifications, storage


def test_line_sends_at_all_five_milestones_once(clients, monkeypatch):
    due = date(2026, 12, 20)
    with db.transaction() as c:
        task = c.execute("SELECT id FROM tasks WHERE case_id='case-a' ORDER BY id LIMIT 1").fetchone()
        c.execute("UPDATE tasks SET status='done'")
        c.execute("UPDATE tasks SET status='todo', due_date=? WHERE id=?", (due.isoformat(), task['id']))
        c.execute("INSERT INTO line_bindings VALUES(?,?,?,NULL)", ('employer-a', 'fixture-line-id', config.stamp()))

    sent = []

    def line_request(path, payload, retry=None):
        sent.append((path, payload, retry))
        return {'status':'sent','reason':None,'request_id':'stub'}

    monkeypatch.setattr(notifications, 'line_request', line_request)
    for days in (30, 14, 7, 3, 0):
        on = due - timedelta(days=days)
        assert [item['status'] for item in notifications.run_schedule(on)] == ['sent']
        assert [item['status'] for item in notifications.run_schedule(on)] == ['duplicate']
    for days in (31, 29, 15, 8, 4, 2, 1, -1):
        assert notifications.run_schedule(due - timedelta(days=days)) == []
    assert len(sent) == 5
    assert all(call[0] == 'push' and call[1]['to'] == 'fixture-line-id' for call in sent)
    for call, countdown in zip(sent, ('剩 30 天','剩 14 天','剩 7 天','剩 3 天','今天到期'), strict=True):
        assert due.isoformat() in call[1]['messages'][0]['text'] and countdown in call[1]['messages'][0]['text']


def test_line_uses_the_same_scoped_30_day_window_in_preview_and_reply(clients, monkeypatch):
    today = date(2026, 11, 1)
    monkeypatch.setattr(config, 'today', lambda: today)
    with db.transaction() as c:
        c.execute("UPDATE tasks SET status='done'")
        a_task = c.execute("SELECT id FROM tasks WHERE case_id='case-a' ORDER BY id LIMIT 1").fetchone()
        b_task = c.execute("SELECT id FROM tasks WHERE case_id='case-b' ORDER BY id LIMIT 1").fetchone()
        days_and_statuses = [(-1, 'todo'), (0, 'todo'), (30, 'todo'), (31, 'todo'), (2, 'needs_review')]
        for days, status in days_and_statuses:
            c.execute(
                """
                INSERT INTO tasks
                SELECT ?, case_id, document_id, rule_key || ?, title, event_date, start_date, ?,
                       law_ref, law_version, calc_trace_json, ?, office, official_url
                FROM tasks WHERE id=?
                """,
                (f'fixture-task-{days}', f':{days}', (today + timedelta(days=days)).isoformat(), status, a_task['id']),
            )
        c.execute("UPDATE tasks SET status='todo', due_date=? WHERE id=?", (today.isoformat(), b_task['id']))
        c.execute("INSERT INTO line_bindings VALUES(?,?,?,NULL)", ('employer-a', 'fixture-line-id', config.stamp()))

    response = clients['employer-a'].post('/api/line/preview')
    assert response.status_code == 200
    preview = response.json()
    assert preview['reminder_days'] == [30, 14, 7, 3, 0]
    assert preview['count'] == 2 and preview['upcoming_days'] == 30

    replies = []
    monkeypatch.setattr(notifications, 'line_request', lambda path, payload: replies.append((path, payload)))
    notifications.event({'webhookEventId': 'fixture-event', 'type': 'message',
                         'source': {'userId': 'fixture-line-id'}, 'message': {'text': '待辦'}, 'replyToken': 'fixture-reply'})
    path, payload = replies[0]
    assert path == 'reply'
    assert payload['messages'][0]['text'] == preview['text']
    for days in (0, 30):
        assert (today + timedelta(days=days)).isoformat() in preview['text']
    for days in (-1, 2, 31):
        assert (today + timedelta(days=days)).isoformat() not in preview['text']
    assert 'DEMO-B01' not in preview['text']


def test_live_scan_sends_only_masked_ocr_text_and_keeps_manual_check(clients, monkeypatch):
    result = '變更日：2026-03-20\n證號：A123456789'
    monkeypatch.setattr(storage, 'read_scan_text', lambda raw: result)

    def model(system, text, model):
        assert model == 'sonnet'
        assert 'A123456789' not in text and '已遮蔽' in text and '變更日：2026-03-20' in text
        assert '不得計算' in system
        return json.dumps({'doc_type':'住宿地點變更','workers':[{'event_date':'2026-03-20',
                            'evidence':{'event_date':'變更日：2026-03-20', 'permit_start':'invented'}}]})

    monkeypatch.setattr(llm, 'call', model)
    image = (config.WEB / 'samples' / '住宿地點變更_掃描.png').read_bytes()
    response = clients['employer-a'].post('/api/documents/extract', files={'file':('synthetic.png', image, 'image/png')})
    assert response.status_code == 200, response.text
    draft = response.json()
    assert draft['mode'] == '本機 OCR ＋即時模型擷取'
    assert draft['fields'][0]['warning']
    assert set(draft['workers'][0]['evidence']) == {'event_date'}
    assert 'A123456789' not in draft['masked_preview']


def test_unknown_scan_never_enters_ocr_or_model(clients, monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError('Unverified scans may not be processed')

    monkeypatch.setattr(storage, 'read_scan_text', unexpected)
    monkeypatch.setattr(llm, 'call', unexpected)
    image = io.BytesIO()
    Image.new('RGB', (50, 50)).save(image, format='PNG')
    response = clients['employer-a'].post('/api/documents/extract', files={'file':('other.png', image.getvalue(), 'image/png')})
    assert response.status_code == 422


def test_missing_ocr_language_data_leaves_stored_mode_available(clients, monkeypatch, tmp_path):
    monkeypatch.setattr(config, 'OCR_DATA_PATH', tmp_path / 'no-models')
    image = (config.WEB / 'samples' / '住宿地點變更_掃描.png').read_bytes()
    files = {'file': ('synthetic.png', image, 'image/png')}
    a = clients['employer-a']
    response = a.post('/api/documents/extract', files=files)
    assert response.status_code == 503 and '本機 OCR' in response.text
    assert a.post('/api/documents/extract', files=files, data={'mode':'stored'}).status_code == 200


def test_live_text_pdf_keeps_page_markers_and_masks_before_the_model(clients, monkeypatch):
    with fitz.open() as document:
        document.new_page().insert_text((72, 72), 'Synthetic document sample A123456789')
        document.new_page().insert_text((72, 72), 'Arrived on 2026-11-13 (synthetic sample)')
        pdf = document.tobytes()

    def model(system, text, model):
        assert '## 第 1 頁' in text and '## 第 2 頁' in text
        assert 'A123456789' not in text and '2026-11-13' in text
        return json.dumps({'doc_type':'入國通報受理證明書','workers':[{'entry_date':'2026-11-13',
                            'evidence':{'entry_date':'Arrived on 2026-11-13'}}]})

    monkeypatch.setattr(llm, 'call', model)
    response = clients['employer-a'].post('/api/documents/extract', files={'file':('synthetic.pdf', pdf, 'application/pdf')})
    assert response.status_code == 200, response.text
    assert '## 第 2 頁' in response.json()['masked_preview']
