"""Regression tests for the self-audit findings: LINE pair-code guessing and pre-auth upload buffering."""
import base64
import hashlib
import hmac
import json
from fastapi.testclient import TestClient
from demo.server import config, db, notifications
from demo.server.app import app


def signed(client, events, secret='line-secret'):
    raw = json.dumps({'events': events}).encode()
    sig = base64.b64encode(hmac.new(secret.encode(), raw, hashlib.sha256).digest()).decode()
    return client.post('/line/webhook', content=raw,
                       headers={'x-line-signature': sig, 'content-type': 'application/json'})


def ev(user, text, eid):
    return {'type': 'message', 'webhookEventId': eid, 'source': {'userId': user},
            'message': {'type': 'text', 'text': text}, 'replyToken': 'reply-' + eid}


def active_binding(account):
    with db.transaction() as c:
        row = c.execute('SELECT line_user_id FROM line_bindings WHERE account_id=? AND revoked_at IS NULL',
                        (account,)).fetchone()
    return row['line_user_id'] if row else None


def test_pair_code_guessing_is_throttled_per_line_user(clients, monkeypatch):
    monkeypatch.setenv('LINE_CHANNEL_SECRET', 'line-secret')
    replies = []
    monkeypatch.setattr(notifications, 'line_request',
                        lambda path, payload, retry=None: replies.append(payload['messages'][0]['text']) or {'status': 'sent', 'reason': None, 'request_id': 'r'})
    victim = clients['employer-a']
    code = victim.post('/api/line/pair-code').json()['code']
    wrong = [f'{(int(code) + i) % 1_000_000:06d}' for i in range(1, notifications.PAIR_FAILURES + 1)]
    for i, guess in enumerate(wrong):
        assert signed(victim, [ev('U_ATTACKER', guess, f'g{i}')]).status_code == 200
    # Locked: even the correct code is refused for this LINE user.
    signed(victim, [ev('U_ATTACKER', code, 'hit')])
    assert '次數過多' in replies[-1]
    assert active_binding('employer-a') is None
    # A different LINE user (the real employer) can still pair with the same valid code.
    signed(victim, [ev('U_VICTIM', code, 'legit')])
    assert active_binding('employer-a') == 'U_VICTIM'


def test_successful_pair_clears_failure_counter(clients, monkeypatch):
    monkeypatch.setenv('LINE_CHANNEL_SECRET', 'line-secret')
    monkeypatch.setattr(notifications, 'line_request', lambda *a, **k: {'status': 'sent', 'reason': None, 'request_id': 'r'})
    a = clients['employer-a']
    code = a.post('/api/line/pair-code').json()['code']
    for i in range(notifications.PAIR_FAILURES - 1):
        signed(a, [ev('U_A', f'{(int(code) + 1 + i) % 1_000_000:06d}', f'w{i}')])
    signed(a, [ev('U_A', code, 'ok')])
    assert active_binding('employer-a') == 'U_A'
    with db.transaction() as c:
        assert c.execute('SELECT COUNT(*) FROM login_attempts').fetchone()[0] == 0


def test_large_body_rejected_before_auth_for_anonymous_upload(env):
    anon = TestClient(app, headers={'Origin': config.PUBLIC_ORIGIN})
    r = anon.post('/api/documents/extract', files={'file': ('a.txt', b'x' * (1024 * 1024), 'text/plain')})
    assert r.status_code == 413, r.text
    r = anon.post('/api/tasks/any/proof', files={'file': ('a.txt', b'x' * (1024 * 1024), 'text/plain')})
    assert r.status_code == 413, r.text


def test_large_body_rejected_on_lookalike_paths(clients):
    r = clients['employer-a'].post('/static/extract', content=b'x' * (1024 * 1024))
    assert r.status_code == 413, r.text


def test_signed_in_upload_still_accepts_large_body(clients):
    r = clients['employer-a'].post('/api/documents/extract', data={'mode': 'stored'},
                                   files={'file': ('a.txt', ('合成' * 300_000).encode(), 'text/plain')})
    assert r.status_code != 413, r.text
