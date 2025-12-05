"""
Generic web scraper for importing RFPs from any government website.
Uses Stagehand's AI-powered extraction to handle unknown page structures.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import aiofiles
import aiohttp
from aiohttp import ClientTimeout
from pydantic import BaseModel, Field

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


# Pydantic schemas for Stagehand extraction validation
class GenericRFPMetadataSchema(BaseModel):
    """Schema for generic RFP metadata extraction."""

    title: str | None = None
    solicitation_number: str | None = Field(default=None, alias="solicitationNumber")
    agency: str | None = None
    office: str | None = None
    department: str | None = None
    description: str | None = None
    posted_date: str | None = Field(default=None, alias="postedDate")
    response_deadline: str | None = Field(default=None, alias="responseDeadline")
    close_date: str | None = Field(default=None, alias="closeDate")
    award_date: str | None = Field(default=None, alias="awardDate")
    award_amount: str | None = Field(default=None, alias="awardAmount")
    estimated_value: str | None = Field(default=None, alias="estimatedValue")
    naics_code: str | None = Field(default=None, alias="naicsCode")
    psc_code: str | None = Field(default=None, alias="pscCode")
    set_aside_type: str | None = Field(default=None, alias="setAsideType")
    category: str | None = None
    contract_type: str | None = Field(default=None, alias="contractType")
    place_of_performance: str | None = Field(default=None, alias="placeOfPerformance")
    point_of_contact: str | None = Field(default=None, alias="pointOfContact")
    contact_email: str | None = Field(default=None, alias="contactEmail")
    contact_phone: str | None = Field(default=None, alias="contactPhone")

    model_config = {"populate_by_name": True}


class GenericDocumentItemSchema(BaseModel):
    """Schema for individual document item."""

    filename: str
    url: str
    type: str | None = None
    description: str | None = None


class GenericDocumentsListSchema(BaseModel):
    """Schema for documents list extraction."""

    documents: list[GenericDocumentItemSchema] = []


class GenericQAItemSchema(BaseModel):
    """Schema for individual Q&A item."""

    question_number: str | None = Field(default=None, alias="questionNumber")
    question: str
    answer: str | None = None
    asked_date: str | None = Field(default=None, alias="askedDate")
    answered_date: str | None = Field(default=None, alias="answeredDate")
    category: str | None = None

    model_config = {"populate_by_name": True}


class GenericQAListSchema(BaseModel):
    """Schema for Q&A list extraction."""

    qa_items: list[GenericQAItemSchema] = Field(default=[], alias="qaItems")

    model_config = {"populate_by_name": True}


class GenericWebScraper(BaseScraper):
    """
    Generic scraper for any government RFP website.

    Uses Stagehand with Browserbase for AI-powered extraction.
    Works with unknown page layouts by using LLM understanding.
    This is the fallback scraper when no platform-specific scraper matches.
    """

    PLATFORM_NAME = "generic"
    SUPPORTED_DOMAINS: list[str] = []  # Empty = accepts any domain as fallback

    # Configuration constants
    DOWNLOAD_TIMEOUT_SECONDS = 60
    DOWNLOAD_MAX_RETRIES = 3
    DOWNLOAD_RETRY_DELAY_SECONDS = 2

    def __init__(
        self,
        document_storage_path: str = "data/rfp_documents",
        browserbase_project_id: str | None = None,
        browserbase_api_key: str | None = None,
        model_api_key: str | None = None,
    ):
        """
        Initialize Generic Web scraper.

        Args:
            document_storage_path: Base path for storing downloaded documents
            browserbase_project_id: Browserbase project ID (or from env BROWSERBASE_PROJECT_ID)
            browserbase_api_key: Browserbase API key (or from env BROWSERBASE_API_KEY)
            model_api_key: LLM API key for Stagehand (or from env OPENAI_API_KEY)
        """
        super().__init__(document_storage_path)

        self.browserbase_project_id = browserbase_project_id or os.getenv(
            "BROWSERBASE_PROJECT_ID", ""
        )
        self.browserbase_api_key = browserbase_api_key or os.getenv(
            "BROWSERBASE_API_KEY", ""
        )
        self.model_api_key = model_api_key or os.getenv("OPENAI_API_KEY", "")

        if not self.browserbase_api_key:
            logger.warning("Browserbase API key not configured. Scraping may fail.")
        if not self.model_api_key:
            logger.warning(
                "Model API key not configured. Stagehand AI features may fail."
            )

    def is_valid_url(self, url: str) -> bool:
        """
        Accept any HTTP/HTTPS URL as fallback scraper.

        This scraper is designed to work with any government website.

        Args:
            url: URL to validate

        Returns:
            True if URL uses HTTP or HTTPS scheme
        """
        try:
            parsed = urlparse(url)
            return parsed.scheme in ("http", "https") and bool(parsed.netloc)
        except Exception:
            return False

    def _to_dict(self, data: Any) -> dict:
        """
        Convert Stagehand extraction result to dict.

        Stagehand may return data as a Pydantic model instance instead of a dict.
        This helper ensures we always get a dict for processing.
        """
        if isinstance(data, dict):
            return data
        if hasattr(data, "model_dump"):  # Pydantic v2
            return data.model_dump()
        if hasattr(data, "dict"):  # Pydantic v1
            return data.dict()
        return {}

    async def _create_stagehand_session(self) -> Any:
        """
        Create a Stagehand browser session using Browserbase.

        Returns:
            Stagehand instance with browser session
        """
        try:
            from stagehand import Stagehand

            stagehand = Stagehand(
                env="BROWSERBASE",
                api_key=self.browserbase_api_key,
                project_id=self.browserbase_project_id,
                model_api_key=self.model_api_key,
                verbose=1,  # 0=quiet, 1=info, 2=debug
            )

            await stagehand.init()
            logger.info("Stagehand session initialized with Browserbase")
            return stagehand

        except ImportError as err:
            logger.error("Stagehand package not installed. Run: pip install stagehand")
            raise ScraperError("Stagehand package not installed") from err
        except Exception as e:
            logger.error("Failed to create Stagehand session: %s", e)
            raise ScraperConnectionError(
                f"Failed to connect to Browserbase: {e}"
            ) from e

    async def scrape(self, url: str) -> ScrapedRFP:
        """
        Scrape RFP data from any government website URL.

        Uses AI-powered extraction to handle unknown page structures.

        Args:
            url: Any HTTP/HTTPS URL for a government RFP

        Returns:
            ScrapedRFP with extracted data
        """
        if not self.is_valid_url(url):
            raise ValueError(f"Invalid URL: {url}")

        logger.info("Scraping URL with GenericWebScraper: %s", url)
        stagehand = None

        try:
            stagehand = await self._create_stagehand_session()
            page = stagehand.page

            # Navigate to the URL
            await page.goto(url)
            await asyncio.sleep(3)  # Wait for dynamic content

            # Extract RFP metadata using Stagehand's AI extraction
            rfp_data = await self._extract_rfp_metadata(stagehand)

            # Extract documents with base URL for resolving relative links
            documents = await self._extract_documents(stagehand, url)

            # Extract Q&A (if present)
            qa_items = await self._extract_qa(stagehand)

            # Detect platform from URL for source_platform field
            detected_platform = self._detect_platform(url)

            # Build the ScrapedRFP
            scraped_rfp = ScrapedRFP(
                source_url=url,
                source_platform=detected_platform,
                title=self._get_field(rfp_data, "title") or "Untitled RFP",
                solicitation_number=self._get_field(rfp_data, "solicitation_number"),
                description=self._get_field(rfp_data, "description"),
                agency=self._get_field(rfp_data, "agency"),
                office=self._get_field(rfp_data, "office") or self._get_field(rfp_data, "department"),
                posted_date=self._parse_date(self._get_field(rfp_data, "posted_date")),
                response_deadline=self._parse_date(
                    self._get_field(rfp_data, "response_deadline")
                    or self._get_field(rfp_data, "close_date")
                ),
                award_amount=self._parse_amount(self._get_field(rfp_data, "award_amount")),
                estimated_value=self._parse_amount(self._get_field(rfp_data, "estimated_value")),
                naics_code=self._get_field(rfp_data, "naics_code"),
                category=self._get_field(rfp_data, "category"),
                documents=documents,
                qa_items=qa_items,
                raw_data=rfp_data,
            )

            scraped_rfp.compute_checksum()
            logger.info("Successfully scraped RFP: %s", scraped_rfp.title)
            return scraped_rfp

        except Exception as e:
            logger.error("Error scraping URL %s: %s", url, e)
            raise ScraperParseError(f"Failed to scrape: {e}") from e

        finally:
            if stagehand:
                try:
                    await stagehand.close()
                except Exception as e:
                    logger.warning("Error closing Stagehand session: %s", e)

    def _detect_platform(self, url: str) -> str:
        """
        Detect the platform from the URL domain.

        Args:
            url: The source URL

        Returns:
            Platform name string
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Known government platforms
            if "sam.gov" in domain:
                return "sam.gov"
            elif "beaconbid.com" in domain:
                return "beaconbid"
            elif "fbo.gov" in domain:
                return "fbo.gov"
            elif "govwin" in domain:
                return "govwin"
            elif "grants.gov" in domain:
                return "grants.gov"
            elif "ebuy" in domain:
                return "ebuy"
            elif ".gov" in domain:
                # Generic government domain
                return domain.replace("www.", "")
            else:
                return "generic"
        except Exception:
            return "generic"

    def _get_field(self, data: dict, snake_key: str) -> Any:
        """
        Get field value with fallback to camelCase key.

        Args:
            data: Dictionary to extract from
            snake_key: The snake_case key name

        Returns:
            Field value or None
        """
        if not data:
            return None

        # Try snake_case first
        value = data.get(snake_key)
        if value:
            return value

        # Convert snake_case to camelCase and try that
        parts = snake_key.split("_")
        camel_key = parts[0] + "".join(p.capitalize() for p in parts[1:])
        return data.get(camel_key)

    async def _extract_rfp_metadata(self, stagehand: Any) -> dict[str, Any]:
        """
        Extract RFP metadata using Stagehand's AI extraction.

        Uses comprehensive prompts designed for various government RFP formats.

        Args:
            stagehand: Active Stagehand session

        Returns:
            Dict with extracted metadata
        """
        try:
            from stagehand import ExtractOptions

            result = await stagehand.page.extract(
                ExtractOptions(
                    instruction="""Extract the RFP (Request for Proposal) or solicitation information from this page.

This is a government contracting opportunity page. Find and extract ALL available information:

REQUIRED FIELDS:
- title: The main title/name of the solicitation or opportunity
- solicitation_number: The official solicitation, RFP, RFQ, or IFB number (may be labeled as Notice ID, Reference Number, etc.)
- agency: The government agency or organization posting this (e.g., Department of Defense, GSA, State agencies)
- description: A summary or description of what the RFP is for

DATES (look for various labels):
- posted_date: When posted/published/issued (look for "Posted", "Published", "Issue Date", "Release Date")
- response_deadline: When proposals/bids are due (look for "Due Date", "Deadline", "Closing Date", "Response Due", "Offer Due", "Submission Deadline"). Include full date AND time with timezone if shown.
- award_date: Anticipated award date if shown

CLASSIFICATION:
- naics_code: Any NAICS code (6-digit industry code)
- psc_code: Product Service Code if shown
- category: The category or type (IT Services, Construction, Professional Services, etc.)
- set_aside_type: Any set-aside designation (Small Business, 8(a), HUBZone, SDVOSB, WOSB, etc.)

FINANCIAL:
- award_amount: Contract value, award amount, or ceiling if shown
- estimated_value: Estimated contract value

CONTACT INFO:
- point_of_contact: Name of the contracting officer or POC
- contact_email: Email address for questions
- contact_phone: Phone number

LOCATION:
- office: Specific office or department within the agency
- place_of_performance: Where work will be performed

Look thoroughly - government pages often have information in tables, sidebars, or collapsed sections.
                    """,
                    schema_definition=GenericRFPMetadataSchema,
                )
            )

            data = result.data if hasattr(result, "data") else result
            data = self._to_dict(data)
            logger.info("Extracted metadata fields: %s", list(data.keys()))
            return data

        except Exception as e:
            logger.error("Error extracting metadata: %s", e)
            return {}

    async def _extract_documents(
        self, stagehand: Any, base_url: str
    ) -> list[ScrapedDocument]:
        """
        Extract document links from the RFP page.

        Args:
            stagehand: Active Stagehand session
            base_url: Base URL for resolving relative links

        Returns:
            List of ScrapedDocument objects (not downloaded yet)
        """
        try:
            from stagehand import ExtractOptions

            result = await stagehand.page.extract(
                ExtractOptions(
                    instruction="""Find all downloadable documents and attachments on this page.

Look for:
- PDF documents (solicitation, amendments, attachments)
- Word documents (.doc, .docx)
- Excel files (.xls, .xlsx)
- ZIP archives
- Any other downloadable files

For each document found, extract:
- filename: The visible name/label of the file
- url: The ACTUAL href/download link URL (must be unique per document)
- type: Document type (solicitation, amendment, attachment, specification, pricing, etc.)
- description: Any description or notes about the document

IMPORTANT:
1. Each document has a UNIQUE download URL - extract the exact href attribute
2. Look in tables, lists, attachment sections, and download areas
3. Some pages have document tabs or accordion sections - check those too
4. Don't include navigation links, only actual document downloads
                    """,
                    schema_definition=GenericDocumentsListSchema,
                )
            )

            documents = []
            data = result.data if hasattr(result, "data") else result
            data = self._to_dict(data)
            doc_list = data.get("documents", [])

            logger.info("Found %d document links", len(doc_list))

            for doc in doc_list:
                filename = doc.get("filename", "unknown")
                file_ext = Path(filename).suffix.lower().lstrip(".")
                raw_url = doc.get("url", "")

                # Resolve the URL
                resolved_url = self._resolve_document_url(raw_url, base_url)

                documents.append(
                    ScrapedDocument(
                        filename=filename,
                        source_url=resolved_url or raw_url,
                        file_type=file_ext if file_ext else None,
                        document_type=self._classify_document_type(
                            doc.get("type", ""), filename
                        ),
                    )
                )

            return documents

        except Exception as e:
            logger.error("Error extracting documents: %s", e)
            return []

    def _resolve_document_url(self, url: str, base_url: str) -> str | None:
        """
        Resolve and validate a document URL.

        Args:
            url: The extracted URL (may be relative or absolute)
            base_url: The base URL for resolving relative URLs

        Returns:
            Resolved absolute URL or None if invalid
        """
        if not url:
            return None

        url = url.strip()

        # Skip invalid/placeholder URLs
        if url in ["#", "javascript:void(0)", "javascript:;", ""]:
            return None

        if url.startswith("mailto:") or url.startswith("tel:"):
            return None

        # Check if already absolute
        parsed = urlparse(url)
        if parsed.scheme in ("http", "https"):
            return url

        # Resolve relative URL
        try:
            resolved = urljoin(base_url, url)
            parsed_resolved = urlparse(resolved)
            if parsed_resolved.scheme in ("http", "https") and parsed_resolved.netloc:
                return resolved
        except Exception as e:
            logger.warning("Failed to resolve URL %s: %s", url, e)

        return None

    async def _extract_qa(self, stagehand: Any) -> list[ScrapedQA]:
        """
        Extract Q&A entries from the RFP page.

        Many government sites have Q&A or amendment sections.

        Args:
            stagehand: Active Stagehand session

        Returns:
            List of ScrapedQA objects
        """
        try:
            from stagehand import ExtractOptions

            # Try to find and click Q&A tab/section if it exists
            try:
                await stagehand.page.act(
                    "Click on any Q&A, Questions, FAQs, or Clarifications tab or section if visible"
                )
                await asyncio.sleep(1)
            except Exception:
                logger.debug("No Q&A tab found, checking current page content")

            result = await stagehand.page.extract(
                ExtractOptions(
                    instruction="""Find all Questions and Answers (Q&A), clarifications, or FAQs on this page.

These are typically vendor questions about the RFP with official answers.

For each Q&A entry, extract:
- question_number: The question number if shown (Q1, Q2, #1, etc.)
- question: The full question text
- answer: The answer text (may be empty if not yet answered)
- asked_date: When the question was submitted
- answered_date: When it was answered
- category: Category if shown (technical, pricing, scope, etc.)

Look for:
- Q&A sections or tabs
- Amendment documents with Q&A
- Clarification logs
- FAQ sections
                    """,
                    schema_definition=GenericQAListSchema,
                )
            )

            qa_items = []
            data = result.data if hasattr(result, "data") else result
            data = self._to_dict(data)
            qa_list = data.get("qaItems", []) or data.get("qa_items", [])

            for qa in qa_list:
                question = qa.get("question") or qa.get("questionText") or ""
                if question:
                    qa_items.append(
                        ScrapedQA(
                            question_number=qa.get("question_number") or qa.get("questionNumber"),
                            question_text=question,
                            answer_text=qa.get("answer") or qa.get("answerText"),
                            asked_date=self._parse_date(
                                qa.get("asked_date") or qa.get("askedDate")
                            ),
                            answered_date=self._parse_date(
                                qa.get("answered_date") or qa.get("answeredDate")
                            ),
                        )
                    )

            logger.info("Found %d Q&A items", len(qa_items))
            return qa_items

        except Exception as e:
            logger.error("Error extracting Q&A: %s", e)
            return []

    async def download_documents(
        self, rfp: ScrapedRFP, rfp_id: str
    ) -> list[ScrapedDocument]:
        """
        Download all documents for an RFP.

        For generic sites, try direct HTTP download first (most gov sites allow this).
        Fall back to browser-based download if needed.

        Args:
            rfp: ScrapedRFP containing document info
            rfp_id: Unique ID for organizing storage

        Returns:
            List of ScrapedDocument with local file paths
        """
        storage_path = self.get_document_storage_path(rfp_id)
        downloaded_docs = []

        if not rfp.documents:
            logger.info("No documents to download for RFP %s", rfp_id)
            return downloaded_docs

        logger.info("Downloading %d documents for RFP %s", len(rfp.documents), rfp_id)

        # Try direct HTTP download (works for most government sites)
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

        logger.info(
            "Downloaded %d/%d documents for RFP %s",
            len(downloaded_docs),
            len(rfp.documents),
            rfp_id,
        )
        return downloaded_docs

    async def _download_single_document(
        self, session: aiohttp.ClientSession, doc: ScrapedDocument, storage_path: Path
    ) -> ScrapedDocument | None:
        """Download a single document with retry logic."""
        last_error: Exception | None = None

        if not doc.source_url or not doc.source_url.startswith(("http://", "https://")):
            logger.error(f"Invalid document URL: {doc.source_url} for {doc.filename}")
            return None

        for attempt in range(1, self.DOWNLOAD_MAX_RETRIES + 1):
            try:
                logger.info(
                    "Downloading (attempt %d/%d): %s",
                    attempt,
                    self.DOWNLOAD_MAX_RETRIES,
                    doc.filename,
                )

                # Add headers to mimic browser request
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/pdf,application/msword,application/vnd.openxmlformats-officedocument.*,*/*",
                }

                async with session.get(doc.source_url, headers=headers) as response:
                    if response.status == 200:
                        safe_filename = self._sanitize_filename(doc.filename)
                        file_path = storage_path / safe_filename

                        content = await response.read()
                        async with aiofiles.open(file_path, "wb") as f:
                            await f.write(content)

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
                last_error = ScraperDownloadError("Timeout")
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
                break

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
        updated_rfp = await self.scrape(url)

        has_changes = (
            existing_checksum is None
            or updated_rfp.scrape_checksum != existing_checksum
        )

        result = {
            "has_changes": has_changes,
            "new_checksum": updated_rfp.scrape_checksum,
            "document_count": len(updated_rfp.documents),
            "qa_count": len(updated_rfp.qa_items),
            "updated_rfp": updated_rfp,
        }

        if has_changes:
            logger.info("Changes detected for %s", url)
        else:
            logger.info("No changes for %s", url)

        return result

    def _parse_date(self, date_str: str | None) -> datetime | None:
        """
        Parse various date formats to timezone-aware datetime.

        Handles many formats found on government sites.

        Args:
            date_str: Date string in various formats

        Returns:
            timezone-aware datetime (UTC if no timezone specified)
        """
        if not date_str:
            return None

        # Try dateutil.parser first (handles most formats)
        try:
            from dateutil import parser as date_parser

            parsed = date_parser.parse(date_str, fuzzy=True, default=None)
            if parsed:
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed
        except ImportError:
            logger.debug("dateutil not available, using manual parsing")
        except (ValueError, TypeError) as e:
            logger.debug("dateutil parsing failed: %s, trying manual", e)

        # Manual parsing fallback
        cleaned = date_str.strip()
        detected_tz = None

        tz_map = {
            "CST": timezone(timedelta(hours=-6)),
            "CDT": timezone(timedelta(hours=-5)),
            "EST": timezone(timedelta(hours=-5)),
            "EDT": timezone(timedelta(hours=-4)),
            "PST": timezone(timedelta(hours=-8)),
            "PDT": timezone(timedelta(hours=-7)),
            "MST": timezone(timedelta(hours=-7)),
            "MDT": timezone(timedelta(hours=-6)),
            "UTC": timezone.utc,
            "GMT": timezone.utc,
        }

        for tz_abbr, tz_obj in tz_map.items():
            if cleaned.endswith(f" {tz_abbr}"):
                detected_tz = tz_obj
                cleaned = cleaned[: -len(tz_abbr) - 1]
                break
            elif cleaned.endswith(tz_abbr):
                detected_tz = tz_obj
                cleaned = cleaned[: -len(tz_abbr)]
                break

        cleaned = cleaned.replace(" at ", " ")

        formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%m-%d-%Y",
            "%B %d, %Y",
            "%b %d, %Y",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%B %d, %Y %I:%M:%S %p",
            "%B %d, %Y %H:%M:%S",
            "%b %d, %Y %I:%M:%S %p",
            "%b %d, %Y %H:%M:%S",
            "%m/%d/%Y %I:%M %p",
            "%m/%d/%Y %H:%M",
        ]

        for fmt in formats:
            try:
                parsed = datetime.strptime(cleaned.strip(), fmt)
                if detected_tz:
                    parsed = parsed.replace(tzinfo=detected_tz)
                else:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed
            except ValueError:
                continue

        logger.warning("Could not parse date: %s", date_str)
        return None

    def _parse_amount(self, amount_str: str | None) -> float | None:
        """Parse amount strings to float."""
        if not amount_str:
            return None

        try:
            cleaned = amount_str.replace("$", "").replace(",", "").strip()
            if cleaned.upper().endswith("K"):
                return float(cleaned[:-1]) * 1000
            elif cleaned.upper().endswith("M"):
                return float(cleaned[:-1]) * 1_000_000
            elif cleaned.upper().endswith("B"):
                return float(cleaned[:-1]) * 1_000_000_000
            return float(cleaned)
        except ValueError:
            logger.warning("Could not parse amount: %s", amount_str)
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
            or "ifb" in filename_lower
        ):
            return "solicitation"
        elif (
            "q&a" in doc_type_lower
            or "qa" in filename_lower
            or "question" in filename_lower
            or "clarification" in filename_lower
        ):
            return "qa_response"
        elif "pricing" in filename_lower or "price" in filename_lower:
            return "pricing"
        elif "specification" in filename_lower or "spec" in filename_lower:
            return "specification"
        else:
            return "attachment"

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to be filesystem-safe."""
        unsafe_chars = '<>:"/\\|?*'
        safe_name = filename
        for char in unsafe_chars:
            safe_name = safe_name.replace(char, "_")
        return safe_name.strip()
