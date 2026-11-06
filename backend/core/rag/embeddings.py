import os
import re
import math
import hashlib
from typing import List
import numpy as np

class EmbeddingProvider:
    """Base interface for embedding models."""
    def embed_query(self, text: str) -> List[float]:
        raise NotImplementedError

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError


class LocalSemanticEmbeddingProvider(EmbeddingProvider):
    """
    Lightweight, deterministic local semantic embedding generator.
    Produces 128-dimensional normalized dense vectors using sub-word n-gram hashing
    and domain-specific SRE vocabulary weighting.
    Works with 0 external network dependencies and 0 API cost.
    """
    DIMENSIONS = 128

    # High-signal SRE keywords given enhanced semantic weight
    SRE_KEYWORDS = {
        "oom": 0, "oomkilled": 0, "137": 1, "memory": 2, "leak": 3, "ram": 2,
        "postgres": 4, "postgresql": 4, "database": 5, "connection": 6, "pool": 7,
        "exhausted": 8, "starvation": 8, "timeout": 9, "500": 10, "504": 11,
        "cpu": 12, "throttling": 13, "cfs": 14, "quota": 14, "threads": 15,
        "restart": 16, "crash": 17, "pgbouncer": 18, "latency": 19, "redis": 20
    }

    def _text_to_vector(self, text: str) -> np.ndarray:
        vec = np.zeros(self.DIMENSIONS, dtype=np.float32)
        words = re.findall(r'\b[a-zA-Z0-9_\-]+\b', text.lower())
        if not words:
            return vec

        for word in words:
            # Check SRE keyword bonus
            if word in self.SRE_KEYWORDS:
                dim_idx = self.SRE_KEYWORDS[word] % self.DIMENSIONS
                vec[dim_idx] += 3.0

            # Hash n-grams for general semantic distribution
            h = int(hashlib.md5(word.encode("utf-8")).hexdigest()[:8], 16)
            idx = h % self.DIMENSIONS
            vec[idx] += 1.0

            # 3-char subgrams
            for i in range(len(word) - 2):
                sub = word[i:i+3]
                sub_h = int(hashlib.sha256(sub.encode("utf-8")).hexdigest()[:6], 16)
                vec[sub_h % self.DIMENSIONS] += 0.3

        # L2 normalize
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def embed_query(self, text: str) -> List[float]:
        return self._text_to_vector(text).tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._text_to_vector(t).tolist() for t in texts]


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI text-embedding-3-small provider."""
    def __init__(self, api_key: str = None, model: str = "text-embedding-3-small"):
        from openai import OpenAI
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key)
        self.model = model

    def embed_query(self, text: str) -> List[float]:
        response = self.client.embeddings.create(input=[text], model=self.model)
        return response.data[0].embedding

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        response = self.client.embeddings.create(input=texts, model=self.model)
        return [item.embedding for item in response.data]


def get_default_embedding_provider() -> EmbeddingProvider:
    """Factory to get the best available embedding provider."""
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and api_key.startswith("sk-") and len(api_key) > 20:
        try:
            return OpenAIEmbeddingProvider(api_key=api_key)
        except Exception:
            pass
    return LocalSemanticEmbeddingProvider()

