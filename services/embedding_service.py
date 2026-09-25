import os
from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer


class EmbeddingService:
    _model = None

    @classmethod
    def get_model(cls):
        if cls._model is None:
            cls._model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        return cls._model

    @classmethod
    def embed_text(cls, text: str) -> List[float]:
        model = cls.get_model()
        embedding = model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        return embedding.astype(float).tolist()

    @classmethod
    def embed_batch(cls, texts: List[str]) -> List[List[float]]:
        model = cls.get_model()
        embeddings = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return embeddings.astype(float).tolist()
