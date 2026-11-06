import json
import os
from typing import List, Dict, Any, Tuple
import numpy as np

class InMemoryVectorStore:
    """
    High-performance in-memory vector store with cosine similarity ranking.
    Supports persistence to JSON and provides fast exact nearest-neighbor search.
    Compatible with PostgreSQL pgvector migration.
    """

    def __init__(self):
        self.chunks: List[Dict[str, Any]] = []
        self.embeddings: List[List[float]] = []

    def clear(self):
        self.chunks = []
        self.embeddings = []

    def add_chunks(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]):
        if len(chunks) != len(embeddings):
            raise ValueError("Chunks count must match embeddings count")
        self.chunks.extend(chunks)
        self.embeddings.extend(embeddings)

    def similarity_search(
        self, 
        query_embedding: List[float], 
        top_k: int = 3, 
        score_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        if not self.embeddings:
            return []

        q_vec = np.array(query_embedding, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm == 0:
            return []
        q_vec = q_vec / q_norm

        matrix = np.array(self.embeddings, dtype=np.float32)
        # Normalize stored vectors
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normalized_matrix = matrix / norms

        # Dot product for cosine similarity
        scores = np.dot(normalized_matrix, q_vec)

        # Rank indices
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score >= score_threshold:
                chunk = dict(self.chunks[idx])
                chunk["similarity_score"] = round(score, 4)
                results.append(chunk)

        return results

    def save_to_file(self, file_path: str):
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        data = {
            "chunks": self.chunks,
            "embeddings": self.embeddings
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_from_file(self, file_path: str) -> bool:
        if not os.path.exists(file_path):
            return False
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.chunks = data.get("chunks", [])
            self.embeddings = data.get("embeddings", [])
        return True

