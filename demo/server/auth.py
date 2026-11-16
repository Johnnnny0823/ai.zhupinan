"""Opaque sessions and expiring, single-use demo login codes."""
import hashlib
import hmac
import os
import secrets
from datetime import timedelta
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

def login(request, account_id, code):
    key = digest(request.client.host if request.client else 'local')
    error = None
    token = secrets.token_urlsafe(32)
    with db.transaction() as c:
        attempt = c.execute('SELECT * FROM login_attempts WHERE key_hash=?', (key,)).fetchone()
        if attempt and attempt['blocked_until'] and attempt['blocked_until'] > config.stamp():
            error = (429, '嘗試次數過多，請於 5 分鐘後再試')
        else:
            row = c.execute('SELECT * FROM login_codes WHERE code_hash=? AND account_id=? AND consumed_at IS NULL AND expires_at>?',
                            (digest(code), account_id, config.stamp())).fetchone()
            if not row or not hmac.compare_digest(row['code_hash'], digest(code)):
                failures = (attempt['failures'] if attempt else 0) + 1
                if attempt and attempt['blocked_until'] and attempt['blocked_until'] <= config.stamp():
                    failures = 1
                blocked = (config.now()+timedelta(minutes=5)).isoformat() if failures >= 5 else None
                c.execute('INSERT INTO login_attempts VALUES(?,?,?,?) ON CONFLICT(key_hash) DO UPDATE SET failures=excluded.failures,blocked_until=excluded.blocked_until,updated_at=excluded.updated_at',
                          (key, failures, blocked, config.stamp()))
                error = (401, '帳號或登入碼錯誤；登入碼僅能使用一次')
            else:
                c.execute('UPDATE login_codes SET consumed_at=? WHERE code_hash=?', (config.stamp(), digest(code)))
                c.execute('DELETE FROM login_attempts WHERE key_hash=?', (key,))
                c.execute('DELETE FROM sessions WHERE expires_at<=?', (config.stamp(),))
                c.execute('INSERT INTO sessions VALUES(?,?,?)', (digest(token), account_id, (config.now()+timedelta(hours=config.SESSION_HOURS)).isoformat()))
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
