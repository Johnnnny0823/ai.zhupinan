"""Proxy-safe per-account/client lockout plus an account-wide guessing budget."""
from datetime import timedelta
from fastapi.testclient import TestClient

from demo.server import config
from demo.server.app import app


def client():
    return TestClient(app, headers={'Origin': config.PUBLIC_ORIGIN})


def login(c, code, ip, account='employer-a'):
    return c.post('/api/session', json={'account_id': account, 'code': code}, headers={'X-Forwarded-For': ip})


def test_proxy_client_lock_does_not_lock_other_sources(env):
    c = client()
    for _ in range(6):
        login(c, 'wrong-code', '203.0.113.7, 127.0.0.1')
    assert login(c, 'test-code-A', '203.0.113.7').status_code == 429
    assert login(client(), 'test-code-A', '198.51.100.9').status_code == 200


def test_account_limit_blocks_sixty_rotating_sources(env):
    c = client()
    statuses = [login(c, 'wrong-code', f'198.51.100.{i + 1}').status_code for i in range(60)]
    assert statuses[:50] == [401] * 50
    assert statuses[50:] == [429] * 10
    assert login(c, 'test-code-A', '203.0.113.1').status_code == 429
    assert login(c, 'test-code-B', '203.0.113.1', 'employer-b').status_code == 200


def test_same_source_only_locks_attempted_account(env):
    c = client()
    for _ in range(6):
        login(c, 'wrong-code', '203.0.113.7')
    assert login(c, 'test-code-B', '203.0.113.7', 'employer-b').status_code == 200


def test_account_budget_expires_after_ten_minutes(env, monkeypatch):
    c = client()
    for i in range(50):
        login(c, 'wrong-code', f'198.51.100.{i + 1}')
    assert login(c, 'test-code-A', '203.0.113.1').status_code == 429
    later = config.now() + timedelta(minutes=11)
    monkeypatch.setattr(config, 'now', lambda: later)
    assert login(c, 'test-code-A', '203.0.113.1').status_code == 200
