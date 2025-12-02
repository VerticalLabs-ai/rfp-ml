"""
RAG (Retrieval-Augmented Generation) module for semantic search and context retrieval.

This module now uses ChromaDB for persistent vector storage.
"""

from .chroma_rag_engine import ChromaRAGEngine, get_rag_engine, reset_rag_engine
from .rag_engine import RAGConfig, RAGContext, RetrievalResult

# Compatibility aliases
RAGEngine = ChromaRAGEngine
create_rag_engine = get_rag_engine


__all__ = [
    "RAGEngine",
    "ChromaRAGEngine",
    "RAGConfig",
    "RAGContext",
    "RetrievalResult",
    "create_rag_engine",
    "get_rag_engine",
    "reset_rag_engine",
]
