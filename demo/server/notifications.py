"""Account-scoped LINE Push/Reply with durable idempotency and signature-first webhooks."""
import base64
import hashlib
import hmac
import os
import secrets
import uuid
from datetime import date, timedelta, datetime
import httpx
from fastapi import HTTPException
from . import config, db, auth

TITLE = {
 'apply_permit':'申請聘僱許可', 'health_entry':'安排入國健康檢查',
 'health_6m':'安排定期健康檢查','health_18m':'安排定期健康檢查','health_30m':'安排定期健康檢查',
 'dorm_change':'通知住宿地點變更','recheck_report':'檢查證明備查','onestop_register':'登錄入國講習',
 'renewal_window':'申請期滿續聘或轉換','permit_expiry':'確認許可屆滿安排',
 'termination_notice':'辦理聘僱終止通知','abscond_notice':'向主管機關核對通知事項','replacement_window':'核對遞補申請',
}

# Days before the due date on which a LINE reminder is pushed (0 = the due date itself).
REMINDER_DAYS = (7, 3, 1, 0)

def text_for(task):
    # Only server-owned task titles/code/date, never worker names or document fields.
    title=TITLE.get(task['rule_key'].split(':')[0],'查看待辦')
    return f"【竹聘安｜合成示範】\n{task['display_code']}｜{title}\n期限：{task['due_date'] or '需人工確認'}\n請登入查看：{config.PUBLIC_ORIGIN}/"

def preview(aid):
    with db.transaction() as c:
        rows=c.execute("SELECT t.*,c.display_code FROM tasks t JOIN cases c ON c.id=t.case_id WHERE c.owner_id=? AND t.status NOT IN ('done','needs_review') AND t.due_date<=? ORDER BY t.due_date LIMIT 8",(aid,(config.today()+timedelta(days=30)).isoformat())).fetchall()
        bound=bool(c.execute('SELECT 1 FROM line_bindings WHERE account_id=? AND revoked_at IS NULL',(aid,)).fetchone())
    return {'count':len(rows),'bound':bound,'configured':bool(os.getenv('LINE_CHANNEL_ACCESS_TOKEN') and os.getenv('LINE_CHANNEL_SECRET')),
            'text':'\n\n'.join(text_for(t) for t in rows) if rows else '目前沒有需要提醒的事項。','synthetic':True}

def pair_code(aid):
    with db.transaction() as c:
        c.execute('DELETE FROM pair_codes WHERE account_id=? OR expires_at<=?',(aid,config.stamp()))
        for _ in range(20):
            code=f'{secrets.randbelow(1_000_000):06d}'
            hashed=auth.digest(code)
            if not c.execute('SELECT 1 FROM pair_codes WHERE code_hash=?',(hashed,)).fetchone(): break
        else: raise HTTPException(503,'配對碼暫時無法產生，請重試')
        expires=(config.now()+timedelta(minutes=10)).isoformat()
        c.execute('INSERT INTO pair_codes VALUES(?,?,?,NULL)',(hashed,aid,expires))
    return {'code':code,'expires_at':expires,'instruction':'請在指定的 LINE 官方帳號對話輸入這六位數字；配對碼僅能用一次。'}

def revoke(aid):
    with db.transaction() as c:
        c.execute('UPDATE line_bindings SET revoked_at=? WHERE account_id=?',(config.stamp(),aid))
        c.execute('DELETE FROM pair_codes WHERE account_id=?',(aid,))
        db.audit(c,aid,None,'line_binding',aid,'revoke')

def verify_signature(raw, signature):
    secret=os.getenv('LINE_CHANNEL_SECRET','')
    if not secret: raise HTTPException(503,'尚未設定 LINE Webhook 密鑰')
    expected=base64.b64encode(hmac.new(secret.encode(),raw,hashlib.sha256).digest()).decode()
    if not hmac.compare_digest(expected,signature or ''): raise HTTPException(401,'LINE 簽章無效')

def line_request(path,payload,retry=None):
    token=os.getenv('LINE_CHANNEL_ACCESS_TOKEN','')
    if not token: return {'status':'failed','reason':'LINE_NOT_CONFIGURED','request_id':None}
    headers={'Authorization':'Bearer '+token}
    if retry: headers['X-Line-Retry-Key']=retry
    try:
        r=httpx.post('https://api.line.me/v2/bot/message/'+path,json=payload,headers=headers,timeout=15)
        accepted=r.status_code==409 and bool(r.headers.get('x-line-accepted-request-id'))
        return {'status':'sent' if r.is_success or accepted else 'failed',
                'reason':None if r.is_success or accepted else 'LINE_HTTP_'+str(r.status_code),
                'request_id':r.headers.get('x-line-request-id') or r.headers.get('x-line-accepted-request-id')}
    except httpx.RequestError:
        return {'status':'uncertain','reason':'LINE_NETWORK_UNCERTAIN','request_id':None}

