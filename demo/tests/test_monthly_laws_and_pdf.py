import fitz
import pytest

from demo import law_catalog
from demo.server import config, gemini, llm
from demo.server.pdf_to_md import convert


def test_moj_parser_verifies_identity_date_and_article_number():
    pytest.importorskip('bs4')
    from demo.sync_laws import parse_page

    html = '''<a id="hlLawName">就業服務法</a>
      <table><tr id="trLNNDate"><td>民國 114 年 1 月 20 日</td></tr></table>
      <div id="pnLawFla"><div class="row"><div class="col-no"><span>本條文有附件</span>
        <a>第 1 條</a></div><div class="law-article"><div class="line-0000">測試第一項</div>
        <div class="line-0004">測試第二項</div></div></div></div>'''
    result = parse_page('N0090001', html)
    assert result['revision'] == '民國 114 年 01 月 20 日'
    assert result['articles'] == [{'no': '第1條', 'text': '測試第一項\n測試第二項'}]
    with pytest.raises(ValueError, match='identity'):
        parse_page('N0090027', html)
    with pytest.raises(ValueError, match='article number'):
        parse_page('N0090001', html.replace('第 1 條', '無條號'))


def test_missing_official_page_leaves_last_snapshot_intact(tmp_path, monkeypatch):
    pytest.importorskip('bs4')
    from demo import sync_laws

    previous = {'format': 1, 'laws': {key: {} for key in law_catalog.SOURCES}}
    destination = tmp_path / 'current.json'
    import json
    destination.write_text(json.dumps(previous), encoding='utf-8')
    def fail(*args):
        raise ValueError('official response missing')
    monkeypatch.setattr(sync_laws, 'fetch_one', fail)
    with pytest.raises(ValueError, match='official response missing'):
        sync_laws.sync(destination)
    assert law_catalog.read_snapshot(destination) == previous


def test_existing_public_snapshot_contains_official_sources():
    snapshot = law_catalog.read_snapshot()
    assert len(snapshot['laws']) == 6
    article = next(a for a in law_catalog.snapshot_articles(snapshot) if a['law'] == '就業服務法')
    assert article['source_url'] == law_catalog.source_url('N0090001') and article['revision']


def test_pdf_to_md_preserves_table_cells_and_heading():
    with fitz.open() as document:
        page = document.new_page()
        page.insert_text((72, 58), 'Synthetic form')
        for x in (70, 180, 320):
            page.draw_line((x, 100), (x, 160))
        for y in (100, 130, 160):
            page.draw_line((70, y), (320, y))
        page.insert_text((80, 120), 'Field')
        page.insert_text((192, 120), 'Value')
        page.insert_text((80, 149), 'Entry date')
        page.insert_text((192, 149), '2026-11-13')
        result = convert(document)
    assert '# 合成公文' in result and '## 第 1 頁' in result
    assert '| Field | Value |' in result and '| Entry date | 2026-11-13 |' in result
    assert result.count('Entry date') == 1


def test_two_model_disagreement_flags_date_and_only_sends_masked_markdown(clients, monkeypatch):
    with fitz.open() as document:
        document.new_page().insert_text((72, 72), 'Entry 2026-11-13, synthetic ID A123456789')
        pdf = document.tobytes()
    monkeypatch.setattr(config, 'GEMINI_CROSSCHECK', True)
    import json
    monkeypatch.setattr(llm,'call',lambda system, user, model: json.dumps({
        'doc_type':'入國通報受理證明書','workers':[{'entry_date':'2026-11-13'}]
    }))
    def fake_gemini(system, source):
        assert '直聘移工管理專家' in system and 'PDFToMD Markdown' in source
        assert '## 第 1 頁' in source and 'A123456789' not in source
        return {'doc_type':'入國通報受理證明書','workers':[{'entry_date':'2026-11-14'}]}
    monkeypatch.setattr(gemini,'call',fake_gemini)
    response = clients['employer-a'].post('/api/documents/extract',
                                          files={'file':('synthetic.pdf',pdf,'application/pdf')})
    assert response.status_code == 200, response.text
    draft = response.json()
    assert draft['cross_check'] == 'disagreement' and draft['source_format'] == 'markdown'
    assert draft['fields'][0]['warning'] and draft['fields'][0]['value'] == '2026-11-13'


def test_approved_scan_pdf_uses_ocr_before_markdown(clients, monkeypatch):
    from demo.server import storage
    calls = []
    def paddle(raw):
        assert raw.startswith(b'\x89PNG')
        calls.append(1)
        return '合成公文變更日：115年3月20日'
    def model(system, source, model):
        assert 'PDFToMD Markdown' in source and '## 第 1 頁' in source and '115年3月20日' in source
        return '{"doc_type":"住宿地點變更","workers":[{"event_date":"2026-03-20"}]}'
    monkeypatch.setattr(storage,'paddle_text',paddle)
    monkeypatch.setattr(llm,'call',model)
    sample = config.WEB/'samples'/'住宿地點變更_合成掃描.pdf'
    response = clients['employer-a'].post('/api/documents/extract',
                                          files={'file':('scan.pdf',sample.read_bytes(),'application/pdf')})
    assert response.status_code == 200 and len(calls) == 1
    result = response.json()
    assert result['source_format'] == 'markdown' and result['fields'][0]['warning']


def test_gemini_transport_sets_system_prompt_and_requests_json(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'fixture-token')
    monkeypatch.delenv('DEMO_GEMINI_MODEL', raising=False)
    import httpx

    def fake_post(url, **options):
        assert url.endswith('/models/gemini-3.1-pro-preview:generateContent')
        assert options['headers']['x-goog-api-key'] == 'fixture-token'
        assert options['json']['systemInstruction'] == {'parts': [{'text':'直聘移工管理專家'}]}
        assert options['json']['contents'][0]['parts'][0]['text'] == '已遮蔽 Markdown'
        assert options['json']['generationConfig']['responseMimeType'] == 'application/json'
        return httpx.Response(200, request=httpx.Request('POST', url),
            json={'candidates':[{'content':{'parts':[{'text':'{"doc_type":"住宿地點變更","workers":[]}'}]}}]})
    monkeypatch.setattr(gemini.httpx, 'post', fake_post)
    assert gemini.call('直聘移工管理專家','已遮蔽 Markdown')['doc_type'] == '住宿地點變更'
