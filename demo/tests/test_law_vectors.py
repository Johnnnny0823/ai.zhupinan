"""Cover versioned indexing, quote provenance and the question API's fallback."""
import pytest

from demo.server import config, law_vectors
from demo.server.app import ARTICLES, RETRIEVER, app


def test_snapshot_hash_and_chunk_tail():
    article = {'law': '測試法規', 'no': '第1條', 'text': '甲' * 320 + '末'}
    chunks = list(law_vectors.law_chunks([article]))
    assert len(chunks) == 2 and chunks[-1][1].endswith('末')
    assert law_vectors.snapshot_collection([article]) != law_vectors.snapshot_collection([
        {**article, 'text': article['text'] + '乙'},
    ])


def test_qdrant_round_trip_and_stale_snapshot_rejection(env, monkeypatch):
    pytest.importorskip('qdrant_client')
    np = pytest.importorskip('numpy')
    articles = [
        {'law': '測試法規', 'no': '第1條', 'text': '辦理健康檢查。'},
        {'law': '測試法規', 'no': '第2條', 'text': '提出住宿變更通報。'},
    ]

    class Embedder:
        def passage_embed(self, passages, batch_size):
            assert batch_size > 0
            for passage in passages:
                axis = 0 if '健康' in passage else 1
                yield np.eye(1, law_vectors.DIMENSION, axis)[0]

        def query_embed(self, question):
            assert question == '健檢'
            yield np.eye(1, law_vectors.DIMENSION, 0)[0]

    monkeypatch.setattr(law_vectors, 'load_embedder', lambda **options: Embedder())
    assert law_vectors.build_index(articles) == 2
    assert law_vectors.build_index(articles) == 2
    opened = law_vectors.open_index(articles)
    assert opened is not None
    try:
        assert opened.search('健檢', set()) == articles
        assert opened.search('健檢', {0}) == articles[1:]
    finally:
        opened.close()
    assert law_vectors.open_index([articles[0]]) is None


def test_hybrid_question_uses_masked_input_and_preserves_ownership(clients, monkeypatch):
    question = '健檢期限 A123456789'
    keywords = RETRIEVER.top('健檢期限 〔身分證或居留證號已遮蔽〕')
    expected_index = next(i for i, article in enumerate(ARTICLES) if article not in keywords)
    searches = []

    class Index:
        def search(self, text, exclude):
            assert 'A123456789' not in text
            assert expected_index not in exclude
            searches.append(text)
            return [ARTICLES[expected_index]]

    monkeypatch.setattr(app.state, 'law_vectors', Index(), raising=False)
    assert clients['employer-a'].post('/api/qa', json={'question': question, 'case_id': 'case-b'}).status_code == 404
    assert searches == []
    assert clients['officer'].post('/api/qa', json={'question': question, 'case_id': 'case-a'}).status_code == 403
    assert searches == []
    answer = clients['officer'].post('/api/qa', json={'question': question})
    assert answer.status_code == 200
    result = answer.json()
    assert result['retrieval'] == 'qdrant_bm25'
    assert result['citations'] == keywords + [ARTICLES[expected_index]]


def test_fallback_is_reported_when_vector_search_fails(clients, monkeypatch):
    class BrokenIndex:
        def search(self, *args):
            raise RuntimeError('test failure')

    monkeypatch.setattr(app.state, 'law_vectors', BrokenIndex(), raising=False)
    question = '健檢怎麼辦'
    answer = clients['officer'].post('/api/qa', json={'question': question})
    assert answer.status_code == 200
    assert answer.json()['retrieval'] == 'bm25'
    assert answer.json()['citations'] == RETRIEVER.top(question)


def test_external_qdrant_endpoint_is_rejected(env, monkeypatch):
    pytest.importorskip('qdrant_client')
    monkeypatch.setattr(config, 'QDRANT_URL', 'https://example.invalid:6333')
    with pytest.raises(ValueError, match='本機'):
        law_vectors.connect()
