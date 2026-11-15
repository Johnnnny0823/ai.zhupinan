"""Case-scoped repository helpers. Never trust case/task IDs from a client."""
import json
import sys
import uuid
from fastapi import HTTPException
from . import config, db
sys.path.insert(0,str(config.ROOT/'validation'/'scripts'))
from rules import compute_traced, RULES_VERSION, law_versions

OFFICES = {
 'onestop_register':('移工一站式服務網（勞動部）','https://fwots.wda.gov.tw/'),
 'apply_permit':('勞動部勞動力發展署','https://fwapply.wda.gov.tw/'),
 'dorm_change':('新竹市政府勞工及青年處','https://dep-labor.hccg.gov.tw/'),
 'recheck_report':('新竹市衛生局','https://dep.hcchb.gov.tw/'),
}
OFFICIAL_URLS = {v[1] for v in OFFICES.values()} | {'https://www.cdc.gov.tw/Category/Page/nU7y97g0GqJbB3kn5B-nPg','https://fwapply.wda.gov.tw/'}

def uid(): return uuid.uuid4().hex

def owned_case(c, cid, aid):
    row=c.execute('SELECT * FROM cases WHERE id=? AND owner_id=?',(cid,aid)).fetchone()
    if not row: raise HTTPException(404,'找不到這個案件')
    return dict(row)

def owned_task(c, tid, aid):
    row=c.execute('SELECT t.*,c.display_code FROM tasks t JOIN cases c ON c.id=t.case_id WHERE t.id=? AND c.owner_id=?',(tid,aid)).fetchone()
    if not row: raise HTTPException(404,'找不到這項待辦')
    return dict(row)

def serialize_task(row):
    data=dict(row)
    data['calc_trace']=json.loads(data.pop('calc_trace_json'))
    data['days_left']=(__import__('datetime').date.fromisoformat(data['due_date'])-config.today()).days if data['due_date'] else None
    data['overdue']=data['days_left'] is not None and data['days_left']<0
    data['synthetic']=True
    return data

def calculations(kind, fields):
    result=[]
    for idx,w in enumerate(fields):
        for o in compute_traced(kind,w):
            o['rule_key']=f"{o['key']}:{idx}"
            o['calc_trace']['source_excerpts']=w.get('evidence',{})
            result.append(o)
    return result

def save_document(c, aid, cid, kind, fields, source_digest, source_filename):
    owned_case(c,cid,aid)
    old=c.execute('SELECT id FROM documents WHERE case_id=? AND source_digest=?',(cid,source_digest)).fetchone()
    if old:
        return [r['id'] for r in c.execute('SELECT id FROM tasks WHERE document_id=?',(old['id'],))],True
    did=uid()
    c.execute('INSERT INTO documents VALUES(?,?,?,?,?,?,?)',(did,cid,kind,source_filename,json.dumps(fields,ensure_ascii=False),config.stamp(),source_digest))
    ids=[]
    for o in calculations(kind,fields):
        tid=uid(); ids.append(tid)
        office,url=OFFICES.get(o['key'],('衛生福利部指定健康檢查醫院','https://www.cdc.gov.tw/Category/Page/nU7y97g0GqJbB3kn5B-nPg') if o['key'].startswith('health_') else ('勞動部勞動力發展署','https://fwapply.wda.gov.tw/'))
        assert url in OFFICIAL_URLS
        c.execute('INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(tid,cid,did,o['rule_key'],o['title'],o['calc_trace']['event_date'],o['start'],o['due'],o['basis'],json.dumps(o['calc_trace']['law_versions'],ensure_ascii=False),json.dumps(o['calc_trace'],ensure_ascii=False),o['status'],office,url))
    c.execute('UPDATE cases SET updated_at=? WHERE id=?',(config.stamp(),cid))
    db.audit(c,aid,cid,'document',did,'confirm_fields')
    return ids,False
