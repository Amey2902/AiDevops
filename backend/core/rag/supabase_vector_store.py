import os
import requests
from typing import List, Dict, Any, Optional

class SupabaseVectorStore:
    """
    Cloud Vector Database adapter for Supabase pgvector.
    Provides semantic vector search, chunk synchronization, and runbook matching.
    """

    def __init__(self, supabase_url: Optional[str] = None, supabase_key: Optional[str] = None):
        self.url = (supabase_url or os.getenv("SUPABASE_URL", "")).rstrip("/")
        self.key = supabase_key or os.getenv("SUPABASE_KEY", "")
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

    def is_configured(self) -> bool:
        return bool(self.url and self.key and len(self.key) > 10)

    def upload_chunks(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]) -> int:
        """Upload vectorized runbook chunks into Supabase runbook_embeddings table."""
        if not self.is_configured():
            return 0

        endpoint = f"{self.url}/rest/v1/runbook_embeddings"
        records = []
        for chunk, emb in zip(chunks, embeddings):
            records.append({
                "title": chunk.get("title", ""),
                "content": chunk.get("content", ""),
                "source_file": chunk.get("metadata", {}).get("filename", ""),
                "category": chunk.get("metadata", {}).get("category", ""),
                "embedding": emb
            })

        try:
            resp = requests.post(endpoint, headers=self.headers, json=records, timeout=10)
            if resp.status_code in [200, 201]:
                return len(records)
            else:
                print(f"[SupabaseVectorStore] Upload failed: {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"[SupabaseVectorStore] Error uploading to Supabase: {e}")

        return 0

    def semantic_search(self, query_embedding: List[float], top_k: int = 3) -> List[Dict[str, Any]]:
        """Call Supabase RPC match_runbooks function for cosine similarity search."""
        if not self.is_configured():
            return []

        rpc_endpoint = f"{self.url}/rest/v1/rpc/match_runbooks"
        payload = {
            "query_embedding": query_embedding,
            "match_threshold": 0.0,
            "match_count": top_k
        }

        try:
            resp = requests.post(rpc_endpoint, headers=self.headers, json=payload, timeout=8)
            if resp.status_code == 200:
                results = resp.json()
                formatted = []
                for r in results:
                    formatted.append({
                        "title": r.get("title"),
                        "content": r.get("content"),
                        "similarity_score": round(float(r.get("similarity", 0.0)), 4),
                        "metadata": {
                            "filename": r.get("source_file"),
                            "category": r.get("category")
                        }
                    })
                return formatted
            else:
                print(f"[SupabaseVectorStore] RPC search failed: {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"[SupabaseVectorStore] Error querying Supabase RPC: {e}")

        return []
