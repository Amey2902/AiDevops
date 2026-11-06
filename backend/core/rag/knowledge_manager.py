import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from .chunker import MarkdownChunker
from .embeddings import get_default_embedding_provider, EmbeddingProvider
from .vector_store import InMemoryVectorStore

class KnowledgeManager:
    """
    Coordinates runbook ingestion, embedding generation, vector indexing,
    and semantic retrieval for DevOpsAI.
    """

    def __init__(self, knowledge_base_dir: Optional[Path] = None, embedding_provider: Optional[EmbeddingProvider] = None):
        if knowledge_base_dir is None:
            # Look up knowledge_base directory relative to backend
            base = Path(__file__).resolve().parent.parent.parent.parent
            self.knowledge_base_dir = base / "knowledge_base"
        else:
            self.knowledge_base_dir = Path(knowledge_base_dir)

        self.embedding_provider = embedding_provider or get_default_embedding_provider()
        self.chunker = MarkdownChunker()
        self.vector_store = InMemoryVectorStore()
        self.indexed_files: List[str] = []
        self._is_indexed = False

    def ingest_all(self, force_reload: bool = False) -> int:
        """Scan knowledge_base directory and index all markdown documents."""
        if self._is_indexed and not force_reload:
            return len(self.vector_store.chunks)

        self.vector_store.clear()
        self.indexed_files = []

        if not self.knowledge_base_dir.exists():
            return 0

        all_chunks = []
        md_files = list(self.knowledge_base_dir.glob("**/*.md"))

        for file_path in md_files:
            try:
                content = file_path.read_text(encoding="utf-8")
                category = file_path.parent.name
                metadata = {
                    "source_path": str(file_path),
                    "filename": file_path.name,
                    "category": category,
                    "title": file_path.stem.replace("_", " ").title()
                }
                chunks = self.chunker.chunk_markdown(content, metadata=metadata)
                all_chunks.extend(chunks)
                self.indexed_files.append(str(file_path))
            except Exception as e:
                print(f"[KnowledgeManager] Error loading {file_path}: {e}")

        if all_chunks:
            texts = [c["content"] for c in all_chunks]
            embeddings = self.embedding_provider.embed_documents(texts)
            self.vector_store.add_chunks(all_chunks, embeddings)

        self._is_indexed = True
        return len(all_chunks)

    def query(self, query_text: str, top_k: int = 3, score_threshold: float = 0.0) -> List[Dict[str, Any]]:
        """Perform semantic search against indexed runbooks and incident docs."""
        if not self._is_indexed:
            self.ingest_all()

        q_vec = self.embedding_provider.embed_query(query_text)
        return self.vector_store.similarity_search(q_vec, top_k=top_k, score_threshold=score_threshold)

    def get_stats(self) -> Dict[str, Any]:
        """Return knowledge base status and indexed documents count."""
        return {
            "is_indexed": self._is_indexed,
            "total_chunks": len(self.vector_store.chunks),
            "indexed_files_count": len(self.indexed_files),
            "indexed_files": self.indexed_files,
            "embedding_provider": self.embedding_provider.__class__.__name__
        }


# Singleton instance
_GLOBAL_KNOWLEDGE_MANAGER: Optional[KnowledgeManager] = None

def get_knowledge_manager() -> KnowledgeManager:
    global _GLOBAL_KNOWLEDGE_MANAGER
    if _GLOBAL_KNOWLEDGE_MANAGER is None:
        _GLOBAL_KNOWLEDGE_MANAGER = KnowledgeManager()
        _GLOBAL_KNOWLEDGE_MANAGER.ingest_all()
    return _GLOBAL_KNOWLEDGE_MANAGER
