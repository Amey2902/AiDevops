"""
DevOpsAI RAG Knowledge Base Subsystem
Handles document chunking, embeddings, vector indexing, and semantic retrieval for SRE runbooks.
"""

from .knowledge_manager import KnowledgeManager, get_knowledge_manager

__all__ = ["KnowledgeManager", "get_knowledge_manager"]
