"""Proxy-safe per-account/client lockout plus an account-wide guessing budget."""
from datetime import timedelta
from fastapi.testclient import TestClient

from demo.server import config
from demo.server.app import app


def client(ip='203.0.113.7'):
    return TestClient(app, headers={'Origin': config.PUBLIC_ORIGIN}, client=(ip, 50000))


def login(c, code, account='employer-a', forwarded_ip=None):
    headers = {'X-Forwarded-For': forwarded_ip} if forwarded_ip else {}
    return c.post('/api/session', json={'account_id': account, 'code': code}, headers=headers)


def test_client_lock_ignores_untrusted_forwarding_header(env):
    c = client()
    for i in range(5):
        assert login(c, 'wrong-code', forwarded_ip=f'198.51.100.{i + 1}').status_code == 401
    assert login(c, 'test-code-A', forwarded_ip='198.51.100.99').status_code == 429
    assert login(client('198.51.100.9'), 'test-code-A').status_code == 200


def test_account_limit_blocks_sixty_rotating_sources(env):
    statuses = [login(client(f'198.51.100.{i + 1}'), 'wrong-code').status_code for i in range(60)]
    assert statuses[:50] == [401] * 50
    assert statuses[50:] == [429] * 10
    assert login(client(), 'test-code-A').status_code == 429
    assert login(client(), 'test-code-B', 'employer-b').status_code == 200


def test_same_source_only_locks_attempted_account(env):
    c = client()
    for _ in range(6):
        login(c, 'wrong-code')
    assert login(c, 'test-code-B', 'employer-b').status_code == 200


def test_account_budget_expires_after_ten_minutes(env, monkeypatch):
    c = client()
    for i in range(50):
        login(client(f'198.51.100.{i + 1}'), 'wrong-code')
    assert login(c, 'test-code-A').status_code == 429
    later = config.now() + timedelta(minutes=11)
    monkeypatch.setattr(config, 'now', lambda: later)
    assert login(c, 'test-code-A').status_code == 200
