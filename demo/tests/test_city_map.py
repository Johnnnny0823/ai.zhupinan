"""市府視角地圖：區界來自內政部公開資料，件數明確標示為合成數據，頁面不帶行內腳本。"""
import json
from fastapi.testclient import TestClient
from demo.server.app import app


def test_city_page_and_assets_are_served(env):
    c = TestClient(app)
    page = c.get('/city.html')
    assert page.status_code == 200 and '合成示範數據' in page.text
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


def test_city_counts_are_labelled_synthetic(env):
    demo = TestClient(app).get('/data/city-demo.json').json()
    assert demo['synthetic'] is True and '不是' in demo['label']
    assert set(demo['districts']) == {'O01', 'O02', 'O03'}
