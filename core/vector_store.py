import chromadb
from core.embeddings import generate_embeddings, chunk_text

_chroma_client = None
_collection = None


def get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path="./chroma_db")
    return _chroma_client


def get_collection(collection_name: str = "documents"):
    global _collection
    if _collection is None:
        client = get_chroma_client()
        _collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hf:space": "cosine"}
        )
    return _collection


def store_document(document_id: str, text: str, metadata: dict = {}):
    collection = get_collection()
    chunks = chunk_text(text)

    for i, chunk in enumerate(chunks):
        embedding = generate_embeddings(chunk)
        collection.add(
            ids=[f"{document_id}chunk{i}"],
            embeddings=[embedding],
            documents=[chunk],
            metadatas=[{**metadata, "chunk_index": i}]
        )

    return len(chunks)


def search_documents(query: str, n_results: int = 5, user_id: int = None):
    collection = get_collection()
    query_embedding = generate_embeddings(query)

    where = {"user_id": str(user_id)} if user_id else None

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where
    )

    return results