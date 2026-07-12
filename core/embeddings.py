from sentence_transformers import SentenceTransformer
import numpy as np

_model = None


def get_embedding_model():
    global _model
    if _model is None:
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model


def generate_embeddings(text: str) -> list:
    model = get_embedding_model()
    embedding = model.encode(text)
    return embedding.tolist()


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list:
    words = text.split()
    chunks = []

    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)

    return chunks