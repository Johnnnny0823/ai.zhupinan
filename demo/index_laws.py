"""Build the Qdrant collection from the repository's public law snapshots."""
from demo.server.law_vectors import build_index, snapshot_collection
from demo.law_catalog import read_snapshot, snapshot_articles


def main():
    articles = snapshot_articles(read_snapshot())
    chunks = build_index(articles)
    print(f'Qdrant collection {snapshot_collection(articles)}: {len(articles)} articles, {chunks} vectors.')


if __name__ == '__main__':
    main()
