"""
RAG (Retrieval-Augmented Generation) Engine for Government RFP Bid Generation
This module implements a vector-based retrieval system that indexes processed RFP datasets
and provides semantic search capabilities for generating contextual bid responses.
"""
import json
import logging
import os
import pickle
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.config.paths import PathConfig
from src.config.settings import settings

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    print("Warning: FAISS not available. Install with: pip install faiss-cpu")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("Warning: Sentence Transformers not available. Install with: pip install sentence-transformers")

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("Warning: Scikit-learn not available. Install with: pip install scikit-learn")


@dataclass
class RAGConfig:
    """Configuration for RAG Engine"""
    # Paths - use PathConfig for environment-agnostic paths
    data_dir: str = field(default_factory=lambda: str(PathConfig.PROCESSED_DATA_DIR))
    embeddings_dir: str = field(default_factory=lambda: str(PathConfig.EMBEDDINGS_DIR))
    # Model settings
    embedding_model: str = field(default_factory=lambda: settings.rag.embedding_model)
    # Text processing
    chunk_size: int = field(default_factory=lambda: settings.rag.chunk_size)
    chunk_overlap: int = field(default_factory=lambda: settings.rag.chunk_overlap)
    max_text_length: int = field(default_factory=lambda: settings.rag.max_text_length)
    # Retrieval settings
    top_k: int = field(default_factory=lambda: settings.rag.top_k)
    similarity_threshold: float = field(default_factory=lambda: settings.rag.similarity_threshold)
    # FAISS settings
    use_gpu: bool = field(default_factory=lambda: settings.rag.use_gpu)
    index_type: str = field(default_factory=lambda: settings.rag.index_type)
    # Fallback settings
    use_tfidf_fallback: bool = field(default_factory=lambda: settings.rag.use_tfidf_fallback)


@dataclass
class RetrievalResult:
    """Result from document retrieval"""
    document_id: str
    content: str
    metadata: Dict[str, Any]
    similarity_score: float
    source_dataset: str


@dataclass
class RAGContext:
    """Context for RAG-enhanced generation"""
    query: str
    retrieved_documents: List[RetrievalResult]
    total_retrieved: int
    retrieval_method: str
    context_text: str


