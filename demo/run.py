"""Cross-platform entry point. Loads ignored demo/.env before importing config."""
import argparse
import logging
import os
from pathlib import Path

def main():
    env=Path(__file__).parent/'.env'
    if env.exists():
        for line in env.read_text(encoding='utf-8-sig').splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                key,value=line.split('=',1)
                if key.strip() in {'DEMO_DATA','PUBLIC_ORIGIN','DEMO_LOGIN_A','DEMO_LOGIN_B','DEMO_LOGIN_OFFICER','DEMO_DB_PATH','DEMO_TEMP_PATH','LINE_CHANNEL_ACCESS_TOKEN','LINE_CHANNEL_SECRET'}:
                    os.environ.setdefault(key.strip(),value.strip().strip('"').strip("'"))
    p=argparse.ArgumentParser();p.add_argument('command',choices=['serve','seed','codes','reset','empty','notify']);args=p.parse_args()
    from .server import config,db,auth
    from .seed import seed
    from .reset import reset
    if not config.DEMO_DATA:raise SystemExit('請先在demo/.env設定DEMO_DATA=true')
    db.initialize()
    config.DB_PATH.parent.mkdir(parents=True,exist_ok=True)
    logging.basicConfig(filename=config.DB_PATH.parent/'errors.log',level=logging.WARNING,format='%(asctime)s %(levelname)s %(name)s %(message)s')
    if args.command=='serve':
        import uvicorn
        uvicorn.run('demo.server.app:app',host='127.0.0.1',port=8765,access_log=False)
    elif args.command=='notify':
        from .server.notifications import run_schedule
        print(run_schedule())
    else:
        with db.transaction() as c:
            if args.command=='seed':seed(c)
            elif args.command=='codes':auth.issue_codes(c)
            else:reset(c,args.command=='reset')
        print('完成。登入碼不會列在輸出。')

if __name__=='__main__':main()
