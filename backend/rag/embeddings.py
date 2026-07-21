"""Document embedding generation for RAG retrieval."""

from __future__ import annotations

import hashlib
from typing import Any

import numpy as np
from backend.config.settings import get_settings


class EmbeddingEngine:
    """Generates embeddings using sentence-transformers with TF-IDF fallback."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", use_cpu: bool = True) -> None:
        self.model_name = model_name
        self._model = None
        self._vocabulary: dict[str, int] = {}
        self._idf: dict[str, float] = {}
        settings = get_settings()

        if not settings.use_transformer_embeddings:
            print("ℹ Using TF-IDF fallback embeddings (USE_TRANSFORMER_EMBEDDINGS is disabled)")
            return

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            print("⚠ sentence-transformers is unavailable, falling back to TF-IDF")
            return

        import os
        os.environ['TRANSFORMERS_CACHE'] = '/tmp'
        os.environ['HF_HOME'] = '/tmp'
        try:
            self._model = SentenceTransformer(model_name, device='cpu')
            print(f"✓ Loaded sentence-transformer model: {model_name}")
        except Exception as e:
            print(f"⚠ Failed to load transformer model: {e}, falling back to TF-IDF")
            self._model = None

    @property
    def using_transformer(self) -> bool:
        return self._model is not None

    def embed(self, texts: list[str]) -> np.ndarray:
        if self._model is not None:
            return self._model.encode(texts, normalize_embeddings=True)

        return self._tfidf_embed(texts)

    def embed_single(self, text: str) -> np.ndarray:
        return self.embed([text])[0]

    def _tfidf_embed(self, texts: list[str]) -> np.ndarray:
        vectors = []
        for text in texts:
            tokens = self._tokenize(text)
            vec = np.zeros(384)
            for i, token in enumerate(tokens):
                idx = int(hashlib.md5(token.encode()).hexdigest(), 16) % 384
                vec[idx] += 1.0 / (i + 1)
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            vectors.append(vec)
        return np.array(vectors)

    def _tokenize(self, text: str) -> list[str]:
        return [
            w.lower().strip(".,;:!?\"'()[]{}")
            for w in text.split()
            if len(w) > 2
        ]

    def similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b))
