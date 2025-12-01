import logging
import os
import pickle
import re
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

        distances, indices = self.index.search(query_embedding, k * 2) # Retrieve extra for filtering

        results = []
        for idx in indices[0]:
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
        Robust parsing of a reference document to extract sections.
        Handles multiple formats: markdown headers, HTML headings, and plain text patterns.
        """
        # Common section headers to look for
        section_patterns = {
            "executive_summary": [
                r"executive\s+summary",
                r"summary",
                r"overview",
                r"introduction"
            ],
            "technical_approach": [
                r"technical\s+approach",
                r"methodology",
                r"approach",
                r"solution\s+approach",
                r"technical\s+solution"
            ],
            "past_performance": [
                r"past\s+performance",
                r"relevant\s+experience",
                r"qualifications",
                r"experience"
            ],
            "pricing": [
                r"pricing",
                r"cost",
                r"price\s+proposal",
                r"financial"
            ],
            "management_plan": [
                r"management\s+plan",
                r"project\s+management",
                r"organization",
                r"team"
            ],
            "company_qualifications": [
                r"company\s+qualifications",
                r"corporate\s+capabilities",
                r"about\s+us",
                r"company\s+profile"
            ],
            "compliance": [
                r"compliance",
                r"requirements",
                r"compliance\s+matrix"
            ]
        }
        
        # Normalize text for parsing
        normalized_text = text
        
        # Extract sections based on different formats
        sections = self._extract_sections(normalized_text, section_patterns)
        
        if not sections:
            # Fallback: treat entire document as "General"
            self.logger.info(f"No sections detected in {filename}, treating as 'General'")
            self.add_example(text, "General", {"source_file": filename})
        else:
            # Add each detected section as a separate example
            for section_type, section_text in sections:
                if len(section_text.strip()) > 50:  # Only add substantial sections
                    self.add_example(
                        section_text,
                        section_type,
                        {"source_file": filename, "section_type": section_type}
                    )
                    self.logger.info(f"Extracted {section_type} section from {filename}")
    
    def _extract_sections(self, text: str, section_patterns: dict[str, list[str]]) -> list[tuple[str, str]]:
        """
        Extract sections from text using multiple parsing strategies.
        Returns list of (section_type, section_text) tuples.
        """
        sections = []
        lines = text.split('\n')
        
        # Strategy 1: Markdown-style headers (# ## ###)
        markdown_header_pattern = re.compile(r'^#{1,3}\s+(.+)$', re.IGNORECASE)
        
        # Strategy 2: HTML headings (<h1>, <h2>, <h3>)
        html_header_pattern = re.compile(r'<h[1-3][^>]*>(.+?)</h[1-3]>', re.IGNORECASE | re.DOTALL)
        
        # Strategy 3: Plain text headers (all caps, bold patterns)
        plain_header_pattern = re.compile(r'^(?:[A-Z][A-Z\s]{3,}|[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+):?\s*$')
        
        current_section = None
        current_text = []
        section_start_idx = 0
        
        # Track header positions
        header_positions = []
        
        # Find all potential headers
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Check markdown headers
            md_match = markdown_header_pattern.match(line_stripped)
            if md_match:
                header_text = md_match.group(1).strip()
                header_positions.append((i, header_text, 'markdown'))
                continue
            
            # Check HTML headers
            html_match = html_header_pattern.search(line_stripped)
            if html_match:
                header_text = html_match.group(1).strip()
                # Remove HTML tags from header text
                header_text = re.sub(r'<[^>]+>', '', header_text)
                header_positions.append((i, header_text, 'html'))
                continue
            
            # Check plain text headers (lines that look like headers)
            if len(line_stripped) > 3 and len(line_stripped) < 100:
                if plain_header_pattern.match(line_stripped) or (
                    line_stripped.isupper() and len(line_stripped.split()) <= 8
                ):
                    header_positions.append((i, line_stripped, 'plain'))
        
        # Extract sections between headers
        for idx, (line_num, header_text, header_type) in enumerate(header_positions):
            # Determine section type from header text
            section_type = self._classify_section(header_text, section_patterns)
            
            if section_type:
                # Get text until next header or end of document
                start_line = line_num + 1
                end_line = header_positions[idx + 1][0] if idx + 1 < len(header_positions) else len(lines)
                
                section_lines = lines[start_line:end_line]
                section_text = '\n'.join(section_lines).strip()
                
                if section_text:
                    sections.append((section_type, section_text))
        
        # If no structured sections found, try pattern-based extraction
        if not sections:
            sections = self._extract_by_patterns(text, section_patterns)
        
        return sections
    
    def _classify_section(self, header_text: str, section_patterns: dict[str, list[str]]) -> str | None:
        """Classify a header into a known section type."""
        header_lower = header_text.lower()
        
        for section_type, patterns in section_patterns.items():
            for pattern in patterns:
                if re.search(pattern, header_lower):
                    return section_type
        
        return None
    
    def _extract_by_patterns(self, text: str, section_patterns: dict[str, list[str]]) -> list[tuple[str, str]]:
        """
        Fallback: Extract sections by searching for patterns in the text.
        Splits text at section boundaries.
        """
        sections = []
        text_lower = text.lower()
        
        # Find all section markers
        markers = []
        for section_type, patterns in section_patterns.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text_lower):
                    markers.append((match.start(), section_type, match.group()))
        
        # Sort by position
        markers.sort(key=lambda x: x[0])
        
        # Extract text between markers
        for idx, (start_pos, section_type, _) in enumerate(markers):
            end_pos = markers[idx + 1][0] if idx + 1 < len(markers) else len(text)
            section_text = text[start_pos:end_pos].strip()
            
            # Remove the header line itself
            lines = section_text.split('\n')
            if len(lines) > 1:
                section_text = '\n'.join(lines[1:]).strip()
            
            if len(section_text) > 50:  # Only substantial sections
                sections.append((section_type, section_text))
        
        return sections

# Global instance
style_manager = StyleGuideManager()
