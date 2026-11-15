import os
os.environ['DEMO_DATA']='true'
import pytest
from fastapi.testclient import TestClient
from demo.server import config,db,auth
from demo.server.app import app,DRAFTS
from demo.seed import seed

@pytest.fixture
def env(tmp_path,monkeypatch):
    monkeypatch.setattr(config,'DB_PATH',tmp_path/'demo.sqlite3')
    monkeypatch.setattr(config,'TEMP_PATH',tmp_path/'temp')
    monkeypatch.setattr(config,'DEMO_DATA',True)
    monkeypatch.setattr(config,'PUBLIC_ORIGIN','http://testserver')
    monkeypatch.setenv('DEMO_LOGIN_A','test-code-A')
    monkeypatch.setenv('DEMO_LOGIN_B','test-code-B')
    monkeypatch.setenv('DEMO_LOGIN_OFFICER','test-code-officer')
    monkeypatch.delenv('LINE_CHANNEL_ACCESS_TOKEN',raising=False)
    monkeypatch.delenv('LINE_CHANNEL_SECRET',raising=False)
    db.initialize()
    with db.transaction() as c: seed(c)
    DRAFTS.clear()
    return tmp_path

@pytest.fixture
def clients(env):
    clients={}
    for aid,code in [('employer-a','test-code-A'),('employer-b','test-code-B'),('officer','test-code-officer')]:
        c=TestClient(app,headers={'Origin':config.PUBLIC_ORIGIN})
        r=c.post('/api/session',json={'account_id':aid,'code':code})
        assert r.status_code==200,r.text
        clients[aid]=c
    return clients
