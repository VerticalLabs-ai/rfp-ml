"""
Base scraper class for RFP portals.
Provides common interface and utilities for all portal-specific scrapers.
"""
import os
import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ScrapedDocument:
    """Represents a document downloaded from an RFP."""
    filename: str
    source_url: str
    file_type: Optional[str] = None
    document_type: Optional[str] = None  # "solicitation", "amendment", "attachment", "qa_response"
    file_path: Optional[str] = None  # Local path after download
    file_size: Optional[int] = None
    checksum: Optional[str] = None
    downloaded_at: Optional[datetime] = None


@dataclass
class ScrapedQA:
    """Represents a Q&A entry from an RFP."""
    question_number: Optional[str] = None
    question_text: str = ""
    answer_text: Optional[str] = None
    asked_date: Optional[datetime] = None
    answered_date: Optional[datetime] = None


@dataclass
class ScrapedRFP:
    """Represents scraped RFP data from a portal."""
    # Core identifiers
    source_url: str
    source_platform: str

    # Basic info
    title: str
    solicitation_number: Optional[str] = None
    description: Optional[str] = None
    agency: Optional[str] = None
    office: Optional[str] = None

    # Dates
    posted_date: Optional[datetime] = None
    response_deadline: Optional[datetime] = None

    # Amounts
    award_amount: Optional[float] = None
    estimated_value: Optional[float] = None

    # Classification
    naics_code: Optional[str] = None
    category: Optional[str] = None

    # Scraped content
    documents: List[ScrapedDocument] = field(default_factory=list)
    qa_items: List[ScrapedQA] = field(default_factory=list)

    # Metadata
    raw_data: Dict[str, Any] = field(default_factory=dict)
    scrape_checksum: Optional[str] = None
    scraped_at: datetime = field(default_factory=datetime.utcnow)

    def compute_checksum(self) -> str:
        """Compute checksum of scraped content for change detection."""
        content = f"{self.title}|{self.solicitation_number}|{self.description}|{len(self.documents)}|{len(self.qa_items)}"
        self.scrape_checksum = hashlib.md5(content.encode()).hexdigest()
        return self.scrape_checksum


class BaseScraper(ABC):
    """
    Abstract base class for RFP portal scrapers.

    Subclasses must implement:
    - scrape(url): Extract RFP data from a URL
    - is_valid_url(url): Check if URL belongs to this portal
    """

    PLATFORM_NAME: str = "unknown"
    SUPPORTED_DOMAINS: List[str] = []

    def __init__(self, document_storage_path: str = "data/rfp_documents"):
        """
        Initialize the scraper.

        Args:
            document_storage_path: Base path for storing downloaded documents
        """
        self.document_storage_path = Path(document_storage_path)
        self.document_storage_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"{self.__class__.__name__} initialized with storage: {self.document_storage_path}")

    def is_valid_url(self, url: str) -> bool:
        """
        Check if URL is supported by this scraper.

        Args:
            url: URL to check

        Returns:
            True if URL belongs to a supported domain
        """
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        return any(supported in domain for supported in self.SUPPORTED_DOMAINS)

    @abstractmethod
    async def scrape(self, url: str) -> ScrapedRFP:
        """
        Scrape RFP data from the given URL.

        Args:
            url: URL to scrape

        Returns:
            ScrapedRFP with extracted data

        Raises:
            ValueError: If URL is not valid for this scraper
            ScraperError: If scraping fails
        """
        pass

    @abstractmethod
    async def download_documents(self, rfp: ScrapedRFP, rfp_id: str) -> List[ScrapedDocument]:
        """
        Download all documents for an RFP.

        Args:
            rfp: ScrapedRFP containing document URLs
            rfp_id: Unique ID for organizing storage

        Returns:
            List of ScrapedDocument with local file paths
        """
        pass

    @abstractmethod
    async def refresh(self, url: str, existing_checksum: Optional[str] = None) -> Dict[str, Any]:
        """
        Check for updates on an existing RFP.

        Args:
            url: URL to check
            existing_checksum: Previous scrape checksum for comparison

        Returns:
            Dict with:
                - has_changes: bool
                - new_qa_count: int
                - new_document_count: int
                - updated_rfp: Optional[ScrapedRFP]
        """
        pass

    def get_document_storage_path(self, rfp_id: str) -> Path:
        """Get the storage path for a specific RFP's documents."""
        rfp_path = self.document_storage_path / rfp_id
        rfp_path.mkdir(parents=True, exist_ok=True)
        return rfp_path

    def compute_file_checksum(self, file_path: str) -> str:
        """Compute MD5 checksum of a file."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()


class ScraperError(Exception):
    """Base exception for scraper errors."""
    pass


class ScraperConnectionError(ScraperError):
    """Error connecting to portal."""
    pass


class ScraperParseError(ScraperError):
    """Error parsing portal content."""
    pass


class ScraperDownloadError(ScraperError):
    """Error downloading documents."""
    pass
