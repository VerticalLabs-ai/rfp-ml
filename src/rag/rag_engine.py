"""
RAG Engine Compatibility Shim.

This module redirects to the ChromaDB implementation for backward compatibility.
The FAISS implementation has been moved to rag_engine_faiss_deprecated.py.

For new code, use: from src.rag.chroma_rag_engine import get_rag_engine
"""

from src.rag.chroma_rag_engine import ChromaRAGEngine, get_rag_engine

# Compatibility alias
RAGEngine = ChromaRAGEngine


# Compatibility stubs for types no longer used by ChromaDB
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


def create_rag_engine() -> ChromaRAGEngine:
    """Deprecated: Use get_rag_engine() instead."""
    return get_rag_engine()


def search_rfps(query: str, top_k: int = 5) -> list:
    """Deprecated compatibility function."""
    engine = get_rag_engine()
    return engine.retrieve(query, top_k=top_k)


# Re-export for backward compatibility
__all__ = [
    "RAGEngine",
    "RAGConfig",
    "RAGContext",
    "RetrievalResult",
    "create_rag_engine",
    "get_rag_engine",
    "search_rfps",
]
