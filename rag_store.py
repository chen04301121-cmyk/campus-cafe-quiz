"""Vector store for the RAG Text-to-SQL feature.

This file does two jobs:
1. Store the knowledge documents (from rag_knowledge.py) in ChromaDB.
2. Retrieve the documents that are most similar to a user's question.

ChromaDB turns every text into a list of numbers (an "embedding") using its
built-in default model, so we do not need any API key for this part.
"""

from pathlib import Path

import chromadb

from rag_knowledge import build_documents

# The database lives in a folder next to this file.
# It is created automatically the first time we run.
DB_PATH = str(Path(__file__).with_name("chroma_db"))
COLLECTION_NAME = "cafe_sql_knowledge"


def get_collection():
    """Open (or create) the ChromaDB collection that holds our documents."""
    client = chromadb.PersistentClient(path=DB_PATH)
    # Cosine distance: a smaller number means the texts are more similar.
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def build_index():
    """Write all knowledge documents into ChromaDB.

    upsert means "insert, or update if the id already exists", so running
    this many times never creates duplicates.
    """
    collection = get_collection()
    documents = build_documents()
    collection.upsert(
        ids=[doc["id"] for doc in documents],
        documents=[doc["text"] for doc in documents],
        metadatas=[{"kind": doc["kind"]} for doc in documents],
    )
    return collection.count()


def ensure_index():
    """Build the index only if it is empty (used when the website starts)."""
    collection = get_collection()
    expected = len(build_documents())
    if collection.count() != expected:
        build_index()
    return get_collection()


def retrieve(question, n_results=4):
    """Return the documents most similar to the question.

    Each result is a dict with: id, kind, text, distance.
    """
    collection = ensure_index()
    result = collection.query(
        query_texts=[question],
        n_results=n_results,
    )

    # ChromaDB returns one list per query text; we only sent one question.
    hits = []
    for doc_id, text, meta, distance in zip(
        result["ids"][0],
        result["documents"][0],
        result["metadatas"][0],
        result["distances"][0],
    ):
        hits.append(
            {
                "id": doc_id,
                "kind": meta["kind"],
                "text": text,
                "distance": distance,
            }
        )
    return hits


if __name__ == "__main__":
    # Self-check: build the index, then try a few sample questions.
    print(f"Documents stored: {build_index()}")

    test_questions = [
        "How many units of each drink did we sell?",
        "Which items never got ordered?",
        "What is the total money earned per category?",
    ]
    for question in test_questions:
        print(f"\nQuestion: {question}")
        for hit in retrieve(question, n_results=3):
            first_line = hit["text"].splitlines()[0][:70]
            print(f"  [{hit['distance']:.3f}] {hit['kind']:<9} {hit['id']}: {first_line}")
