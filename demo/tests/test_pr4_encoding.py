"""Only plausible text is decoded; UTF-16 requires a BOM."""
import json
import pytest
from demo.server import llm, storage

TEXT = '【合成示範】\n入國日期：115/03/05\n'


@pytest.mark.parametrize('encoding', ['utf-8', 'utf-8-sig', 'utf-16', 'cp950'])
def test_supported_text_encodings_reach_extraction_without_garbling(clients, monkeypatch, encoding):
    seen = []
    def model(_system, user, **_kwargs):
        seen.append(user)
        return json.dumps({'doc_type': '入國通報受理證明書', 'workers': [{'entry_date': '2026-03-05', 'evidence': {'entry_date': '115/03/05'}}]})
    monkeypatch.setattr(llm, 'call', model)
    response = clients['employer-a'].post('/api/documents/extract', files={'file': ('sample.txt', TEXT.encode(encoding), 'text/plain')})
    assert response.status_code == 200, response.text
    assert json.loads(seen[0])['document'] == TEXT
    assert response.json()['fields'][0]['warning']


@pytest.mark.parametrize('raw', [bytes(range(1, 255)) * 4, b'abc\x00def', b'\xff\xfe\x01', TEXT.encode('utf-16-le'), b'x' * 97 + b'\x01' * 3])
def test_binary_or_non_printable_text_still_rejected(clients, raw):
    response = clients['employer-a'].post('/api/documents/extract', files={'file': ('x.txt', raw, 'text/plain')}, data={'mode': 'stored'})
    assert response.status_code == 415, response.text
    assert '請另存為 UTF-8' in response.json()['detail']


def test_printable_ratio_must_be_above_97_percent():
    assert storage.decode_text(b'x' * 98 + b'\x01' * 2) is not None
    assert storage.decode_text(b'x' * 97 + b'\x01' * 3) is None


def test_utf16_fixed_sample_can_use_stored_result(clients):
    from demo.server.samples import SAMPLES
    response = clients['employer-a'].post('/api/documents/extract', files={'file': ('sample.txt', SAMPLES['entry']['text'].encode('utf-16'), 'text/plain')}, data={'mode': 'stored'})
    assert response.status_code == 200 and response.json()['mode'] == '預存示範結果'


@pytest.mark.parametrize('encoding', ['utf-16', 'cp950'])
def test_encoded_fixed_proof_stays_readable(clients, encoding):
    client = clients['employer-a']
    tid = client.get('/api/cases/case-a').json()['tasks'][0]['id']
    sample = client.get('/api/tasks/' + tid + '/proof-sample').json()['text']
    response = client.post('/api/tasks/' + tid + '/proof', files={'file': ('proof.txt', sample.encode(encoding), 'text/plain')}, data={'mode': 'stored'})
    assert response.status_code == 200, response.text
    assert response.json()['proof']['verdict'] == 'on_time'
