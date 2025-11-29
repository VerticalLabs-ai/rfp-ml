import logging
import os
import pickle
from dataclasses import dataclass
from typing import Any

# Import path configuration
from src.config.paths import PathConfig

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

@dataclass
class StyleExample:
    text: str
    section_type: str  # e.g., "executive_summary", "technical_approach"
    metadata: dict[str, Any] = None

class StyleGuideManager:
    """
    Manages 'Voice of the Customer' style examples.
    Stores user-uploaded reference proposals and retrieves relevant style snippets
    to guide LLM generation.
    """
    def __init__(self, data_dir: str = None):
        self.logger = logging.getLogger(__name__)
        self.data_dir = data_dir or str(PathConfig.DATA_DIR / "style_guide")
        os.makedirs(self.data_dir, exist_ok=True)

        self.index_path = os.path.join(self.data_dir, "style_index.faiss")
        self.metadata_path = os.path.join(self.data_dir, "style_metadata.pkl")

        self.model_name = "all-MiniLM-L6-v2"
        self.model = None
        self.index = None
        self.examples: list[StyleExample] = []

        self._initialize()

    def _initialize(self):
        """Initialize model and load index."""
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.model = SentenceTransformer(self.model_name)
                self.logger.info(f"Style embedding model {self.model_name} loaded.")
            except Exception as e:
                self.logger.error(f"Failed to load style embedding model: {e}")

        if os.path.exists(self.index_path) and os.path.exists(self.metadata_path):
            self._load_index()
        else:
            self._create_empty_index()

    def _create_empty_index(self):
        if FAISS_AVAILABLE and self.model:
            embedding_dim = self.model.get_sentence_embedding_dimension()
            self.index = faiss.IndexFlatIP(embedding_dim)
            self.examples = []
            self.logger.info("Created empty FAISS index for style guide.")

    def _load_index(self):
        if FAISS_AVAILABLE:
            try:
                self.index = faiss.read_index(self.index_path)
                with open(self.metadata_path, 'rb') as f:
                    self.examples = pickle.load(f)
                self.logger.info(f"Loaded style index with {len(self.examples)} examples.")
            except Exception as e:
                self.logger.error(f"Failed to load style index: {e}")
                self._create_empty_index()

    def _save_index(self):
        if FAISS_AVAILABLE and self.index:
            faiss.write_index(self.index, self.index_path)
            with open(self.metadata_path, 'wb') as f:
                pickle.dump(self.examples, f)
            self.logger.info("Saved style index to disk.")

    def add_example(self, text: str, section_type: str, metadata: dict[str, Any] = None):
        """Add a style example to the index."""
        if not self.model or not self.index:
            self.logger.warning("StyleManager not initialized (missing dependencies).")
            return

        # Create embedding
        embedding = self.model.encode([text])
        faiss.normalize_L2(embedding)

        # Add to index
        self.index.add(embedding)

        # Store metadata
        example = StyleExample(text=text, section_type=section_type, metadata=metadata or {})
        self.examples.append(example)

        self._save_index()
        self.logger.info(f"Added style example for {section_type}.")

    def retrieve_examples(self, query: str, section_type: str = None, k: int = 3) -> list[StyleExample]:
        """Retrieve relevant style examples."""
        if not self.model or not self.index or len(self.examples) == 0:
            return []

        # Filter by section_type if needed (naive filter after retrieval, or better: retrieval then filter)
        # For small datasets, we can retrieve more and filter.

        query_embedding = self.model.encode([query])
        faiss.normalize_L2(query_embedding)

        D, I = self.index.search(query_embedding, k * 2) # Retrieve extra for filtering

        results = []
        for idx in I[0]:
            if idx < 0 or idx >= len(self.examples):
                continue

            example = self.examples[idx]
            if section_type and example.section_type != section_type:
                continue

            results.append(example)
            if len(results) >= k:
                break

        return results

    def ingest_file(self, text: str, filename: str):
        """
        Heuristic parsing of a reference document to extract sections.
        This is a simplified parser.
        """
        # Naive split by common headers
        headers = ["Executive Summary", "Technical Approach", "Past Performance", "Pricing", "Management Plan"]

        # TODO: Implement robust parsing. For now, treat whole file as "General" or try to detect one section.

        detected_section = "General"
        lower_text = text.lower()

        for h in headers:
            if h.lower() in lower_text[:200]: # Check start of file
                detected_section = h.lower().replace(" ", "_")
                break

        self.add_example(text, detected_section, {"source_file": filename})

# Global instance
style_manager = StyleGuideManager()
