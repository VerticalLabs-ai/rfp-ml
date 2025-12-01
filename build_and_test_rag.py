#!/usr/bin/env python3
"""
Build and test RAG system for RFP datasets.
"""
import json
import logging
import os
import pickle
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Tuple

import faiss
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
def get_project_root():
    """Get project root directory (works locally and in Docker)."""
    # Check if running in Docker
    if os.path.exists("/app/data"):
        return "/app"
    # Otherwise use the directory containing this script
    return os.path.dirname(os.path.abspath(__file__))


class RAGEngine:
    """
    Retrieval-Augmented Generation engine for RFP datasets.
    """
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        embeddings_dir: str = None,
        processed_data_dir: str = None
    ):
        project_root = get_project_root()
        if embeddings_dir is None:
            embeddings_dir = os.path.join(project_root, "data", "embeddings")
        if processed_data_dir is None:
            processed_data_dir = os.path.join(project_root, "data", "processed")
        self.model_name = model_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embeddings_dir = embeddings_dir
        self.processed_data_dir = processed_data_dir
        # Create directories
        os.makedirs(self.embeddings_dir, exist_ok=True)
        # Initialize components
        self.model = None
        self.index = None
        self.documents = []
        self.metadata = []
        # File paths
        self.index_path = os.path.join(self.embeddings_dir, "faiss_index.bin")
        self.documents_path = os.path.join(self.embeddings_dir, "documents.pkl")
        self.metadata_path = os.path.join(self.embeddings_dir, "metadata.pkl")
        self.embeddings_path = os.path.join(self.embeddings_dir, "embeddings.npy")
        self.config_path = os.path.join(self.embeddings_dir, "config.json")
    def load_model(self) -> None:
        """Load the sentence transformer model."""
        logger.info(f"Loading sentence transformer model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        logger.info(f"Model loaded. Embedding dimension: {self.model.get_sentence_embedding_dimension()}")
    def load_rfp_datasets(self) -> pd.DataFrame:
        """Load all processed RFP datasets and combine them."""
        datasets = []
        files_to_load = [
            "rfp_master_dataset.parquet",
            "bottled_water_rfps.parquet",
            "construction_rfps.parquet",
            "delivery_rfps.parquet"
        ]
        for filename in files_to_load:
            filepath = os.path.join(self.processed_data_dir, filename)
            if os.path.exists(filepath):
                logger.info(f"Loading {filename}")
                df = pd.read_parquet(filepath)
                df['source_file'] = filename
                datasets.append(df)
                logger.info(f"Loaded {len(df)} records from {filename}")
            else:
                logger.warning(f"File not found: {filepath}")
        if not datasets:
            raise FileNotFoundError("No RFP datasets found")
        # Combine datasets
        combined_df = pd.concat(datasets, ignore_index=True)
        logger.info(f"Combined dataset shape: {combined_df.shape}")
        return combined_df
    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks with overlap."""
        if pd.isna(text) or not isinstance(text, str):
            return []
        words = text.split()
        chunks = []
        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk_words = words[i:i + self.chunk_size]
            chunk = " ".join(chunk_words)
            if chunk.strip():
                chunks.append(chunk)
        return chunks if chunks else [text]
    def _determine_category(self, row: pd.Series) -> str:
        """Determine RFP category based on content."""
        title = str(row.get('title', '')).lower()
        description = str(row.get('description', '')).lower()
        source = str(row.get('source_file', '')).lower()
        if 'bottled_water' in source or any(term in title + description for term in ['water', 'beverage', 'bottle']):
            return 'bottled_water'
        elif 'construction' in source or any(term in title + description for term in ['construction', 'build', 'infrastructure']):
            return 'construction'
        elif 'delivery' in source or any(term in title + description for term in ['delivery', 'transport', 'logistics']):
            return 'delivery'
        else:
            return 'general'
    def prepare_documents(self, df: pd.DataFrame) -> Tuple[List[str], List[Dict]]:
        """Prepare documents for embedding by chunking and creating metadata."""
        documents = []
        metadata = []
        # Key text columns to process
        text_columns = [
            'description', 'title', 'agency', 'office'
        ]
        logger.info("Preparing documents for embedding...")
        for idx, row in df.iterrows():
            # Combine text from multiple columns
            text_parts = []
            for col in text_columns:
                if col in row and pd.notna(row[col]) and str(row[col]).strip():
                    text_parts.append(f"{col}: {str(row[col])}")
            if not text_parts:
                continue
            combined_text = " | ".join(text_parts)
            chunks = self.chunk_text(combined_text)
            for chunk_idx, chunk in enumerate(chunks):
                documents.append(chunk)
                chunk_metadata = {
                    'original_index': idx,
                    'chunk_index': chunk_idx,
                    'total_chunks': len(chunks),
                    'source_file': row.get('source_file', 'unknown'),
                    'naics_code': row.get('naics_code', ''),
                    'award_amount': row.get('award_amount', 0),
                    'award_date': str(row.get('award_date', '')),
                    'title': str(row.get('title', ''))[:100],
                    'category': self._determine_category(row),
                    'agency': str(row.get('agency', ''))[:50]
                }
                metadata.append(chunk_metadata)
        logger.info(f"Prepared {len(documents)} document chunks from {len(df)} original records")
        return documents, metadata
    def generate_embeddings(self, documents: List[str]) -> np.ndarray:
        """Generate embeddings for documents."""
        if not self.model:
            self.load_model()
        logger.info(f"Generating embeddings for {len(documents)} documents...")
        # Generate in batches
        batch_size = 1000
        embeddings = []
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            batch_embeddings = self.model.encode(batch, show_progress_bar=True)
            embeddings.append(batch_embeddings)
            logger.info(f"Processed batch {i//batch_size + 1}/{(len(documents)-1)//batch_size + 1}")
        all_embeddings = np.vstack(embeddings)
        logger.info(f"Generated embeddings shape: {all_embeddings.shape}")
        return all_embeddings
    def build_faiss_index(self, embeddings: np.ndarray) -> faiss.Index:
        """Build FAISS index for efficient similarity search."""
        logger.info("Building FAISS index...")
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatIP(dimension)
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        index.add(embeddings.astype(np.float32))
        logger.info(f"FAISS index built with {index.ntotal} vectors")
        return index
    def save_artifacts(self, embeddings: np.ndarray, documents: List[str], metadata: List[Dict]) -> None:
        """Save all artifacts to disk."""
        logger.info("Saving artifacts to disk...")
        # Save FAISS index
        faiss.write_index(self.index, self.index_path)
        # Save embeddings
        np.save(self.embeddings_path, embeddings)
        # Save documents and metadata
        with open(self.documents_path, 'wb') as f:
            pickle.dump(documents, f)
        with open(self.metadata_path, 'wb') as f:
            pickle.dump(metadata, f)
        # Save configuration
        config = {
            'model_name': self.model_name,
            'chunk_size': self.chunk_size,
            'chunk_overlap': self.chunk_overlap,
            'num_documents': len(documents),
            'embedding_dimension': embeddings.shape[1],
            'created_at': datetime.now().isoformat(),
            'index_type': 'IndexFlatIP'
        }
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info(f"Artifacts saved to {self.embeddings_dir}")
    def load_artifacts(self) -> bool:
        """Load previously saved artifacts."""
        try:
            logger.info("Loading artifacts from disk...")
            if not os.path.exists(self.index_path):
                return False
            self.index = faiss.read_index(self.index_path)
            with open(self.documents_path, 'rb') as f:
                self.documents = pickle.load(f)
            with open(self.metadata_path, 'rb') as f:
                self.metadata = pickle.load(f)
            if not self.model:
                self.load_model()
            logger.info(f"Artifacts loaded successfully. Index contains {self.index.ntotal} vectors")
            return True
        except Exception as e:
            logger.error(f"Failed to load artifacts: {e}")
            return False
    def build_index(self, force_rebuild: bool = False) -> None:
        """Build the complete RAG index from processed RFP data."""
        # Check if artifacts exist
        if not force_rebuild and self.load_artifacts():
            logger.info("Using existing artifacts")
            return
        # Load and prepare data
        df = self.load_rfp_datasets()
        documents, metadata = self.prepare_documents(df)
        # Generate embeddings
        embeddings = self.generate_embeddings(documents)
        # Build FAISS index
        self.index = self.build_faiss_index(embeddings)
        # Store data
        self.documents = documents
        self.metadata = metadata
        # Save artifacts
        self.save_artifacts(embeddings, documents, metadata)
    def retrieve(self, query: str, k: int = 10) -> List[Dict[str, Any]]:
        """Retrieve top-k most similar documents for a query."""
        if not self.index or not self.model:
            raise RuntimeError("Index not built or model not loaded. Call build_index() first.")
        # Generate query embedding
        query_embedding = self.model.encode([query])
        faiss.normalize_L2(query_embedding)
        # Search in FAISS index
        scores, indices = self.index.search(query_embedding.astype(np.float32), k)
        # Prepare results
        results = []
        for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx < len(self.documents):
                result = {
                    'rank': i + 1,
                    'score': float(score),
                    'text': self.documents[idx],
                    'metadata': self.metadata[idx]
                }
                results.append(result)
        return results
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the RAG system."""
        if not self.index:
            return {'status': 'not_built'}
        # Category distribution
        categories = {}
        for meta in self.metadata:
            cat = meta.get('category', 'unknown')
            categories[cat] = categories.get(cat, 0) + 1
        return {
            'status': 'ready',
            'total_documents': len(self.documents),
            'index_size': self.index.ntotal,
            'embedding_dimension': self.model.get_sentence_embedding_dimension() if self.model else None,
            'model_name': self.model_name,
            'category_distribution': categories,
            'chunk_size': self.chunk_size,
            'chunk_overlap': self.chunk_overlap
        }
def test_rag_system():
    """Test the RAG system with sample queries."""
    print("=" * 80)
    print("RAG SYSTEM BUILD AND VALIDATION TEST")
    print("=" * 80)
    # Initialize RAG engine
    rag = RAGEngine()
    # Build index
    print("Building RAG index...")
    start_time = time.time()
    rag.build_index()
    build_time = time.time() - start_time
    print(f"Index built in {build_time:.2f} seconds")
    # Get stats
    stats = rag.get_stats()
    print("\nRAG System Stats:")
    print(json.dumps(stats, indent=2))
    # Test queries for each category
    test_queries = [
        {
            "category": "Bottled Water",
            "query": "bottled water delivery services for government facilities",
        },
        {
            "category": "Construction",
            "query": "construction project management and infrastructure development",
        },
        {
            "category": "Delivery/Logistics",
            "query": "logistics and delivery services for government contracts",
        },
        {
            "category": "General",
            "query": "facility maintenance and professional services",
        }
    ]
    print("\n" + "="*80)
    print("TESTING RETRIEVAL PERFORMANCE")
    print("="*80)
    total_retrieval_time = 0
    for test_case in test_queries:
        print(f"\nCategory: {test_case['category']}")
        print(f"Query: {test_case['query']}")
        print("-" * 60)
        # Measure retrieval time
        start_time = time.time()
        results = rag.retrieve(test_case['query'], k=3)
        retrieval_time = time.time() - start_time
        total_retrieval_time += retrieval_time
        print(f"Retrieval time: {retrieval_time:.3f} seconds")
        if not results:
            print("No results found!")
            continue
        for result in results:
            print(f"\nRank {result['rank']} (Score: {result['score']:.3f}):")
            print(f"  Category: {result['metadata'].get('category', 'N/A')}")
            print(f"  Title: {result['metadata'].get('title', 'N/A')}")
            print(f"  Agency: {result['metadata'].get('agency', 'N/A')}")
            print(f"  Text Preview: {result['text'][:150]}...")
    avg_retrieval_time = total_retrieval_time / len(test_queries)
    print("\n" + "="*80)
    print("PERFORMANCE SUMMARY")
    print("="*80)
    print(f"Total Documents: {stats['total_documents']:,}")
    print(f"Index Build Time: {build_time:.2f} seconds")
    print(f"Average Retrieval Time: {avg_retrieval_time:.3f} seconds")
    print(f"Model: {stats['model_name']}")
    print(f"Embedding Dimension: {stats['embedding_dimension']}")
    # Category distribution
    print("\nCategory Distribution:")
    for category, count in stats['category_distribution'].items():
        percentage = (count / stats['total_documents']) * 100
        print(f"  {category}: {count:,} documents ({percentage:.1f}%)")
    # Validation criteria
    validation_results = {
        'system_ready': stats['status'] == 'ready',
        'adequate_size': stats['total_documents'] > 1000,
        'fast_build': build_time < 300,  # 5 minutes
        'fast_retrieval': avg_retrieval_time < 1.0,  # 1 second
        'balanced_categories': len(stats['category_distribution']) >= 3
    }
    print("\nVALIDATION RESULTS:")
    passed = 0
    for criterion, result in validation_results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {criterion}: {status}")
        if result:
            passed += 1
    overall_score = passed / len(validation_results)
    print(f"\nOVERALL VALIDATION: {passed}/{len(validation_results)} ({overall_score:.1%})")
    if overall_score >= 0.8:
        print("✅ RAG SYSTEM VALIDATION: SUCCESSFUL")
        return True
    else:
        print("❌ RAG SYSTEM VALIDATION: NEEDS IMPROVEMENT")
        return False
if __name__ == "__main__":
    success = test_rag_system()
    sys.exit(0 if success else 1)