class DocumentProcessor:
    """Handles document preprocessing and chunking"""
    def __init__(self, config: RAGConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def preprocess_text(self, text: str) -> str:
        """Preprocess text for embedding"""
        if not isinstance(text, str):
            return ""
        # Basic cleaning
        text = text.strip()
        text = text.replace('\n', ' ').replace('\r', ' ')
        text = ' '.join(text.split())  # normalize whitespace
        # Truncate if too long
        if len(text) > self.config.max_text_length:
            text = text[:self.config.max_text_length] + "..."
        return text

    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks for embedding"""
        if not text:
            return []
        # Simple word-based chunking
        words = text.split()
        chunks = []
        for i in range(0, len(words), self.config.chunk_size - self.config.chunk_overlap):
            chunk_words = words[i:i + self.config.chunk_size]
            chunk_text = ' '.join(chunk_words)
            if chunk_text.strip():
                chunks.append(chunk_text.strip())
        return chunks if chunks else [text]

    def extract_text_fields(self, row: pd.Series) -> str:
        """Extract and combine relevant text fields from a dataset row"""
        text_parts = []
        # Common RFP text fields to extract
        text_fields = [
            'description', 'title', 'notice_type', 'solicitation_number',
            'agency', 'office', 'location', 'classification_code',
            'naics_code', 'set_aside', 'pop_address', 'pop_country',
            'pop_state', 'pop_zip', 'primary_poc', 'primary_poc_email',
            'secondary_poc', 'secondary_poc_email', 'office_address',
            'subject', 'award_description', 'award_amount'
        ]
        for field in text_fields:
            if field in row and pd.notna(row[field]):
                value = str(row[field]).strip()
                if value and value.lower() not in ['nan', 'none', '']:
                    text_parts.append(f"{field}: {value}")
        combined_text = ' | '.join(text_parts)
        return self.preprocess_text(combined_text)


class EmbeddingEngine:
    """Handles text embeddings using Sentence Transformers"""
    def __init__(self, config: RAGConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.model = None
        self.model_available = False
        self._initialize_model()

    def _initialize_model(self):
        """Initialize the embedding model"""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            self.logger.warning("Sentence Transformers not available")
            return
        try:
            self.model = SentenceTransformer(self.config.embedding_model)
            self.model_available = True
            self.logger.info(f"Embedding model {self.config.embedding_model} loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load embedding model: {str(e)}")
            self.model_available = False

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts"""
        if not self.model_available:
            raise RuntimeError("Embedding model not available")
        if not texts:
            return np.array([])
        try:
            embeddings = self.model.encode(texts, show_progress_bar=True)
            return embeddings
        except Exception as e:
            self.logger.error(f"Embedding generation failed: {str(e)}")
            raise

    def embed_single_text(self, text: str) -> np.ndarray:
        """Generate embedding for a single text"""
        return self.embed_texts([text])[0]


class VectorIndex:
    """Handles vector indexing and similarity search using FAISS"""
    def __init__(self, config: RAGConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.index = None
        self.document_ids = []
        self.metadata = []
        self.embedding_dim = None
        # Create embeddings directory
        os.makedirs(self.config.embeddings_dir, exist_ok=True)

    def build_index(self, embeddings: np.ndarray, document_ids: List[str], metadata: List[Dict]):
        """Build FAISS index from embeddings"""
        if not FAISS_AVAILABLE:
            raise RuntimeError("FAISS not available")
        if len(embeddings) == 0:
            raise ValueError("No embeddings provided")
        self.embedding_dim = embeddings.shape[1]
        self.document_ids = document_ids.copy()
        self.metadata = metadata.copy()
        # Create FAISS index
        if self.config.index_type == "flat":
            self.index = faiss.IndexFlatIP(self.embedding_dim)  # Inner product (cosine similarity)
        else:
            # For larger datasets, use IVF index
            nlist = min(100, len(embeddings) // 10)  # number of clusters
            self.index = faiss.IndexIVFFlat(
                faiss.IndexFlatIP(self.embedding_dim),
                self.embedding_dim,
                nlist
            )
        # Normalize embeddings for cosine similarity
        embeddings_normalized = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        # Train and add vectors
        if hasattr(self.index, 'train'):
            self.index.train(embeddings_normalized)
        self.index.add(embeddings_normalized)
        self.logger.info(f"Built FAISS index with {len(embeddings)} vectors")

    def search(self, query_embedding: np.ndarray, k: int = None) -> Tuple[List[float], List[int]]:
        """Search for similar vectors"""
        if self.index is None:
            raise RuntimeError("Index not built")
        k = k or self.config.top_k
        k = min(k, self.index.ntotal)  # Don't search for more than available
        # Normalize query embedding
        query_embedding = query_embedding / np.linalg.norm(query_embedding)
        query_embedding = query_embedding.reshape(1, -1)
        # Search
        scores, indices = self.index.search(query_embedding, k)
        return scores[0].tolist(), indices[0].tolist()

    def save_index(self, filepath: str):
        """Save index and metadata to disk"""
        if self.index is None:
            raise RuntimeError("No index to save")
        # Save FAISS index
        faiss.write_index(self.index, f"{filepath}.faiss")
        # Save metadata
        metadata_dict = {
            "document_ids": self.document_ids,
            "metadata": self.metadata,
            "embedding_dim": self.embedding_dim,
            "config": {
                "embedding_model": self.config.embedding_model,
                "chunk_size": self.config.chunk_size,
                "index_type": self.config.index_type
            }
        }
        with open(f"{filepath}_metadata.json", 'w') as f:
            json.dump(metadata_dict, f, indent=2)
        self.logger.info(f"Index saved to {filepath}")

    def load_index(self, filepath: str):
        """Load index and metadata from disk"""
        if not FAISS_AVAILABLE:
            raise RuntimeError("FAISS not available")
        # Load FAISS index
        self.index = faiss.read_index(f"{filepath}.faiss")
        # Load metadata
        with open(f"{filepath}_metadata.json", 'r') as f:
            metadata_dict = json.load(f)
        self.document_ids = metadata_dict["document_ids"]
        self.metadata = metadata_dict["metadata"]
        self.embedding_dim = metadata_dict["embedding_dim"]
        self.logger.info(f"Index loaded from {filepath}")


class TFIDFRetriever:
    """Fallback retriever using TF-IDF similarity"""
    def __init__(self, config: RAGConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.vectorizer = None
        self.tfidf_matrix = None
        self.documents = []
        self.document_ids = []
        self.metadata = []

    def build_index(self, documents: List[str], document_ids: List[str], metadata: List[Dict]):
        """Build TF-IDF index"""
        if not SKLEARN_AVAILABLE:
            raise RuntimeError("Scikit-learn not available")
        self.documents = documents.copy()
        self.document_ids = document_ids.copy()
        self.metadata = metadata.copy()
        # Build TF-IDF matrix
        self.vectorizer = TfidfVectorizer(
            max_features=10000,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.95
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(documents)
        self.logger.info(f"Built TF-IDF index with {len(documents)} documents")

    def search(self, query: str, k: int = None) -> Tuple[List[float], List[int]]:
        """Search for similar documents using TF-IDF"""
        if self.vectorizer is None or self.tfidf_matrix is None:
            raise RuntimeError("TF-IDF index not built")
        k = k or self.config.top_k
        # Transform query
        query_vector = self.vectorizer.transform([query])
        # Calculate similarities
        similarities = cosine_similarity(query_vector, self.tfidf_matrix)[0]
        # Get top k
        top_indices = np.argsort(similarities)[::-1][:k]
        top_scores = similarities[top_indices]
        return top_scores.tolist(), top_indices.tolist()


class RAGEngine:
    """Main RAG Engine that orchestrates retrieval and context generation"""
    def __init__(self, config: Optional[RAGConfig] = None):
        self.config = config or RAGConfig()
        self.logger = logging.getLogger(__name__)
        # Initialize components
        self.doc_processor = DocumentProcessor(self.config)
        self.embedding_engine = EmbeddingEngine(self.config)
        self.vector_index = VectorIndex(self.config)
        self.tfidf_retriever = TFIDFRetriever(self.config) if self.config.use_tfidf_fallback else None
        # Data storage
        self.documents = []
        self.document_ids = []
        self.document_metadata = []
        self.is_built = False

    def load_datasets(self) -> Dict[str, pd.DataFrame]:
        """Load all processed RFP datasets"""
        datasets = {}
        data_dir = Path(self.config.data_dir)
        if not data_dir.exists():
            raise FileNotFoundError(f"Data directory not found: {data_dir}")
        # Load parquet files
        for file_path in data_dir.glob("*.parquet"):
            dataset_name = file_path.stem
            try:
                df = pd.read_parquet(file_path)
                datasets[dataset_name] = df
                self.logger.info(f"Loaded {dataset_name}: {df.shape[0]} records")
            except Exception as e:
                self.logger.error(f"Failed to load {file_path}: {str(e)}")
        return datasets

    def build_index(self, force_rebuild: bool = False):
        """Build the RAG index from processed datasets"""
        index_path = os.path.join(self.config.embeddings_dir, "rag_index")
        # Check if index already exists
        if not force_rebuild and os.path.exists(f"{index_path}.faiss"):
            try:
                self.vector_index.load_index(index_path)
                if self.tfidf_retriever and os.path.exists(f"{index_path}_tfidf.pkl"):
                    with open(f"{index_path}_tfidf.pkl", 'rb') as f:
                        tfidf_data = pickle.load(f)
                        self.tfidf_retriever.documents = tfidf_data['documents']
                        self.tfidf_retriever.document_ids = tfidf_data['document_ids']
                        self.tfidf_retriever.metadata = tfidf_data['metadata']
                        self.tfidf_retriever.vectorizer = tfidf_data['vectorizer']
                        self.tfidf_retriever.tfidf_matrix = tfidf_data['tfidf_matrix']
                self.is_built = True
                self.logger.info("Loaded existing RAG index")
                return
            except Exception as e:
                self.logger.warning(f"Failed to load existing index: {str(e)}, rebuilding...")
        # Load datasets
        datasets = self.load_datasets()
        if not datasets:
            raise RuntimeError("No datasets found to build index")
        # Process documents
        all_documents = []
        all_document_ids = []
        all_metadata = []
        for dataset_name, df in datasets.items():
            self.logger.info(f"Processing {dataset_name}...")
            for idx, row in df.iterrows():
                # Extract text
                text = self.doc_processor.extract_text_fields(row)
                if not text:
                    continue
                # Create chunks
                chunks = self.doc_processor.chunk_text(text)
                for chunk_idx, chunk in enumerate(chunks):
                    doc_id = f"{dataset_name}_{idx}_{chunk_idx}"
                    metadata = {
                        "source_dataset": dataset_name,
                        "original_index": idx,
                        "chunk_index": chunk_idx,
                        "total_chunks": len(chunks),
                        **{k: v for k, v in row.to_dict().items() if pd.notna(v)}
                    }
                    all_documents.append(chunk)
                    all_document_ids.append(doc_id)
                    all_metadata.append(metadata)
        if not all_documents:
            raise RuntimeError("No documents extracted from datasets")
        self.logger.info(f"Extracted {len(all_documents)} document chunks")
        # Build embeddings if possible
        if self.embedding_engine.model_available:
            try:
                self.logger.info("Generating embeddings...")
                embeddings = self.embedding_engine.embed_texts(all_documents)
                # Build FAISS index
                self.vector_index.build_index(embeddings, all_document_ids, all_metadata)
                # Save index
                self.vector_index.save_index(index_path)
                self.logger.info("Vector index built successfully")
            except Exception as e:
                self.logger.error(f"Failed to build vector index: {str(e)}")
                if not self.config.use_tfidf_fallback:
                    raise
        # Build TF-IDF fallback
        if self.tfidf_retriever:
            try:
                self.logger.info("Building TF-IDF fallback index...")
                self.tfidf_retriever.build_index(all_documents, all_document_ids, all_metadata)
                # Save TF-IDF index
                tfidf_data = {
                    'documents': self.tfidf_retriever.documents,
                    'document_ids': self.tfidf_retriever.document_ids,
                    'metadata': self.tfidf_retriever.metadata,
                    'vectorizer': self.tfidf_retriever.vectorizer,
                    'tfidf_matrix': self.tfidf_retriever.tfidf_matrix
                }
                with open(f"{index_path}_tfidf.pkl", 'wb') as f:
                    pickle.dump(tfidf_data, f)
                self.logger.info("TF-IDF index built successfully")
            except Exception as e:
                self.logger.error(f"Failed to build TF-IDF index: {str(e)}")
        self.is_built = True
        self.logger.info("RAG index building complete")

    def retrieve(self, query: str, k: int = None, use_embeddings: bool = True) -> List[RetrievalResult]:
        """Retrieve relevant documents for a query"""
        if not self.is_built:
            raise RuntimeError("RAG index not built. Call build_index() first.")
        k = k or self.config.top_k
        results = []
        # Try embedding-based retrieval first
        if use_embeddings and self.embedding_engine.model_available and self.vector_index.index is not None:
            try:
                query_embedding = self.embedding_engine.embed_single_text(query)
                scores, indices = self.vector_index.search(query_embedding, k)
                for score, idx in zip(scores, indices):
                    if score >= self.config.similarity_threshold:
                        result = RetrievalResult(
                            document_id=self.vector_index.document_ids[idx],
                            content=self.vector_index.metadata[idx].get('text', ''),
                            metadata=self.vector_index.metadata[idx],
                            similarity_score=float(score),
                            source_dataset=self.vector_index.metadata[idx].get('source_dataset', 'unknown')
                        )
                        results.append(result)
                if results:
                    self.logger.info(f"Retrieved {len(results)} documents using embeddings")
                    return results
            except Exception as e:
                self.logger.warning(f"Embedding retrieval failed: {str(e)}, falling back to TF-IDF")
        # Fallback to TF-IDF
        if self.tfidf_retriever and self.tfidf_retriever.vectorizer is not None:
            try:
                scores, indices = self.tfidf_retriever.search(query, k)
                for score, idx in zip(scores, indices):
                    if score >= self.config.similarity_threshold:
                        result = RetrievalResult(
                            document_id=self.tfidf_retriever.document_ids[idx],
                            content=self.tfidf_retriever.documents[idx],
                            metadata=self.tfidf_retriever.metadata[idx],
                            similarity_score=float(score),
                            source_dataset=self.tfidf_retriever.metadata[idx].get('source_dataset', 'unknown')
                        )
                        results.append(result)
                self.logger.info(f"Retrieved {len(results)} documents using TF-IDF")
                return results
            except Exception as e:
                self.logger.error(f"TF-IDF retrieval failed: {str(e)}")
        self.logger.warning("No retrieval method succeeded")
        return results

    def generate_context(self, query: str, k: int = None) -> RAGContext:
        """Generate RAG context for a query"""
        retrieved_docs = self.retrieve(query, k)
        # Create context text
        context_parts = []
        for doc in retrieved_docs:
            context_parts.append(f"Document {doc.document_id} (score: {doc.similarity_score:.3f}):\n{doc.content}")
        context_text = "\n\n".join(context_parts)
        return RAGContext(
            query=query,
            retrieved_documents=retrieved_docs,
            total_retrieved=len(retrieved_docs),
            retrieval_method="embeddings" if self.embedding_engine.model_available else "tfidf",
            context_text=context_text
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get RAG engine statistics"""
        stats = {
            "is_built": self.is_built,
            "embedding_model": self.config.embedding_model,
            "embedding_available": self.embedding_engine.model_available,
            "vector_index_built": self.vector_index.index is not None,
            "tfidf_available": self.tfidf_retriever is not None,
            "total_documents": len(self.vector_index.document_ids) if self.vector_index.document_ids else 0,
            "embedding_dimension": self.vector_index.embedding_dim,
            "config": {
                "chunk_size": self.config.chunk_size,
                "top_k": self.config.top_k,
                "similarity_threshold": self.config.similarity_threshold
            }
        }
        return stats


def create_rag_engine(config_overrides: Optional[Dict[str, Any]] = None) -> RAGEngine:
    """Factory function to create RAG engine with optional configuration overrides"""
    config = RAGConfig()
    if config_overrides:
        for key, value in config_overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)
    return RAGEngine(config)


if __name__ == "__main__":
    print("=== RAG Engine Test ===")
    try:
        # Create RAG engine
        rag_engine = create_rag_engine()
        print("✓ RAG Engine created")
        # Build index
        print("Building RAG index...")
        rag_engine.build_index()
        print("✓ RAG index built")
        # Test retrieval
        query = "bottled water delivery contract"
        context = rag_engine.generate_context(query)
        print(f"✓ Retrieved {context.total_retrieved} documents for query: '{query}'")
        # Show statistics
        stats = rag_engine.get_statistics()
        print(f"✓ Statistics: {stats}")
        print("✅ RAG Engine test completed successfully!")
    except Exception as e:
        print(f"❌ RAG Engine test failed: {str(e)}")
        import traceback
        traceback.print_exc()
