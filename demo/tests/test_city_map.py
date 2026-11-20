"""市府視角地圖：區界與人口都來自內政部公開資料，頁面不帶行內腳本。"""
import json
from fastapi.testclient import TestClient
from demo.server.app import app


def test_city_page_and_assets_are_served(env):
    c = TestClient(app)
    page = c.get('/city.html')
    assert page.status_code == 200 and '新竹市高齡人口' in page.text
    assert "script-src 'self'" in page.headers['Content-Security-Policy']
    assert '<script>' not in page.text and 'style=' not in page.text
    assert c.get('/vendor/three.module.min.js').status_code == 200


def test_district_boundaries_cover_three_hsinchu_city_districts(env):
    geo = TestClient(app).get('/data/hsinchu-districts.json').json()
    assert [d['eng'] for d in geo['districts']] == ['East District', 'North District', 'Xiangshan District']
    assert '內政部' in geo['source']
    for d in geo['districts']:
        ring = d['polygons'][0][0]
        assert len(ring) > 50
        assert all(120.8 < lon < 121.1 and 24.6 < lat < 24.9 for lon, lat in ring)


def test_city_ages_are_official_and_add_up(env):
    stats = TestClient(app).get('/data/hsinchu-age.json').json()
    assert stats['synthetic'] is False and '內政部戶政司' in stats['source']
    d = stats['districts']
    assert set(d) == {'O01', 'O02', 'O03'}
    # 113 年 12 月底新竹市總人口 457,242 人（新竹市民政處各區人口統計簡表）
    assert sum(x['pop'] for x in d.values()) == stats['city']['pop'] == 457242
    assert sum(x['age65'] for x in d.values()) == stats['city']['age65']
    assert sum(x['age80'] for x in d.values()) == stats['city']['age80']
    assert sum(x['villages'] for x in d.values()) == 122
    for x in d.values():
        assert x['age80'] < x['age65'] < x['pop']
