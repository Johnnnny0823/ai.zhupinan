"""Explicit, backup-first migration of historical SYNTHETIC state.json only."""
import argparse
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path
from .server import config,db
from .server.domain import save_document

def main():
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--case-id',required=True);p.add_argument('--owner',required=True);p.add_argument('--synthetic',action='store_true');p.add_argument('--apply',action='store_true');args=p.parse_args()
    if not config.DEMO_DATA or not args.synthetic:p.error('僅限DEMO_DATA=true且明確宣告--synthetic的既有合成資料')
    data=json.loads(args.source.read_text(encoding='utf-8'))
    if not isinstance(data.get('docs'),list):p.error('缺少docs清單')
    print(f'合成文件 {len(data["docs"])} 份；'+('將備份後遷入' if args.apply else '僅預覽，不寫入'))
    if not args.apply:return
    db.initialize()
    backup=config.DB_PATH.parent/'migration-backup';backup.mkdir(exist_ok=True)
    suffix=config.stamp().replace(':','-')
    shutil.copy2(args.source,backup/f'state-{suffix}.json')
    with sqlite3.connect(config.DB_PATH) as source,sqlite3.connect(backup/f'database-{suffix}.sqlite3') as target:source.backup(target)
    from .server.app import Worker,clean_workers,KINDS
    with db.transaction() as c:
        for doc in data['docs']:
            if doc.get('doc_type') not in KINDS:raise ValueError('不支援的文件類型，整批回滾')
            fields=clean_workers([Worker.model_validate({k:v for k,v in w.items() if k in Worker.model_fields}) for w in doc['workers']])
            digest=hashlib.sha256(json.dumps(doc,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
            save_document(c,args.owner,args.case_id,doc['doc_type'],fields,digest,'legacy-synthetic.json')
    print('已完成；原狀態與資料庫備份位於被忽略的data/migration-backup。舊的AI完成狀態不自動轉成done。')

if __name__=='__main__':main()
