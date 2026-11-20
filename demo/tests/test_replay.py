"""開場案例重播：期限必須來自規則引擎，提醒與判讀沿用系統現行設定，且不含任何帳號資料。"""
from fastapi.testclient import TestClient
from demo.server.app import app
from demo.server.domain import proof_verdict
from demo.server.notifications import REMINDER_DAYS


def test_replay_is_public_and_matches_appeal_decision(env):
    r = TestClient(app).get('/api/demo/replay')
    assert r.status_code == 200
    data = r.json()
    # 訴願決定：生效滿18個月為114/4/8，前後30日即114/3/9至114/5/8；114/5/27才健檢，晚19天。
    assert data['task']['start'] == '2025-03-09' and data['task']['due'] == '2025-05-08'
    assert data['task']['start_roc'] == '114/3/9' and data['task']['due_roc'] == '114/5/8'
    assert data['actual'] == {'date': '2025-05-27', 'roc': '114/5/27', 'verdict': 'late', 'late_days': 19, 'fine': 60000}
    assert data['task']['status'] == 'todo'
    assert '受聘僱外國人健康檢查管理辦法' in data['task']['basis']
    assert data['synthetic'] is True


def test_replay_reminders_follow_live_schedule(env):
    data = TestClient(app).get('/api/demo/replay').json()
    assert [x['days_left'] for x in data['reminders']] == list(REMINDER_DAYS)
    assert [x['date'] for x in data['reminders']] == ['2025-05-01', '2025-05-05', '2025-05-07', '2025-05-08']


def test_replay_contains_no_account_or_case_data(clients):
    text = clients['employer-a'].get('/api/demo/replay').text
    for leaked in ('employer-a', 'DEMO-A01', 'case-a', '家庭看護雇主'):
        assert leaked not in text


def test_proof_verdict_window_edges():
    assert proof_verdict('2025-03-09', '2025-05-08', '2025-05-08') == 'on_time'
    assert proof_verdict('2025-03-09', '2025-05-08', '2025-05-09') == 'late'
    assert proof_verdict('2025-03-09', '2025-05-08', '2025-03-08') == 'early'
    assert proof_verdict(None, '2025-05-08', '2020-01-01') == 'on_time'


def test_replay_page_is_served_with_csp(env):
    r = TestClient(app).get('/replay.html')
    assert r.status_code == 200 and '案例重播' in r.text
    assert "script-src 'self'" in r.headers['Content-Security-Policy']
    assert '<script>' not in r.text and 'style=' not in r.text
