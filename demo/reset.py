"""python -m demo.reset [--empty]. All database deletions use a single transaction."""
import argparse
from .server import config, db, storage
from .seed import seed

def reset(c, rebuild=True):
    if not config.DEMO_DATA: raise RuntimeError('禁止重置非示範環境')
    # Delete session tokens as well. Cleanup failure prevents database commit.
    for sql in ('DELETE FROM qa_events','DELETE FROM audit_events','DELETE FROM notification_log','DELETE FROM proofs','DELETE FROM tasks','DELETE FROM documents','DELETE FROM cases','DELETE FROM line_bindings','DELETE FROM pair_codes','DELETE FROM webhook_events','DELETE FROM sessions','DELETE FROM login_codes','DELETE FROM login_attempts'):
        c.execute(sql)
    storage.clean_runtime()
    if rebuild: seed(c)

def main():
    p=argparse.ArgumentParser();p.add_argument('--empty',action='store_true');args=p.parse_args()
    db.initialize()
    with db.transaction() as c: reset(c,not args.empty)
    print('已清空合成資料'+('' if args.empty else '並重建固定合成案件')+'；所有登入已失效。')

if __name__=='__main__': main()
