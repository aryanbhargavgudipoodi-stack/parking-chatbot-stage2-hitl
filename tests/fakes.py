"""Reusable fake dependencies for offline tests."""

from __future__ import annotations

from typing import List

from langchain_core.embeddings import Embeddings


class DeterministicFakeEmbeddings(Embeddings):
    """Simple deterministic embedding generator for tests.

    The implementation is intentionally tiny and stable so that vector-store
    tests can run offline without any network calls.
    """

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_one(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed_one(text)

    def _embed_one(self, text: str) -> List[float]:
        tokens = text.lower().replace("-", " ").split()
        if not tokens:
            return [0.0] * 8

        vector = []
        for i in range(8):
            total = 0.0
            for token in tokens:
                total += (ord(token[0]) if token else 0) + (len(token) * (i + 1))
            vector.append(round(total / max(len(tokens), 1), 6))
        return vector
