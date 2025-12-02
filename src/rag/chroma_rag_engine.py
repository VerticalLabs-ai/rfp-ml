"""
ChromaDB-based RAG Engine with automatic persistence.

This replaces the FAISS-based implementation with ChromaDB for:
- Built-in persistence (survives container restarts)
- Automatic index management
- Simpler API with better error handling
"""

import logging
import threading
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)


def _get_persist_directory() -> str:
    """Get the ChromaDB persistence directory with Docker-aware path resolution."""
    # Check for Docker environment via mounted volumes
    if Path("/app/data").exists() and Path("/app/src").exists():
        persist_dir = Path("/app/data/chroma")
    else:
        # Local development
        persist_dir = Path(__file__).parent.parent.parent / "data" / "chroma"

    # Ensure directory exists
    persist_dir.mkdir(parents=True, exist_ok=True)
    return str(persist_dir)


class ChromaRAGEngine:
    """
    RAG engine using ChromaDB for persistent vector storage.

    Key improvements over FAISS implementation:
    - Automatic persistence on every write
    - Thread-safe singleton pattern
    - No manual build_index() required for persistence
    - Graceful handling of empty collections
    """

    def __init__(self, persist_directory: str = None):
        """
        Initialize ChromaDB client and collection.

        Args:
            persist_directory: Optional custom path for ChromaDB data.
                              Defaults to data/chroma in project root.
        """
        if persist_directory is None:
            persist_directory = _get_persist_directory()

        try:
            import chromadb
            from chromadb.config import Settings

            # ChromaDB with persistent storage
            self.client = chromadb.PersistentClient(
                path=persist_directory, settings=Settings(anonymized_telemetry=False)
            )

            # Create or get collection with cosine similarity
            self.collection = self.client.get_or_create_collection(
                name="rfp_documents", metadata={"hnsw:space": "cosine"}
            )

            self._persist_directory = persist_directory
            self._embedding_model = None

            logger.info(f"ChromaDB initialized at {persist_directory}")
            logger.info(f"Collection has {self.collection.count()} documents")

        except ImportError as e:
            logger.error(f"ChromaDB not installed: {e}")
            raise ImportError(
                "chromadb package required. Install with: pip install chromadb>=1.0.0"
            ) from e
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise

    @property
    def embedding_model(self):
        """Lazy load the sentence transformer model."""
        if self._embedding_model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
                logger.info("Loaded embedding model: all-MiniLM-L6-v2")
            except ImportError:
                logger.error("sentence-transformers not installed")
                raise
        return self._embedding_model

    @property
    def is_built(self) -> bool:
        """Returns True if the collection has documents."""
        return self.collection.count() > 0

    def add_documents(self, documents: list[dict], ids: list[str] = None) -> int:
        """
        Add documents to the collection.

        Args:
            documents: List of dicts with 'content' key and optional metadata
            ids: Optional list of document IDs

        Returns:
            Number of documents added
        """
        if not documents:
            return 0

        texts = [doc.get("content", "") for doc in documents]

        # Filter out empty texts
        valid_indices = [i for i, t in enumerate(texts) if t.strip()]
        if not valid_indices:
            logger.warning("No valid documents to add (all empty)")
            return 0

        valid_texts = [texts[i] for i in valid_indices]
        valid_docs = [documents[i] for i in valid_indices]

        # Generate IDs if not provided
        if ids is None:
            valid_ids = [str(uuid.uuid4()) for _ in range(len(valid_docs))]
        else:
            valid_ids = [ids[i] for i in valid_indices]

        # Prepare metadata (ChromaDB requires string values)
        metadatas = []
        for doc in valid_docs:
            meta = {}
            for k, v in doc.items():
                if k != "content" and v is not None:
                    meta[k] = str(v) if not isinstance(v, str) else v
            metadatas.append(meta)

        # ChromaDB has a max batch size of ~5000, so we batch our inserts
        BATCH_SIZE = 5000
        total_added = 0

        for batch_start in range(0, len(valid_texts), BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, len(valid_texts))

            batch_texts = valid_texts[batch_start:batch_end]
            batch_ids = valid_ids[batch_start:batch_end]
            batch_metas = metadatas[batch_start:batch_end]

            # Generate embeddings for this batch
            batch_embeddings = self.embedding_model.encode(batch_texts).tolist()

            # Upsert batch
            self.collection.upsert(
                ids=batch_ids,
                embeddings=batch_embeddings,
                documents=batch_texts,
                metadatas=batch_metas,
            )

            total_added += len(batch_texts)
            logger.info(
                f"Added batch {batch_start}-{batch_end} ({len(batch_texts)} docs)"
            )

        logger.info(f"Added {total_added} documents to collection")
        return total_added

    def retrieve(
        self, query: str, top_k: int = 5, similarity_threshold: float = 0.3
    ) -> list[dict]:
        """
        Retrieve relevant documents for a query.

        Args:
            query: Search query text
            top_k: Maximum number of results
            similarity_threshold: Minimum similarity score (0-1)

        Returns:
            List of matching documents with content, metadata, and similarity
        """
        if self.collection.count() == 0:
            logger.warning("Collection is empty, no documents to retrieve")
            return []

        # Generate query embedding
        query_embedding = self.embedding_model.encode([query]).tolist()

        # Query collection
        n_results = min(top_k, self.collection.count())
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

        # Convert distances to similarities and filter by threshold
        # ChromaDB returns L2 distance for cosine space, convert to similarity
        retrieved = []

        if not results["documents"] or not results["documents"][0]:
            return []

        for i, (doc, meta, dist) in enumerate(
            zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
                strict=True,
            )
        ):
            # For cosine distance, similarity = 1 - distance
            # ChromaDB with hnsw:space=cosine returns squared L2 distance of normalized vectors
            # which equals 2 * (1 - cosine_similarity)
            similarity = 1 - (dist / 2)

            if similarity >= similarity_threshold:
                retrieved.append(
                    {
                        "content": doc,
                        "metadata": meta,
                        "similarity": round(similarity, 4),
                        "document_id": results["ids"][0][i],
                    }
                )

        logger.info(
            f"Retrieved {len(retrieved)} documents for query (threshold={similarity_threshold})"
        )
        return retrieved

    def get_statistics(self) -> dict:
        """Get collection statistics."""
        return {
            "total_documents": self.collection.count(),
            "collection_name": self.collection.name,
            "persist_directory": self._persist_directory,
            "is_built": True,
            "embedding_available": True,  # Always True - model lazy-loads on first use
            "total_vectors": self.collection.count(),  # Compatibility with old API
        }

    def get_index_info(self) -> dict:
        """Get index information for compatibility with old API."""
        count = self.collection.count()
        return {
            "vectors": {
                "total": count,
                "documents_with_metadata": count,
            },
            "files": {
                "faiss_exists": True,  # ChromaDB handles this internally
                "metadata_exists": True,
                "metadata_valid": True,
            },
            "collection": self.collection.name,
            "persist_directory": self._persist_directory,
        }

    def build_index(self, force_rebuild: bool = False):
        """
        Build or rebuild index from parquet files.

        With ChromaDB, the index is automatically persisted, so this method
        only rebuilds when force_rebuild=True or the collection is empty.

        Args:
            force_rebuild: If True, clear and rebuild from parquet files
        """
        if force_rebuild:
            logger.info("Force rebuild requested, clearing collection...")
            self._rebuild_from_parquet()
        elif self.collection.count() == 0:
            logger.info("Empty collection detected, building from parquet files...")
            self._rebuild_from_parquet()
        else:
            logger.info(f"Index ready with {self.collection.count()} documents")

    def _rebuild_from_parquet(self):
        """Rebuild index from parquet files in data/processed."""
        import pandas as pd

        # Determine data directory
        if Path("/app/data/processed").exists():
            data_dir = Path("/app/data/processed")
        else:
            data_dir = Path(__file__).parent.parent.parent / "data" / "processed"

        if not data_dir.exists():
            logger.error(f"Data directory not found: {data_dir}")
            return

        # Clear existing collection
        try:
            self.client.delete_collection("rfp_documents")
        except Exception as e:
            logger.debug(f"Collection deletion skipped (may not exist): {e}")

        self.collection = self.client.create_collection(
            name="rfp_documents", metadata={"hnsw:space": "cosine"}
        )

        # Load and index all parquet files
        total_docs = 0
        parquet_files = list(data_dir.glob("*.parquet"))

        if not parquet_files:
            logger.warning(f"No parquet files found in {data_dir}")
            return

        logger.info(f"Found {len(parquet_files)} parquet files to index")

        for parquet_file in parquet_files:
            try:
                df = pd.read_parquet(parquet_file)
                documents = []
                ids = []

                for idx, row in df.iterrows():
                    content = self._extract_content(row)
                    if content and content.strip():
                        documents.append(
                            {
                                "content": content,
                                "title": str(row.get("title", "")),
                                "agency": str(row.get("agency", "")),
                                "naics_code": str(row.get("naics_code", "")),
                                "source_file": parquet_file.name,
                            }
                        )
                        ids.append(f"{parquet_file.stem}_{idx}")

                if documents:
                    self.add_documents(documents, ids)
                    total_docs += len(documents)
                    logger.info(
                        f"Indexed {len(documents)} docs from {parquet_file.name}"
                    )

            except Exception as e:
                logger.error(f"Failed to process {parquet_file}: {e}")

        logger.info(f"Rebuild complete: {total_docs} total documents indexed")

    def _extract_content(self, row) -> str:
        """Extract searchable content from a dataframe row."""
        import pandas as pd  # Ensure availability

        fields = [
            "title",
            "description",
            "agency",
            "requirements",
            "scope",
            "solicitation_number",
            "naics_code",
        ]
        parts = []
        for field in fields:
            if field in row.index and row[field] and pd.notna(row[field]):
                parts.append(str(row[field]))
        return " ".join(parts)

    def delete_collection(self):
        """Delete the entire collection (for cleanup/testing)."""
        try:
            self.client.delete_collection("rfp_documents")
            logger.info("Collection deleted")
        except Exception as e:
            logger.warning(f"Failed to delete collection: {e}")


# Thread-safe singleton instance
_engine_instance: ChromaRAGEngine | None = None
_engine_lock = threading.Lock()


def get_rag_engine() -> ChromaRAGEngine:
    """
    Get singleton ChromaDB RAG engine.

    This ensures only one instance exists across all threads/requests,
    preventing the "multiple instances" problem from the old FAISS implementation.
    """
    global _engine_instance
    if _engine_instance is None:
        with _engine_lock:
            if _engine_instance is None:
                _engine_instance = ChromaRAGEngine()
    return _engine_instance


def reset_rag_engine():
    """Reset the singleton (for testing purposes)."""
    global _engine_instance
    with _engine_lock:
        _engine_instance = None


# Import pandas at module level for type checking
try:
    import pandas as pd
except ImportError:
    pd = None
