"""Opaque sessions and expiring, single-use demo login codes."""
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta
from ipaddress import ip_address
from fastapi import HTTPException, Request
from . import config, db

COOKIE = 'zpa_session'

def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()

def account(request: Request):
    with db.transaction() as c:
        row = c.execute('SELECT a.* FROM sessions s JOIN accounts a ON a.id=s.account_id WHERE s.id_hash=? AND s.expires_at>?',
                        (digest(request.cookies.get(COOKIE, '')), config.stamp())).fetchone()
    if not row:
        raise HTTPException(401, '登入已失效，請使用示範登入碼重新登入')
    return dict(row)

def employer(request: Request):
    a = account(request)
    if a['role'] != 'employer':
        raise HTTPException(403, '此功能僅開放雇主')
    return a

def officer(request: Request):
    a = account(request)
    if a['role'] != 'officer':
        raise HTTPException(403, '此功能僅開放市府承辦人')
    return a

CLIENT_FAILURES = 5
CLIENT_LOCK_MINUTES = 5
ACCOUNT_FAILURES = 50
ACCOUNT_WINDOW_MINUTES = 10


def client_ip(request: Request) -> str:
    first = request.headers.get('x-forwarded-for', '').split(',')[0].strip()
    if first:
        try:
            return str(ip_address(first))
        except ValueError:
            pass
    return request.client.host if request.client else 'local'


def _keys(request, account_id):
    return digest('client|' + account_id + '|' + client_ip(request)), digest('account|' + account_id)


def _record_failure(c, key, failures, blocked_until, started_at):
    c.execute(
        'INSERT INTO login_attempts VALUES(?,?,?,?) ON CONFLICT(key_hash) DO UPDATE SET '
        'failures=excluded.failures,blocked_until=excluded.blocked_until,updated_at=excluded.updated_at',
        (key, failures, blocked_until, started_at),
    )


def login(request, account_id, code):
    client_key, account_key = _keys(request, account_id)
    error = None
    token = secrets.token_urlsafe(32)
    current = config.now()
    with db.transaction() as c:
        attempt = c.execute('SELECT * FROM login_attempts WHERE key_hash=?', (client_key,)).fetchone()
        budget = c.execute('SELECT * FROM login_attempts WHERE key_hash=?', (account_key,)).fetchone()
        if budget and current - datetime.fromisoformat(budget['updated_at']) >= timedelta(minutes=ACCOUNT_WINDOW_MINUTES):
            c.execute('DELETE FROM login_attempts WHERE key_hash=?', (account_key,))
            budget = None
        if budget and budget['failures'] >= ACCOUNT_FAILURES:
            error = (429, '此帳號嘗試次數過多，請於10分鐘內的限制期間結束後再試')
        elif attempt and attempt['blocked_until'] and attempt['blocked_until'] > current.isoformat():
            error = (429, '此帳號與來源嘗試次數過多，請於5分鐘後再試')
        else:
            row = c.execute(
                'SELECT * FROM login_codes WHERE code_hash=? AND account_id=? AND consumed_at IS NULL AND expires_at>?',
                (digest(code), account_id, current.isoformat()),
            ).fetchone()
            if not row or not hmac.compare_digest(row['code_hash'], digest(code)):
                failures = (attempt['failures'] if attempt else 0) + 1
                if attempt and attempt['blocked_until'] and attempt['blocked_until'] <= current.isoformat():
                    failures = 1
                blocked = (current + timedelta(minutes=CLIENT_LOCK_MINUTES)).isoformat() if failures >= CLIENT_FAILURES else None
                _record_failure(c, client_key, failures, blocked, current.isoformat())
                account_failures = (budget['failures'] if budget else 0) + 1
                window_start = budget['updated_at'] if budget else current.isoformat()
                _record_failure(c, account_key, account_failures, None, window_start)
                error = (401, '帳號或登入碼錯誤；登入碼僅能使用一次')
            else:
                c.execute('UPDATE login_codes SET consumed_at=? WHERE code_hash=?', (config.stamp(), digest(code)))
                c.execute('DELETE FROM login_attempts WHERE key_hash=?', (client_key,))
                c.execute('DELETE FROM sessions WHERE expires_at<=?', (config.stamp(),))
                c.execute('INSERT INTO sessions VALUES(?,?,?)', (digest(token), account_id, (current + timedelta(hours=config.SESSION_HOURS)).isoformat()))
                a = dict(c.execute('SELECT id,role,display_name,is_admin FROM accounts WHERE id=?', (account_id,)).fetchone())
    if error:
        raise HTTPException(*error)
    return token, a


def issue_codes(c):
    codes=[os.getenv(k,'') for k in ('DEMO_LOGIN_A','DEMO_LOGIN_B','DEMO_LOGIN_OFFICER')]
    if len([x for x in codes if x])!=len({x for x in codes if x}):
        raise ValueError('三個示範登入碼必須不同')
    for aid, env in [('employer-a','DEMO_LOGIN_A'),('employer-b','DEMO_LOGIN_B'),('officer','DEMO_LOGIN_OFFICER')]:
        code = os.getenv(env, '')
        if code:
            if len(code) < 8:
                raise ValueError(f'{env} 至少需 8 字元')
            c.execute('DELETE FROM login_codes WHERE account_id=?',(aid,))
            c.execute('INSERT INTO login_codes VALUES(?,?,?,NULL) ON CONFLICT(code_hash) DO UPDATE SET account_id=excluded.account_id,expires_at=excluded.expires_at,consumed_at=NULL',
                      (digest(code), aid, (config.now()+timedelta(hours=24)).isoformat()))
