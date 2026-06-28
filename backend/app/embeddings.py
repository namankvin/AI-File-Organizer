import json
import numpy as np

from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

_model = None # Cache the model after first load so each request does not reload it.

def get_embedding_model() -> SentenceTransformer:
    global _model

    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    return _model

def build_embedding_text(file_record) -> str:
    parts = [
        file_record.name or "",
        file_record.extension or "",
        file_record.text_preview or ""
    ]

    return " ".join(parts).strip()

def generate_embedding(text: str) ->list[float]:
    model = get_embedding_model()
    embedding = model.encode(text)

    return embedding.tolist()

def serialize_embedding(embedding: list[float]) -> str:
    return json.dumps(embedding)

def deserialize_embedding(raw_embedding: str) -> list[float]:
    return json.loads(raw_embedding)

def cosine_similarity(vector_a: list[float], vector_b: list[float]) -> float: # Cosine similarity compares vector direction, which captures semantic closeness. 
    a = np.array(vector_a)
    b = np.array(vector_b)

    denominator = np.linalg.norm(a) * np.linalg.norm(b)

    if denominator == 0:
        return 0.0

    return float(np.dot(a,b) / denominator)