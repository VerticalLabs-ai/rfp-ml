"""
RAG (Retrieval-Augmented Generation) module for semantic search and context retrieval.

This module now uses ChromaDB for persistent vector storage.
"""
from .chroma_rag_engine import ChromaRAGEngine, get_rag_engine, reset_rag_engine

# Compatibility aliases
RAGEngine = ChromaRAGEngine
create_rag_engine = get_rag_engine


# Compatibility stubs for types no longer used by ChromaDB implementation
class RAGConfig:
    """Deprecated: ChromaDB handles configuration internally."""
    pass


class RAGContext:
    """Deprecated: Use retrieve() results directly."""
    def __init__(self, context_text="", retrieved_documents=None):
        self.context_text = context_text
        self.retrieved_documents = retrieved_documents or []


class RetrievalResult:
    """Deprecated: ChromaDB returns dicts directly."""
    def __init__(self, content="", metadata=None, similarity=0.0):
        self.content = content
        self.metadata = metadata or {}
        self.similarity = similarity


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
