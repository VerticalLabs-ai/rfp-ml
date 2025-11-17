"""
Working RAG Engine Implementation for Government RFP Bid Generation
Uses existing FAISS index and embeddings for semantic search
"""
import os
import sys
import logging
import pickle
import json
import time
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd

# Core ML libraries
import faiss
from sentence_transformers import SentenceTransformer

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config.paths import PathConfig
class WorkingRAGEngine:
    """
    Working RAG Engine that uses existing FAISS index and embeddings
    for semantic search across RFP datasets
    """
    def __init__(self, embeddings_dir: str | None = None):
        self.embeddings_dir = embeddings_dir or str(PathConfig.EMBEDDINGS_DIR)
        self.index = None
        self.metadata = []
        self.embedding_model = None
        self.is_loaded = False
        self.logger = self._setup_logger()
        self.logger.info("Working RAG Engine initialized")
    def _setup_logger(self) -> logging.Logger:
        """Setup logging"""
        logger = logging.getLogger('working_rag_engine')
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger
    def load_index(self) -> Dict[str, Any]:
        """Load existing FAISS index and metadata"""
        try:
            # Load FAISS index
            index_path = os.path.join(self.embeddings_dir, "faiss_index.bin")
            if not os.path.exists(index_path):
                raise FileNotFoundError(f"FAISS index not found: {index_path}")
            self.index = faiss.read_index(index_path)
            self.logger.info(f"FAISS index loaded: {self.index.ntotal} vectors, dimension {self.index.d}")
            # Load metadata
            metadata_path = os.path.join(self.embeddings_dir, "metadata.pkl")
            if not os.path.exists(metadata_path):
                raise FileNotFoundError(f"Metadata not found: {metadata_path}")
            with open(metadata_path, 'rb') as f:
                self.metadata = pickle.load(f)
            self.logger.info(f"Metadata loaded: {len(self.metadata)} items")
            # Initialize embedding model for queries
            self._initialize_embedding_model()
            self.is_loaded = True
            return {
                "total_chunks": len(self.metadata),
                "embedding_dimension": self.index.d,
                "index_size": self.index.ntotal
            }
        except Exception as e:
            self.logger.error(f"Failed to load index: {e}")
            raise e
    def _initialize_embedding_model(self):
        """Initialize embedding model for query encoding"""
        if self.embedding_model is None:
            self.logger.info("Loading embedding model for queries...")
            # Use the same model that was used to create the embeddings
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            self.logger.info("Embedding model loaded")
    def search(self, query: str, k: int = 10, similarity_threshold: float = 0.3) -> List[Dict[str, Any]]:
        """
        Search for relevant documents using semantic similarity
        Args:
            query: Search query text
            k: Number of results to return
            similarity_threshold: Minimum similarity score
        Returns:
            List of search results with metadata and scores
        """
        if not self.is_loaded:
            raise RuntimeError("Index not loaded. Call load_index() first.")
        # Generate query embedding
        query_embedding = self.embedding_model.encode([query], convert_to_numpy=True)
        # Normalize for cosine similarity (assuming IndexFlatIP)
        faiss.normalize_L2(query_embedding.astype(np.float32))
        # Search index
        distances, indices = self.index.search(query_embedding.astype(np.float32), k)
        # Prepare results
        results = []
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            if idx < len(self.metadata) and distance >= similarity_threshold:
                metadata_item = self.metadata[idx]
                result = {
                    "rank": i + 1,
                    "score": float(distance),
                    "chunk_id": metadata_item.get("chunk_id", f"chunk_{idx}"),
                    "doc_id": metadata_item.get("doc_id", f"doc_{idx}"),
                    "text": metadata_item.get("text", f"[Text for chunk {idx}]"),
                    "metadata": metadata_item
                }
                results.append(result)
        self.logger.info(f"Search returned {len(results)} results for query: '{query[:50]}...'")
        return results
    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the index"""
        if not self.is_loaded:
            return {"error": "Index not loaded"}
        # Count sources
        source_counts = {}
        total_sources = 0
        for item in self.metadata:
            source = item.get("source_file", "unknown")
            source_counts[source] = source_counts.get(source, 0) + 1
            total_sources += 1
        return {
            "total_chunks": len(self.metadata),
            "index_size": self.index.ntotal,
            "embedding_dimension": self.index.d,
            "source_distribution": source_counts,
            "total_sources": total_sources
        }
    def validate_index(self) -> Dict[str, Any]:
        """Validate index health and performance"""
        if not self.is_loaded:
            return {"error": "Index not loaded"}
        validation_results = {
            "index_integrity": False,
            "embedding_consistency": False,
            "search_performance": {},
            "overall_health": "unknown"
        }
        try:
            # Check index integrity
            if self.index.ntotal == len(self.metadata):
                validation_results["index_integrity"] = True
            # Check embedding consistency
            if self.index.d == 384:  # Expected dimension for MiniLM
                validation_results["embedding_consistency"] = True
            # Test search performance
            test_queries = [
                "bottled water delivery service",
                "construction project management",
                "logistics transportation"
            ]
            search_times = []
            for query in test_queries:
                start_time = time.time()
                results = self.search(query, k=3)
                search_time = time.time() - start_time
                search_times.append(search_time)
            validation_results["search_performance"] = {
                "avg_search_time": np.mean(search_times),
                "max_search_time": np.max(search_times),
                "min_search_time": np.min(search_times),
                "total_test_queries": len(test_queries)
            }
            # Overall health
            if (validation_results["index_integrity"] and 
                validation_results["embedding_consistency"] and
                validation_results["search_performance"]["avg_search_time"] < 2.0):
                validation_results["overall_health"] = "healthy"
            else:
                validation_results["overall_health"] = "needs_attention"
        except Exception as e:
            validation_results["error"] = str(e)
            validation_results["overall_health"] = "error"
        return validation_results
def create_rag_engine() -> WorkingRAGEngine:
    """Create and return working RAG engine"""
    return WorkingRAGEngine()
if __name__ == "__main__":
    # Test the working RAG engine
    print("🔍 WORKING RAG ENGINE TEST")
    print("=" * 50)
    try:
        # Create engine
        rag_engine = create_rag_engine()
        print("✓ RAG engine created")
        # Load index
        load_stats = rag_engine.load_index()
        print(f"✓ Index loaded: {load_stats['total_chunks']} chunks")
        # Test search
        test_query = "bottled water delivery service"
        results = rag_engine.search(test_query, k=3)
        print(f"✓ Search test: {len(results)} results for '{test_query}'")
        if results:
            print(f"✓ Top result score: {results[0]['score']:.3f}")
        # Get stats
        stats = rag_engine.get_index_stats()
        print(f"✓ Index stats: {stats['total_chunks']} chunks, {stats['embedding_dimension']} dimensions")
        # Validate
        validation = rag_engine.validate_index()
        print(f"✓ Validation: {validation['overall_health']}")
        print("\n🚀 Working RAG engine is operational!")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()