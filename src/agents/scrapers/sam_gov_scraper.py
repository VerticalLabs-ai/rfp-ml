"""
SAM.gov scraper for importing RFPs from the federal contracting system.

SAM.gov (System for Award Management) is the primary source for federal
government contract opportunities. This scraper supports both:
1. Direct URL scraping using Stagehand AI extraction
2. API access when opportunity IDs can be extracted from URLs
"""

import asyncio
import logging
import os
import re
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


# Pydantic schemas for Stagehand extraction
class SAMMetadataSchema(BaseModel):
    """Schema for SAM.gov RFP metadata extraction."""

    title: str | None = None
    solicitation_number: str | None = Field(default=None, alias="solicitationNumber")
    notice_id: str | None = Field(default=None, alias="noticeId")
    agency: str | None = None
    sub_agency: str | None = Field(default=None, alias="subAgency")
    office: str | None = None
    description: str | None = None
    posted_date: str | None = Field(default=None, alias="postedDate")
    response_deadline: str | None = Field(default=None, alias="responseDeadline")
    archive_date: str | None = Field(default=None, alias="archiveDate")
    award_amount: str | None = Field(default=None, alias="awardAmount")
    naics_code: str | None = Field(default=None, alias="naicsCode")
    psc_code: str | None = Field(default=None, alias="pscCode")
    set_aside_type: str | None = Field(default=None, alias="setAsideType")
    classification_code: str | None = Field(default=None, alias="classificationCode")
    place_of_performance: str | None = Field(default=None, alias="placeOfPerformance")
    point_of_contact: str | None = Field(default=None, alias="pointOfContact")
    contact_email: str | None = Field(default=None, alias="contactEmail")
    notice_type: str | None = Field(default=None, alias="noticeType")

    model_config = {"populate_by_name": True}


class SAMDocumentSchema(BaseModel):
    """Schema for SAM.gov document item."""

    filename: str
    url: str
    type: str | None = None
    posted_date: str | None = Field(default=None, alias="postedDate")


class SAMDocumentsListSchema(BaseModel):
    """Schema for SAM.gov documents list."""

    documents: list[SAMDocumentSchema] = []


