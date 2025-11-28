"""
BeaconBid RFP scraper using Stagehand/Browserbase for AI-powered extraction.

Stagehand is an AI-native browser automation framework that uses LLMs for resilient
web scraping, even when page layouts change.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiofiles
import aiohttp
from aiohttp import ClientTimeout

from .base_scraper import (
    BaseScraper,
    ScrapedDocument,
    ScrapedQA,
    ScrapedRFP,
    ScraperConnectionError,
    ScraperDownloadError,
    ScraperError,
    ScraperParseError,
)

logger = logging.getLogger(__name__)


class BeaconBidScraper(BaseScraper):
    """
    Scraper for BeaconBid (beaconbid.com) RFP portal.

    Uses Stagehand with Browserbase for cloud browser automation.
    Stagehand's AI-powered extraction makes scraping resilient to UI changes.
    """

    PLATFORM_NAME = "beaconbid"
    SUPPORTED_DOMAINS = ["beaconbid.com", "www.beaconbid.com"]

    # Configuration constants
    DOWNLOAD_TIMEOUT_SECONDS = 60
    DOWNLOAD_MAX_RETRIES = 3
    DOWNLOAD_RETRY_DELAY_SECONDS = 2

    def __init__(
        self,
        document_storage_path: str = "data/rfp_documents",
        browserbase_project_id: str | None = None,
        browserbase_api_key: str | None = None,
    ):
        """
        Initialize BeaconBid scraper.

        Args:
            document_storage_path: Base path for storing downloaded documents
            browserbase_project_id: Browserbase project ID (or from env BROWSERBASE_PROJECT_ID)
            browserbase_api_key: Browserbase API key (or from env BROWSERBASE_API_KEY)
        """
        super().__init__(document_storage_path)

        self.browserbase_project_id = browserbase_project_id or os.getenv(
            "BROWSERBASE_PROJECT_ID", "80ee6cd7-7ffd-4409-97ca-20d5a466bfdb"
        )
        self.browserbase_api_key = browserbase_api_key or os.getenv(
            "BROWSERBASE_API_KEY", ""
        )

        if not self.browserbase_api_key:
            logger.warning("Browserbase API key not configured. Scraping will fail.")

    async def _create_stagehand_session(self) -> Any:
        """
        Create a Stagehand browser session using Browserbase.

        Returns:
            Stagehand instance with browser session
        """
        try:
            # Import stagehand - it's a Python package that wraps the Stagehand SDK
            from stagehand import Stagehand

            stagehand = Stagehand(
                env="BROWSERBASE",
                api_key=self.browserbase_api_key,
                project_id=self.browserbase_project_id,
                verbose=1,  # 0=quiet, 1=info, 2=debug
            )

            await stagehand.init()
            logger.info("Stagehand session initialized with Browserbase")
            return stagehand

        except ImportError:
            logger.error("Stagehand package not installed. Run: pip install stagehand")
            raise ScraperError("Stagehand package not installed")
        except Exception as e:
            logger.error(f"Failed to create Stagehand session: {e}")
            raise ScraperConnectionError(f"Failed to connect to Browserbase: {e}")

    async def scrape(self, url: str) -> ScrapedRFP:
        """
        Scrape RFP data from a BeaconBid URL.

        Args:
            url: BeaconBid solicitation URL

        Returns:
            ScrapedRFP with extracted data
        """
        if not self.is_valid_url(url):
            raise ValueError(f"URL not supported by BeaconBid scraper: {url}")

        logger.info(f"Scraping BeaconBid URL: {url}")
        stagehand = None

        try:
            stagehand = await self._create_stagehand_session()
            page = stagehand.page

            # Navigate to the URL
            await page.goto(url)
            await asyncio.sleep(2)  # Wait for dynamic content

            # Extract RFP metadata using Stagehand's AI extraction
            rfp_data = await self._extract_rfp_metadata(stagehand)

            # Extract documents
            documents = await self._extract_documents(stagehand)

            # Extract Q&A
            qa_items = await self._extract_qa(stagehand)

            # Build the ScrapedRFP
            scraped_rfp = ScrapedRFP(
                source_url=url,
                source_platform=self.PLATFORM_NAME,
                title=rfp_data.get("title", "Untitled RFP"),
                solicitation_number=rfp_data.get("solicitation_number"),
                description=rfp_data.get("description"),
                agency=rfp_data.get("agency"),
                office=rfp_data.get("office"),
                posted_date=self._parse_date(rfp_data.get("posted_date")),
                response_deadline=self._parse_date(rfp_data.get("response_deadline")),
                award_amount=self._parse_amount(rfp_data.get("award_amount")),
                estimated_value=self._parse_amount(rfp_data.get("estimated_value")),
                naics_code=rfp_data.get("naics_code"),
                category=rfp_data.get("category"),
                documents=documents,
                qa_items=qa_items,
                raw_data=rfp_data,
            )

            scraped_rfp.compute_checksum()
            logger.info(f"Successfully scraped RFP: {scraped_rfp.title}")
            return scraped_rfp

        except Exception as e:
            logger.error(f"Error scraping BeaconBid URL {url}: {e}")
            raise ScraperParseError(f"Failed to scrape BeaconBid: {e}")

        finally:
            if stagehand:
                try:
                    await stagehand.close()
                except Exception as e:
                    logger.warning(f"Error closing Stagehand session: {e}")

    async def _extract_rfp_metadata(self, stagehand: Any) -> dict[str, Any]:
        """
        Extract RFP metadata using Stagehand's AI extraction.

        Args:
            stagehand: Active Stagehand session

        Returns:
            Dict with extracted metadata
        """
        try:
            # Use Stagehand's extract() for AI-powered data extraction
            result = await stagehand.extract(
                {
                    "instruction": """Extract the RFP (Request for Proposal) information from this page.
                Find and extract:
                - title: The main title/name of the solicitation
                - solicitation_number: The official solicitation or RFP number
                - agency: The government agency or organization posting this RFP
                - office: The specific office or department (if shown)
                - description: A summary or description of what the RFP is for
                - posted_date: When the RFP was posted/published
                - response_deadline: The deadline for submitting proposals/bids
                - award_amount: Any mentioned contract value or estimated amount
                - naics_code: Any NAICS code mentioned
                - category: The category or type of work (e.g., IT Services, Construction)
                """,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "solicitation_number": {"type": "string"},
                            "agency": {"type": "string"},
                            "office": {"type": "string"},
                            "description": {"type": "string"},
                            "posted_date": {"type": "string"},
                            "response_deadline": {"type": "string"},
                            "award_amount": {"type": "string"},
                            "naics_code": {"type": "string"},
                            "category": {"type": "string"},
                        },
                    },
                }
            )

            logger.info(f"Extracted metadata: {result}")
            return result if result else {}

        except Exception as e:
            logger.error(f"Error extracting metadata: {e}")
            return {}

    async def _extract_documents(self, stagehand: Any) -> list[ScrapedDocument]:
        """
        Extract document links from the RFP page.

        Args:
            stagehand: Active Stagehand session

        Returns:
            List of ScrapedDocument objects (without local paths - not downloaded yet)
        """
        try:
            # Use Stagehand to find document links
            result = await stagehand.extract(
                {
                    "instruction": """Find all downloadable documents/attachments on this page.
                For each document, extract:
                - filename: The name of the file
                - url: The download URL or link
                - type: The type of document (solicitation, amendment, attachment, etc.)
                """,
                    "schema": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "filename": {"type": "string"},
                                "url": {"type": "string"},
                                "type": {"type": "string"},
                            },
                        },
                    },
                }
            )

            documents = []
            if result:
                for doc in result:
                    filename = doc.get("filename", "unknown")
                    file_ext = Path(filename).suffix.lower().lstrip(".")

                    documents.append(
                        ScrapedDocument(
                            filename=filename,
                            source_url=doc.get("url", ""),
                            file_type=file_ext if file_ext else None,
                            document_type=self._classify_document_type(
                                doc.get("type", ""), filename
                            ),
                        )
                    )

            logger.info(f"Found {len(documents)} documents")
            return documents

        except Exception as e:
            logger.error(f"Error extracting documents: {e}")
            return []

    async def _extract_qa(self, stagehand: Any) -> list[ScrapedQA]:
        """
        Extract Q&A entries from the RFP page.

        Args:
            stagehand: Active Stagehand session

        Returns:
            List of ScrapedQA objects
        """
        try:
            # First, try to navigate to Q&A section if it exists
            try:
                await stagehand.act(
                    {
                        "action": "click",
                        "instruction": "Click on the Q&A tab or Questions and Answers section if visible",
                    }
                )
                await asyncio.sleep(1)  # Wait for content to load
            except Exception:
                logger.debug("No Q&A tab found, checking current page")

            # Extract Q&A content
            result = await stagehand.extract(
                {
                    "instruction": """Find all Questions and Answers (Q&A) on this page.
                For each Q&A entry, extract:
                - question_number: The question number (Q1, Q2, etc.) if shown
                - question: The question text
                - answer: The answer text (may be empty if not yet answered)
                - asked_date: When the question was asked (if shown)
                - answered_date: When it was answered (if shown)
                """,
                    "schema": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "question_number": {"type": "string"},
                                "question": {"type": "string"},
                                "answer": {"type": "string"},
                                "asked_date": {"type": "string"},
                                "answered_date": {"type": "string"},
                            },
                        },
                    },
                }
            )

            qa_items = []
            if result:
                for qa in result:
                    if qa.get("question"):  # Only add if there's a question
                        qa_items.append(
                            ScrapedQA(
                                question_number=qa.get("question_number"),
                                question_text=qa.get("question", ""),
                                answer_text=qa.get("answer"),
                                asked_date=self._parse_date(qa.get("asked_date")),
                                answered_date=self._parse_date(qa.get("answered_date")),
                            )
                        )

            logger.info(f"Found {len(qa_items)} Q&A items")
            return qa_items

        except Exception as e:
            logger.error(f"Error extracting Q&A: {e}")
            return []

    async def download_documents(
        self, rfp: ScrapedRFP, rfp_id: str
    ) -> list[ScrapedDocument]:
        """
        Download all documents for an RFP with retry logic.

        Args:
            rfp: ScrapedRFP containing document URLs
            rfp_id: Unique ID for organizing storage

        Returns:
            List of ScrapedDocument with local file paths
        """
        storage_path = self.get_document_storage_path(rfp_id)
        downloaded_docs = []
        timeout = ClientTimeout(total=self.DOWNLOAD_TIMEOUT_SECONDS)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            for doc in rfp.documents:
                if not doc.source_url:
                    logger.warning("No source URL for document: %s", doc.filename)
                    continue

                downloaded = await self._download_single_document(
                    session, doc, storage_path
                )
                if downloaded:
                    downloaded_docs.append(downloaded)

        return downloaded_docs

    async def _download_single_document(
        self, session: aiohttp.ClientSession, doc: ScrapedDocument, storage_path: Path
    ) -> ScrapedDocument | None:
        """Download a single document with retry logic."""
        last_error: Exception | None = None

        for attempt in range(1, self.DOWNLOAD_MAX_RETRIES + 1):
            try:
                logger.info(
                    "Downloading (attempt %d/%d): %s",
                    attempt,
                    self.DOWNLOAD_MAX_RETRIES,
                    doc.filename,
                )
                async with session.get(doc.source_url) as response:
                    if response.status == 200:
                        # Generate safe filename
                        safe_filename = self._sanitize_filename(doc.filename)
                        file_path = storage_path / safe_filename

                        # Write file
                        content = await response.read()
                        async with aiofiles.open(file_path, "wb") as f:
                            await f.write(content)

                        # Update document info
                        doc.file_path = str(file_path)
                        doc.file_size = len(content)
                        doc.checksum = self.compute_file_checksum(str(file_path))
                        doc.downloaded_at = datetime.now(timezone.utc)

                        logger.info(
                            "Downloaded: %s (%d bytes)", safe_filename, doc.file_size
                        )
                        return doc

                    logger.warning(
                        "Failed to download %s: HTTP %d", doc.filename, response.status
                    )
                    last_error = ScraperDownloadError(f"HTTP {response.status}")

            except asyncio.TimeoutError:
                logger.warning(
                    "Timeout downloading %s (attempt %d)", doc.filename, attempt
                )
                last_error = ScraperDownloadError(
                    f"Timeout after {self.DOWNLOAD_TIMEOUT_SECONDS}s"
                )
            except aiohttp.ClientError as e:
                logger.warning(
                    "Client error downloading %s (attempt %d): %s",
                    doc.filename,
                    attempt,
                    e,
                )
                last_error = e
            except Exception as e:
                logger.error("Unexpected error downloading %s: %s", doc.filename, e)
                last_error = e
                break  # Don't retry unexpected errors

            if attempt < self.DOWNLOAD_MAX_RETRIES:
                await asyncio.sleep(self.DOWNLOAD_RETRY_DELAY_SECONDS)

        logger.error(
            "Failed to download %s after %d attempts: %s",
            doc.filename,
            self.DOWNLOAD_MAX_RETRIES,
            last_error,
        )
        return None

    async def refresh(
        self, url: str, existing_checksum: str | None = None
    ) -> dict[str, Any]:
        """
        Check for updates on an existing RFP.

        Args:
            url: URL to check
            existing_checksum: Previous scrape checksum

        Returns:
            Dict with change information
        """
        # Re-scrape the page
        updated_rfp = await self.scrape(url)

        # Compare checksums
        has_changes = (
            existing_checksum is None
            or updated_rfp.scrape_checksum != existing_checksum
        )

        result = {
            "has_changes": has_changes,
            "new_checksum": updated_rfp.scrape_checksum,
            "document_count": len(updated_rfp.documents),
            "qa_count": len(updated_rfp.qa_items),
            "updated_rfp": updated_rfp if has_changes else None,
        }

        if has_changes:
            logger.info(f"Changes detected for {url}")
        else:
            logger.info(f"No changes for {url}")

        return result

    def _parse_date(self, date_str: str | None) -> datetime | None:
        """Parse various date formats to datetime."""
        if not date_str:
            return None

        # Common date formats
        formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%m-%d-%Y",
            "%B %d, %Y",
            "%b %d, %Y",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue

        logger.warning(f"Could not parse date: {date_str}")
        return None

    def _parse_amount(self, amount_str: str | None) -> float | None:
        """Parse amount strings to float."""
        if not amount_str:
            return None

        try:
            # Remove currency symbols and commas
            cleaned = amount_str.replace("$", "").replace(",", "").strip()
            # Handle "K" and "M" suffixes
            if cleaned.upper().endswith("K"):
                return float(cleaned[:-1]) * 1000
            elif cleaned.upper().endswith("M"):
                return float(cleaned[:-1]) * 1_000_000
            return float(cleaned)
        except ValueError:
            logger.warning(f"Could not parse amount: {amount_str}")
            return None

    def _classify_document_type(self, doc_type: str, filename: str) -> str:
        """Classify document type based on extracted type and filename."""
        doc_type_lower = (doc_type or "").lower()
        filename_lower = filename.lower()

        if "amendment" in doc_type_lower or "amendment" in filename_lower:
            return "amendment"
        elif (
            "solicitation" in doc_type_lower
            or "rfp" in filename_lower
            or "rfq" in filename_lower
        ):
            return "solicitation"
        elif (
            "q&a" in doc_type_lower
            or "qa" in filename_lower
            or "question" in filename_lower
        ):
            return "qa_response"
        else:
            return "attachment"

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to be filesystem-safe."""
        # Remove or replace unsafe characters
        unsafe_chars = '<>:"/\\|?*'
        safe_name = filename
        for char in unsafe_chars:
            safe_name = safe_name.replace(char, "_")
        return safe_name.strip()
