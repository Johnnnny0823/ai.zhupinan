"""Build the Qdrant collection from the repository's public law snapshots."""
from demo.server.law_vectors import build_index, snapshot_collection
from validation.scripts.qa import load_articles


def main():
    articles = load_articles()
    chunks = build_index(articles)
    print(f'Qdrant collection {snapshot_collection(articles)}: {len(articles)} articles, {chunks} vectors.')


if __name__ == '__main__':
    main()
