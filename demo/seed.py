"""python -m demo.seed [--codes-only]. No real data is seeded."""
import argparse
import hashlib
from .server import config, db, auth
from .server.domain import save_document
from .server.samples import SAMPLES

def seed(c):
    if not config.DEMO_DATA:
        raise RuntimeError('僅允許 DEMO_DATA=true 的合成示範環境')
    for aid,role,name,admin in [('employer-a','employer','家庭看護雇主 A｜合成示範',0),('employer-b','employer','產業雇主 B｜合成示範',0),('officer','officer','市府承辦人｜合成示範管理員',1)]:
        c.execute('INSERT OR IGNORE INTO accounts VALUES(?,?,?,?,?)',(aid,role,name,config.stamp(),admin))
    auth.issue_codes(c)
    for cid,aid,code in [('case-a','employer-a','DEMO-A01'),('case-b','employer-b','DEMO-B01')]:
        c.execute('INSERT OR IGNORE INTO cases VALUES(?,?,?,?,?)',(cid,aid,code,config.stamp(),config.stamp()))
    for key,cid,aid in [('recheck','case-a','employer-a'),('dorm','case-b','employer-b')]:
        s=SAMPLES[key]
        save_document(c,aid,cid,s['kind'],s['fields'],hashlib.sha256(s['text'].encode()).hexdigest(),key+'.txt')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--codes-only',action='store_true');args=parser.parse_args()
    db.initialize()
    with db.transaction() as c:
        if args.codes_only: auth.issue_codes(c)
        else: seed(c)
    print('合成示範資料／一次性登入碼已就緒；未列出登入碼。')

if __name__=='__main__': main()