class SAMGovScraper(BaseScraper):
    """
    Scraper for SAM.gov (System for Award Management) federal opportunities.

    Handles URLs from:
    - sam.gov/opp/{opportunity_id}/view
    - beta.sam.gov/opp/{opportunity_id}/view
    - sam.gov contract opportunities search results

    Uses Stagehand with Browserbase for AI-powered extraction.
    """

    PLATFORM_NAME = "sam.gov"
    SUPPORTED_DOMAINS = ["sam.gov", "beta.sam.gov", "www.sam.gov"]

    # Configuration
    DOWNLOAD_TIMEOUT_SECONDS = 60
    DOWNLOAD_MAX_RETRIES = 3
    DOWNLOAD_RETRY_DELAY_SECONDS = 2

    def __init__(
        self,
        document_storage_path: str = "data/rfp_documents",
        browserbase_project_id: str | None = None,
        browserbase_api_key: str | None = None,
        model_api_key: str | None = None,
        sam_api_key: str | None = None,
    ):
        """
        Initialize SAM.gov scraper.

        Args:
            document_storage_path: Base path for storing downloaded documents
            browserbase_project_id: Browserbase project ID
            browserbase_api_key: Browserbase API key
            model_api_key: LLM API key for Stagehand
            sam_api_key: SAM.gov API key (optional, for API access)
        """
        super().__init__(document_storage_path)

        self.browserbase_project_id = browserbase_project_id or os.getenv(
            "BROWSERBASE_PROJECT_ID", ""
        )
        self.browserbase_api_key = browserbase_api_key or os.getenv(
            "BROWSERBASE_API_KEY", ""
        )
        self.model_api_key = model_api_key or os.getenv("OPENAI_API_KEY", "")
        self.sam_api_key = sam_api_key or os.getenv("SAM_API_KEY", "")

        if not self.browserbase_api_key:
            logger.warning("Browserbase API key not configured.")
        if not self.model_api_key:
            logger.warning("Model API key not configured.")

    def _to_dict(self, data: Any) -> dict:
        """Convert Stagehand result to dict."""
        if isinstance(data, dict):
            return data
        if hasattr(data, "model_dump"):
            return data.model_dump()
        if hasattr(data, "dict"):
            return data.dict()
        return {}

    def _extract_opportunity_id(self, url: str) -> str | None:
        """
        Extract opportunity ID from SAM.gov URL.

        Patterns:
        - https://sam.gov/opp/{id}/view
        - https://beta.sam.gov/opp/{id}/view
        - https://sam.gov/api/prod/opportunities/v1/{id}

        Args:
            url: SAM.gov URL

        Returns:
            Opportunity ID or None
        """
        patterns = [
            r"/opp/([a-f0-9-]+)/view",
            r"/opportunities/v1/([a-f0-9-]+)",
            r"opportunityId=([a-f0-9-]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    async def _create_stagehand_session(self) -> Any:
        """Create a Stagehand browser session."""
        try:
            from stagehand import Stagehand

            stagehand = Stagehand(
                env="BROWSERBASE",
                api_key=self.browserbase_api_key,
                project_id=self.browserbase_project_id,
                model_api_key=self.model_api_key,
                verbose=1,
            )

            await stagehand.init()
            logger.info("Stagehand session initialized for SAM.gov")
            return stagehand

        except ImportError as err:
            logger.error("Stagehand package not installed")
            raise ScraperError("Stagehand package not installed") from err
        except Exception as e:
            logger.error("Failed to create Stagehand session: %s", e)
            raise ScraperConnectionError(f"Failed to connect: {e}") from e

    async def scrape(self, url: str) -> ScrapedRFP:
        """
        Scrape RFP data from a SAM.gov URL.

        Uses Stagehand AI extraction to handle SAM.gov's dynamic pages.

        Args:
            url: SAM.gov opportunity URL

        Returns:
            ScrapedRFP with extracted data
        """
        if not self.is_valid_url(url):
            raise ValueError(f"URL not supported by SAM.gov scraper: {url}")

        logger.info("Scraping SAM.gov URL: %s", url)
        stagehand = None

        try:
            stagehand = await self._create_stagehand_session()
            page = stagehand.page

            # Navigate to the URL
            await page.goto(url)
            await asyncio.sleep(3)  # SAM.gov has slow dynamic loading

            # Extract metadata
            rfp_data = await self._extract_metadata(stagehand)

            # Extract documents
            documents = await self._extract_documents(stagehand, url)

            # SAM.gov typically doesn't have Q&A on the main page
            qa_items: list[ScrapedQA] = []

            # Build the ScrapedRFP
            scraped_rfp = ScrapedRFP(
                source_url=url,
                source_platform=self.PLATFORM_NAME,
                title=self._get_field(rfp_data, "title") or "Untitled SAM.gov Opportunity",
                solicitation_number=self._get_field(rfp_data, "solicitation_number")
                or self._get_field(rfp_data, "notice_id"),
                description=self._get_field(rfp_data, "description"),
                agency=self._get_field(rfp_data, "agency"),
                office=self._get_field(rfp_data, "office")
                or self._get_field(rfp_data, "sub_agency"),
                posted_date=self._parse_date(self._get_field(rfp_data, "posted_date")),
                response_deadline=self._parse_date(
                    self._get_field(rfp_data, "response_deadline")
                ),
                award_amount=self._parse_amount(self._get_field(rfp_data, "award_amount")),
                naics_code=self._get_field(rfp_data, "naics_code"),
                category=self._get_field(rfp_data, "notice_type")
                or self._classify_by_naics(self._get_field(rfp_data, "naics_code")),
                documents=documents,
                qa_items=qa_items,
                raw_data=rfp_data,
            )

            scraped_rfp.compute_checksum()
            logger.info("Successfully scraped SAM.gov opportunity: %s", scraped_rfp.title)
            return scraped_rfp

        except Exception as e:
            logger.error("Error scraping SAM.gov URL %s: %s", url, e)
            raise ScraperParseError(f"Failed to scrape SAM.gov: {e}") from e

        finally:
            if stagehand:
                try:
                    await stagehand.close()
                except Exception as e:
                    logger.warning("Error closing Stagehand: %s", e)

    def _get_field(self, data: dict, snake_key: str) -> Any:
        """Get field with snake_case or camelCase fallback."""
        if not data:
            return None

        value = data.get(snake_key)
        if value:
            return value

        parts = snake_key.split("_")
        camel_key = parts[0] + "".join(p.capitalize() for p in parts[1:])
        return data.get(camel_key)

    async def _extract_metadata(self, stagehand: Any) -> dict[str, Any]:
        """Extract RFP metadata from SAM.gov page."""
        try:
            from stagehand import ExtractOptions

            result = await stagehand.page.extract(
                ExtractOptions(
                    instruction="""Extract the contract opportunity information from this SAM.gov page.

Find and extract ALL available fields:

IDENTIFIERS:
- title: The opportunity title
- solicitation_number: The solicitation number (may be labeled "Sol#", "Solicitation Number", or "Reference Number")
- notice_id: The SAM.gov Notice ID

ORGANIZATION:
- agency: The federal agency (e.g., "Department of Defense", "GSA")
- sub_agency: Sub-agency or component (e.g., "U.S. Army", "U.S. Navy")
- office: The contracting office

DETAILS:
- description: The full description or synopsis
- notice_type: Type of notice (Solicitation, Pre-solicitation, Award, etc.)

DATES:
- posted_date: When the notice was posted
- response_deadline: Response/Proposal due date (look for "Response Date", "Offers Due", "Closing Date")
- archive_date: When the notice will be archived

CLASSIFICATION:
- naics_code: NAICS code (6-digit number)
- psc_code: Product Service Code
- set_aside_type: Any set-aside (Small Business, 8(a), HUBZone, etc.)
- classification_code: Classification code if shown

LOCATION:
- place_of_performance: Where work will be performed

CONTACT:
- point_of_contact: POC name
- contact_email: POC email address

Look in the main content area, header section, and any expandable sections.
                    """,
                    schema_definition=SAMMetadataSchema,
                )
            )

            data = result.data if hasattr(result, "data") else result
            data = self._to_dict(data)
            logger.info("Extracted SAM.gov metadata: %s", list(data.keys()))
            return data

        except Exception as e:
            logger.error("Error extracting SAM.gov metadata: %s", e)
            return {}

    async def _extract_documents(
        self, stagehand: Any, base_url: str
    ) -> list[ScrapedDocument]:
        """Extract document links from SAM.gov page."""
        try:
            from stagehand import ExtractOptions

            # Try to expand/navigate to attachments section
            try:
                await stagehand.page.act(
                    "Click on 'Attachments' or 'Documents' tab or section if visible"
                )
                await asyncio.sleep(1)
            except Exception:
                logger.debug("No attachments tab found")

            result = await stagehand.page.extract(
                ExtractOptions(
                    instruction="""Find all downloadable documents and attachments on this SAM.gov page.

Look for:
- Attachments section
- Documents table
- Download links for PDFs, Word docs, Excel files
- Amendment documents
- Solicitation documents
- Any other downloadable files

For each document extract:
- filename: The document name
- url: The download URL (href attribute)
- type: Document type (solicitation, amendment, attachment, etc.)
- posted_date: When it was posted if shown

SAM.gov documents are often in a table or list format.
                    """,
                    schema_definition=SAMDocumentsListSchema,
                )
            )

            documents = []
            data = result.data if hasattr(result, "data") else result
            data = self._to_dict(data)
            doc_list = data.get("documents", [])

            logger.info("Found %d documents on SAM.gov", len(doc_list))

            for doc in doc_list:
                filename = doc.get("filename", "unknown")
                file_ext = Path(filename).suffix.lower().lstrip(".")
                raw_url = doc.get("url", "")

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
            logger.error("Error extracting SAM.gov documents: %s", e)
            return []

    def _resolve_document_url(self, url: str, base_url: str) -> str | None:
        """Resolve document URL."""
        if not url:
            return None

        url = url.strip()

        if url in ["#", "javascript:void(0)", "javascript:;", ""]:
            return None

        if url.startswith("mailto:") or url.startswith("tel:"):
            return None

        parsed = urlparse(url)
        if parsed.scheme in ("http", "https"):
            return url

        try:
            resolved = urljoin(base_url, url)
            parsed_resolved = urlparse(resolved)
            if parsed_resolved.scheme in ("http", "https") and parsed_resolved.netloc:
                return resolved
        except Exception as e:
            logger.warning("Failed to resolve URL %s: %s", url, e)

        return None

    def _classify_by_naics(self, naics_code: str | None) -> str | None:
        """Classify category based on NAICS code."""
        if not naics_code:
            return None

        # First 2 digits indicate sector
        try:
            sector = naics_code[:2]
            naics_categories = {
                "23": "Construction",
                "33": "Manufacturing",
                "42": "Wholesale Trade",
                "48": "Transportation",
                "51": "Information Technology",
                "52": "Finance",
                "53": "Real Estate",
                "54": "Professional Services",
                "55": "Management",
                "56": "Administrative Services",
                "61": "Education",
                "62": "Healthcare",
                "71": "Arts & Recreation",
                "72": "Accommodation & Food",
                "81": "Other Services",
                "92": "Public Administration",
            }
            return naics_categories.get(sector)
        except Exception:
            return None

    async def download_documents(
        self, rfp: ScrapedRFP, rfp_id: str
    ) -> list[ScrapedDocument]:
        """Download documents from SAM.gov."""
        storage_path = self.get_document_storage_path(rfp_id)
        downloaded_docs = []

        if not rfp.documents:
            logger.info("No documents to download for SAM.gov RFP %s", rfp_id)
            return downloaded_docs

        logger.info(
            "Downloading %d documents from SAM.gov for RFP %s",
            len(rfp.documents),
            rfp_id,
        )

        timeout = ClientTimeout(total=self.DOWNLOAD_TIMEOUT_SECONDS)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for doc in rfp.documents:
                if not doc.source_url:
                    continue

                downloaded = await self._download_single_document(
                    session, doc, storage_path
                )
                if downloaded:
                    downloaded_docs.append(downloaded)

        logger.info(
            "Downloaded %d/%d SAM.gov documents for RFP %s",
            len(downloaded_docs),
            len(rfp.documents),
            rfp_id,
        )
        return downloaded_docs

    async def _download_single_document(
        self, session: aiohttp.ClientSession, doc: ScrapedDocument, storage_path: Path
    ) -> ScrapedDocument | None:
        """Download a single document with retry logic."""
        if not doc.source_url or not doc.source_url.startswith(("http://", "https://")):
            return None

        last_error = None

        for attempt in range(1, self.DOWNLOAD_MAX_RETRIES + 1):
            try:
                logger.info(
                    "Downloading SAM.gov doc (attempt %d/%d): %s",
                    attempt,
                    self.DOWNLOAD_MAX_RETRIES,
                    doc.filename,
                )

                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/pdf,application/msword,*/*",
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

                        logger.info("Downloaded: %s (%d bytes)", safe_filename, doc.file_size)
                        return doc

                    last_error = ScraperDownloadError(f"HTTP {response.status}")

            except asyncio.TimeoutError:
                last_error = ScraperDownloadError("Timeout")
            except aiohttp.ClientError as e:
                last_error = e
            except Exception as e:
                last_error = e
                break

            if attempt < self.DOWNLOAD_MAX_RETRIES:
                await asyncio.sleep(self.DOWNLOAD_RETRY_DELAY_SECONDS)

        logger.error("Failed to download %s: %s", doc.filename, last_error)
        return None

    async def refresh(
        self, url: str, existing_checksum: str | None = None
    ) -> dict[str, Any]:
        """Check for updates on an existing SAM.gov opportunity."""
        updated_rfp = await self.scrape(url)

        has_changes = (
            existing_checksum is None
            or updated_rfp.scrape_checksum != existing_checksum
        )

        return {
            "has_changes": has_changes,
            "new_checksum": updated_rfp.scrape_checksum,
            "document_count": len(updated_rfp.documents),
            "qa_count": len(updated_rfp.qa_items),
            "updated_rfp": updated_rfp,
        }

    def _parse_date(self, date_str: str | None) -> datetime | None:
        """Parse SAM.gov date formats."""
        if not date_str:
            return None

        try:
            from dateutil import parser as date_parser

            parsed = date_parser.parse(date_str, fuzzy=True)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except Exception:
            pass

        # Manual parsing for common SAM.gov formats
        formats = [
            "%b %d, %Y",  # Dec 15, 2024
            "%B %d, %Y",  # December 15, 2024
            "%m/%d/%Y",  # 12/15/2024
            "%Y-%m-%d",  # 2024-12-15
            "%b %d, %Y %I:%M %p",  # Dec 15, 2024 2:00 PM
        ]

        for fmt in formats:
            try:
                parsed = datetime.strptime(date_str.strip(), fmt)
                return parsed.replace(tzinfo=timezone.utc)
            except ValueError:
                continue

        logger.warning("Could not parse SAM.gov date: %s", date_str)
        return None

    def _parse_amount(self, amount_str: str | None) -> float | None:
        """Parse amount strings."""
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
            return None

    def _classify_document_type(self, doc_type: str, filename: str) -> str:
        """Classify document type."""
        doc_type_lower = (doc_type or "").lower()
        filename_lower = filename.lower()

        if "amendment" in doc_type_lower or "amendment" in filename_lower:
            return "amendment"
        elif "solicitation" in doc_type_lower or "sol" in filename_lower:
            return "solicitation"
        elif "q&a" in doc_type_lower or "qa" in filename_lower:
            return "qa_response"
        else:
            return "attachment"

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename."""
        unsafe_chars = '<>:"/\\|?*'
        safe_name = filename
        for char in unsafe_chars:
            safe_name = safe_name.replace(char, "_")
        return safe_name.strip()
