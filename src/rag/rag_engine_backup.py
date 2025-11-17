import os
import sys
import pickle
import logging
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import json
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config.paths import PathConfig
class RAGEngine:
    """
    Retrieval-Augmented Generation engine for RFP datasets.
    Handles document chunking, embedding generation, FAISS indexing, and semantic retrieval.
    """
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        embeddings_dir: str | None = None,
        processed_data_dir: str | None = None
    ):
        """
        Initialize RAG engine with configurable parameters.
        Args:
            model_name: Sentence transformer model for embeddings
            chunk_size: Maximum tokens per document chunk
            chunk_overlap: Overlap tokens between chunks
            embeddings_dir: Directory to store embeddings and FAISS index
            processed_data_dir: Directory containing processed RFP data
        """
        # Ensure PathConfig directories are initialized
        PathConfig.ensure_directories()

        self.model_name = model_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embeddings_dir = embeddings_dir or str(PathConfig.EMBEDDINGS_DIR)
        self.processed_data_dir = processed_data_dir or str(PathConfig.PROCESSED_DATA_DIR)
        # Create directories if they don't exist
        os.makedirs(self.embeddings_dir, exist_ok=True)
        # Initialize logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        # Initialize model and index
        self.model = None
        self.index = None
        self.documents = []
        self.metadata = []
        # File paths for persistence
        self.index_path = os.path.join(self.embeddings_dir, "faiss_index.bin")
        self.documents_path = os.path.join(self.embeddings_dir, "documents.pkl")
        self.metadata_path = os.path.join(self.embeddings_dir, "metadata.pkl")
        self.embeddings_path = os.path.join(self.embeddings_dir, "embeddings.npy")
    def load_model(self) -> None:
        """Load the sentence transformer model."""
        self.logger.info(f"Loading sentence transformer model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        self.logger.info(f"Model loaded. Embedding dimension: {self.model.get_sentence_embedding_dimension()}")
    def load_rfp_datasets(self) -> pd.DataFrame:
        """
        Load all processed RFP datasets and combine them.
        Returns:
            Combined DataFrame with all RFP data
        """
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
                self.logger.info(f"Loading {filename}")
                df = pd.read_parquet(filepath)
                # Add source file as metadata
                df['source_file'] = filename
                datasets.append(df)
                self.logger.info(f"Loaded {len(df)} records from {filename}")
            else:
                self.logger.warning(f"File not found: {filepath}")
        if not datasets:
            raise FileNotFoundError("No RFP datasets found in processed data directory")
        # Combine all datasets
        combined_df = pd.concat(datasets, ignore_index=True)
        self.logger.info(f"Combined dataset shape: {combined_df.shape}")
        return combined_df
    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks with overlap.
        Args:
            text: Input text to chunk
        Returns:
            List of text chunks
        """
        if pd.isna(text) or not isinstance(text, str):
            return []
        # Simple word-based chunking (approximate token count)
        words = text.split()
        chunks = []
        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk_words = words[i:i + self.chunk_size]
            chunk = " ".join(chunk_words)
            if chunk.strip():  # Only add non-empty chunks
                chunks.append(chunk)
        return chunks if chunks else [text]  # Return original text if chunking fails
    def prepare_documents(self, df: pd.DataFrame) -> Tuple[List[str], List[Dict]]:
        """
        Prepare documents for embedding by chunking and creating metadata.
        Args:
            df: DataFrame with RFP data
        Returns:
            Tuple of (documents list, metadata list)
        """
        documents = []
        metadata = []
        # Define key text columns to process
        text_columns = [
            'description', 'title', 'naics_description', 'set_aside_description',
            'award_description', 'type_of_contract_description'
        ]
        self.logger.info("Preparing documents for embedding...")
        for idx, row in df.iterrows():
            # Combine text from multiple columns
            text_parts = []
            for col in text_columns:
                if col in row and pd.notna(row[col]) and str(row[col]).strip():
                    text_parts.append(f"{col}: {str(row[col])}")
            if not text_parts:
                continue  # Skip rows with no text content
            combined_text = " | ".join(text_parts)
            chunks = self.chunk_text(combined_text)
            for chunk_idx, chunk in enumerate(chunks):
                documents.append(chunk)
                # Create metadata for each chunk
                chunk_metadata = {
                    'original_index': idx,
                    'chunk_index': chunk_idx,
                    'total_chunks': len(chunks),
                    'source_file': row.get('source_file', 'unknown'),
                    'naics_code': row.get('naics_code', ''),
                    'nigp_code': row.get('nigp_code', ''),
                    'total_contract_value': row.get('total_contract_value', 0),
                    'award_date': str(row.get('award_date', '')),
                    'title': str(row.get('title', ''))[:100],  # Truncate for metadata
                    'category': self._determine_category(row)
                }
                metadata.append(chunk_metadata)
        self.logger.info(f"Prepared {len(documents)} document chunks from {len(df)} original records")
        return documents, metadata
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
    def generate_embeddings(self, documents: List[str]) -> np.ndarray:
        """
        Generate embeddings for documents.
        Args:
            documents: List of document chunks
        Returns:
            NumPy array of embeddings
        """
        if not self.model:
            self.load_model()
        self.logger.info(f"Generating embeddings for {len(documents)} documents...")
        # Generate embeddings in batches to handle large datasets
        batch_size = 1000
        embeddings = []
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            batch_embeddings = self.model.encode(batch, show_progress_bar=True)
            embeddings.append(batch_embeddings)
            self.logger.info(f"Processed batch {i//batch_size + 1}/{(len(documents)-1)//batch_size + 1}")
        # Concatenate all embeddings
        all_embeddings = np.vstack(embeddings)
        self.logger.info(f"Generated embeddings shape: {all_embeddings.shape}")
        return all_embeddings
    def build_faiss_index(self, embeddings: np.ndarray) -> faiss.Index:
        """
        Build FAISS index for efficient similarity search.
        Args:
            embeddings: NumPy array of embeddings
        Returns:
            FAISS index
        """
        self.logger.info("Building FAISS index...")
        dimension = embeddings.shape[1]
        # Use IndexFlatIP for inner product similarity (cosine similarity with normalized vectors)
        index = faiss.IndexFlatIP(dimension)
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        # Add embeddings to index
        index.add(embeddings.astype(np.float32))
        self.logger.info(f"FAISS index built with {index.ntotal} vectors")
        return index
    def save_artifacts(self, embeddings: np.ndarray, documents: List[str], metadata: List[Dict]) -> None:
        """Save all artifacts to disk for persistence."""
        self.logger.info("Saving artifacts to disk...")
        # Save FAISS index
        faiss.write_index(self.index, self.index_path)
        # Save embeddings
        np.save(self.embeddings_path, embeddings)
        # Save documents
        with open(self.documents_path, 'wb') as f:
            pickle.dump(documents, f)
        # Save metadata
        with open(self.metadata_path, 'wb') as f:
            pickle.dump(metadata, f)
        # Save configuration and stats
        config = {
            'model_name': self.model_name,
            'chunk_size': self.chunk_size,
            'chunk_overlap': self.chunk_overlap,
            'num_documents': len(documents),
            'embedding_dimension': embeddings.shape[1],
            'created_at': datetime.now().isoformat(),
            'index_type': 'IndexFlatIP'
        }
        config_path = os.path.join(self.embeddings_dir, 'config.json')
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        self.logger.info(f"Artifacts saved to {self.embeddings_dir}")
    def load_artifacts(self) -> bool:
        """
        Load previously saved artifacts.
        Returns:
            True if artifacts loaded successfully, False otherwise
        """
        try:
            self.logger.info("Loading artifacts from disk...")
            # Load FAISS index
            if not os.path.exists(self.index_path):
                return False
            self.index = faiss.read_index(self.index_path)
            # Load documents
            with open(self.documents_path, 'rb') as f:
                self.documents = pickle.load(f)
            # Load metadata
            with open(self.metadata_path, 'rb') as f:
                self.metadata = pickle.load(f)
            # Load model
            if not self.model:
                self.load_model()
            self.logger.info(f"Artifacts loaded successfully. Index contains {self.index.ntotal} vectors")
            return True
        except Exception as e:
            self.logger.error(f"Failed to load artifacts: {e}")
            return False
    def build_index(self, force_rebuild: bool = False) -> None:
        """
        Build the complete RAG index from processed RFP data.
        Args:
            force_rebuild: If True, rebuild even if artifacts exist
        """
        # Check if artifacts already exist
        if not force_rebuild and self.load_artifacts():
            self.logger.info("Using existing artifacts")
            return
        # Load and prepare data
        df = self.load_rfp_datasets()
        documents, metadata = self.prepare_documents(df)
        # Generate embeddings
        embeddings = self.generate_embeddings(documents)
        # Build FAISS index
        self.index = self.build_faiss_index(embeddings)
        # Store documents and metadata
        self.documents = documents
        self.metadata = metadata
        # Save artifacts
        self.save_artifacts(embeddings, documents, metadata)
    def retrieve(self, query: str, k: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve top-k most similar documents for a query.
        Args:
            query: Search query
            k: Number of documents to retrieve
        Returns:
            List of dictionaries containing document text and metadata
        """
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
            if idx < len(self.documents):  # Ensure valid index
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
def main():
    """Main function for testing RAG engine."""
    # Initialize RAG engine
    rag = RAGEngine()
    # Build index
    print("Building RAG index...")
    rag.build_index()
    # Get stats
    stats = rag.get_stats()
    print(f"\nRAG System Stats:")
    print(json.dumps(stats, indent=2))
    # Test queries for each category
    test_queries = [
        "bottled water delivery services for government facilities",
        "construction project management and infrastructure development", 
        "logistics and delivery services for government contracts",
        "facility maintenance and janitorial services"
    ]
    print(f"\nTesting retrieval with sample queries:")
    for query in test_queries:
        print(f"\nQuery: {query}")
        results = rag.retrieve(query, k=3)
        for result in results:
            print(f"  Rank {result['rank']}: Score {result['score']:.3f}")
            print(f"  Category: {result['metadata']['category']}")
            print(f"  Title: {result['metadata']['title']}")
            print(f"  Text preview: {result['text'][:150]}...")
            print()
if __name__ == "__main__":
    main()