def send_task(aid,tid,notice_type,send_date):
    with db.transaction() as c:
        # Hold write transaction during request: revoke/reset cannot race a send.
        task=c.execute("SELECT t.*,c.display_code FROM tasks t JOIN cases c ON c.id=t.case_id WHERE t.id=? AND c.owner_id=? AND t.status NOT IN ('done','needs_review')",(tid,aid)).fetchone()
        binding=c.execute('SELECT * FROM line_bindings WHERE account_id=? AND revoked_at IS NULL',(aid,)).fetchone()
        if not task or not binding: return {'status':'skipped','recipients':0,'reason':'沒有有效綁定或待辦'}
        log=c.execute('SELECT * FROM notification_log WHERE account_id=? AND task_id=? AND notice_type=? AND send_date=?',(aid,tid,notice_type,send_date)).fetchone()
        if log and log['status']=='sent': return {'status':'duplicate','recipients':0}
        if log and log['failure_reason']!='LINE_NOT_CONFIGURED' and config.now()-datetime.fromisoformat(log['claimed_at'])>timedelta(hours=23):
            return {'status':'uncertain','recipients':0,'reason':'原請求狀態待人工核對；已超過自動重試時限'}
        retry=log['retry_key'] if log else str(uuid.uuid4())
        if not log:
            c.execute("INSERT INTO notification_log(account_id,task_id,notice_type,send_date,status,retry_key,claimed_at) VALUES(?,?,?,?,'pending',?,?)",(aid,tid,notice_type,send_date,retry,config.stamp()))
        result=line_request('push',{'to':binding['line_user_id'],'messages':[{'type':'text','text':text_for(task)}]},retry)
        c.execute('UPDATE notification_log SET status=?,line_request_id=?,failure_reason=? WHERE account_id=? AND task_id=? AND notice_type=? AND send_date=?',
                  (result['status'],result['request_id'],result['reason'],aid,tid,notice_type,send_date))
        return {**result,'recipients':1 if result['status']=='sent' else 0}

def send_demo(aid):
    with db.transaction() as c:
        row=c.execute("SELECT t.id FROM tasks t JOIN cases c ON c.id=t.case_id WHERE c.owner_id=? AND t.status NOT IN ('done','needs_review') ORDER BY t.due_date LIMIT 1",(aid,)).fetchone()
    return send_task(aid,row['id'],'demo',config.today().isoformat()) if row else {'status':'skipped','recipients':0,'reason':'目前沒有待辦'}

def run_schedule(on=None):
    on=on or config.today()
    with db.transaction() as c:
        rows=c.execute("SELECT t.id,t.due_date,c.owner_id FROM tasks t JOIN cases c ON c.id=t.case_id WHERE t.status NOT IN ('done','needs_review') AND t.due_date IS NOT NULL").fetchall()
    results=[]
    for row in rows:
        days=(date.fromisoformat(row['due_date'])-on).days
        if days in REMINDER_DAYS: results.append(send_task(row['owner_id'],row['id'],f'due-{days}',on.isoformat()))
    return results

def event(event):
    event_id=event.get('webhookEventId')
    user=(event.get('source') or {}).get('userId')
    if not event_id or not user: return {'status':'ignored'}
    text=(event.get('message') or {}).get('text','').strip()
    reply=None
    with db.transaction() as c:
        if c.execute('SELECT 1 FROM webhook_events WHERE id=?',(event_id,)).fetchone(): return {'status':'duplicate'}
        c.execute('INSERT INTO webhook_events VALUES(?,?)',(event_id,config.stamp()))
        binding=c.execute('SELECT account_id FROM line_bindings WHERE line_user_id=? AND revoked_at IS NULL',(user,)).fetchone()
        if event.get('type')=='unfollow' or text=='取消綁定':
            if binding:
                c.execute('UPDATE line_bindings SET revoked_at=? WHERE account_id=?',(config.stamp(),binding['account_id']))
                c.execute('DELETE FROM pair_codes WHERE account_id=?',(binding['account_id'],))
            reply='已取消綁定，之後不再接收案件提醒。'
        elif event.get('type')=='message' and len(text)==6 and text.isascii() and text.isdigit():
            code=c.execute('SELECT * FROM pair_codes WHERE code_hash=? AND consumed_at IS NULL AND expires_at>?',(auth.digest(text),config.stamp())).fetchone()
            if not code: reply='配對碼無效或已過期，請登入雇主網頁重新取得。'
            elif binding and binding['account_id']!=code['account_id']:
                reply='此 LINE 已有綁定，請先取消原綁定。'
            else:
                c.execute('UPDATE pair_codes SET consumed_at=? WHERE code_hash=?',(config.stamp(),auth.digest(text)))
                c.execute('INSERT INTO line_bindings VALUES(?,?,?,NULL) ON CONFLICT(account_id) DO UPDATE SET line_user_id=excluded.line_user_id,bound_at=excluded.bound_at,revoked_at=NULL',
                          (code['account_id'],user,config.stamp()))
                db.audit(c,code['account_id'],None,'line_binding',code['account_id'],'pair')
                reply='已綁定此雇主的合成示範案件。輸入「待辦」查詢，或「取消綁定」解除。'
        elif event.get('type')=='message' and text=='待辦':
            if binding:
                rows=c.execute("SELECT t.*,c.display_code FROM tasks t JOIN cases c ON c.id=t.case_id WHERE c.owner_id=? AND t.status NOT IN ('done','needs_review') AND t.due_date<=? ORDER BY t.due_date LIMIT 8",(binding['account_id'],(config.today()+timedelta(days=30)).isoformat())).fetchall()
                reply='\n\n'.join(text_for(row) for row in rows) or '目前沒有近期事項。'
            else: reply='請登入雇主網頁取得六位配對碼，再於此對話輸入。'
        elif event.get('type') in ('message','follow'):
            reply='請輸入「待辦」或「取消綁定」；配對請先登入雇主網頁取得六位配對碼。'
    if reply and event.get('replyToken'):
        return line_request('reply',{'replyToken':event['replyToken'],'messages':[{'type':'text','text':reply[:4900]}]})
    return {'status':'processed'}

if __name__=='__main__':
    db.initialize()
    print(run_schedule())
