"""Local Qdrant index of the approved, versioned public statute snapshots."""
import hashlib
import json
import logging
from threading import Lock
from urllib.parse import urlsplit

from . import config

MODEL = 'BAAI/bge-small-zh-v1.5'
EMBEDDING_REVISION = 'fastembed-0.9.1'
DIMENSION = 512
CHUNK_SIZE = 320
CHUNK_STRIDE = 260
logger = logging.getLogger('zhupinan')


def snapshot_collection(articles):
    snapshot = json.dumps([MODEL, EMBEDDING_REVISION, CHUNK_SIZE, CHUNK_STRIDE, articles], ensure_ascii=False, sort_keys=True)
    return 'zhupinan_laws_' + hashlib.sha256(snapshot.encode('utf-8')).hexdigest()[:24]


def law_chunks(articles):
    for article_id, article in enumerate(articles):
        text = article['text']
        for start in range(0, max(1, len(text) - CHUNK_SIZE + CHUNK_STRIDE), CHUNK_STRIDE):
            yield article_id, f"{article['law']} {article['no']}\n{text[start:start + CHUNK_SIZE]}"


def load_embedder(*, local_only):
    from fastembed import TextEmbedding

    return TextEmbedding(MODEL, cache_dir=str(config.LAW_EMBEDDING_CACHE), threads=2, local_files_only=local_only)


def connect():
    from qdrant_client import QdrantClient

    if config.QDRANT_URL:
        url = urlsplit(config.QDRANT_URL)
        if (url.scheme not in ('http', 'https') or url.hostname not in ('127.0.0.1', 'localhost', '::1')
                or url.username is not None or url.password is not None or url.path not in ('', '/')
                or url.query or url.fragment):
            raise ValueError('DEMO_QDRANT_URL 僅接受本機 Qdrant 服務網址')
        return QdrantClient(url=config.QDRANT_URL, timeout=5)
    return QdrantClient(path=str(config.LAW_VECTOR_PATH), force_disable_check_same_thread=True)


def build_index(articles, *, local_only=False):
    from qdrant_client import models

    collection = snapshot_collection(articles)
    chunks = list(law_chunks(articles))
    client = connect()
    try:
        exists = client.collection_exists(collection)
        if exists and client.count(collection, exact=True).count == len(chunks):
            return len(chunks)
        embedder = load_embedder(local_only=local_only)
        if not exists:
            client.create_collection(collection, vectors_config=models.VectorParams(
                size=DIMENSION, distance=models.Distance.COSINE,
            ))
        for offset in range(0, len(chunks), 32):
            batch = chunks[offset:offset + 32]
            vectors = embedder.passage_embed([text for _, text in batch], batch_size=32)
            points = [
                models.PointStruct(id=offset + index, vector=vector.tolist(), payload={'article_id': article_id})
                for index, ((article_id, _), vector) in enumerate(zip(batch, vectors, strict=True))
            ]
            client.upsert(collection, points=points)
        if client.count(collection, exact=True).count != len(chunks):
            raise RuntimeError('法規向量索引的分段數不符')
        return len(chunks)
    finally:
        client.close()


class LawVectors:
    def __init__(self, client, embedder, articles, collection):
        self.client = client
        self.embedder = embedder
        self.articles = articles
        self.collection = collection
        self.lock = Lock()

    def search(self, question, exclude, limit=2):
        from qdrant_client import models

        # Qdrant's local database uses a single connection. Search is called from
        # FastAPI worker threads, so keep this connection's use serialized.
        with self.lock:
            query = next(self.embedder.query_embed(question)).tolist()
            candidates = self.client.query_points(
                collection_name=self.collection, query=query,
                query_filter=models.Filter(must_not=[
                    models.FieldCondition(key='article_id', match=models.MatchAny(any=list(exclude))),
                ]) if exclude else None,
                limit=20, with_payload=True,
            ).points
        articles = []
        seen = set(exclude)
        for point in candidates:
            article_id = (point.payload or {}).get('article_id')
            if type(article_id) is not int or not 0 <= article_id < len(self.articles) or article_id in seen:
                continue
            seen.add(article_id)
            articles.append(self.articles[article_id])
            if len(articles) == limit:
                break
        return articles

    def close(self):
        self.client.close()


def open_index(articles):
    if not config.QDRANT_URL and not config.LAW_VECTOR_PATH.is_dir():
        return None
    client = None
    try:
        collection = snapshot_collection(articles)
        client = connect()
        if client.collection_exists(collection) and client.count(collection, exact=True).count == sum(1 for _ in law_chunks(articles)):
            return LawVectors(client, load_embedder(local_only=True), articles, collection)
        client.close()
    except Exception:
        if client is not None:
            client.close()
        logger.warning('law_vector_index_unavailable')
    return None


def retrieve(lexical, vectors, question, articles):
    hits = lexical.top(question)
    if vectors is None:
        return hits, 'bm25'
    try:
        keys = {(item['law'], item['no']) for item in hits}
        excluded = {i for i, item in enumerate(articles) if (item['law'], item['no']) in keys}
        return hits + vectors.search(question, excluded), 'qdrant_bm25'
    except Exception:
        # Existing statute retrieval remains available even if the local model or index fails.
        logger.warning('law_vector_search_unavailable')
        return hits, 'bm25'
