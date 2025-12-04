"""
BeaconBid RFP scraper using Stagehand/Browserbase for AI-powered extraction.

Stagehand is an AI-native browser automation framework that uses LLMs for resilient
web scraping, even when page layouts change.
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
class RFPMetadataSchema(BaseModel):
    """Schema for RFP metadata extraction."""

    title: str | None = None
    solicitation_number: str | None = None
    agency: str | None = None
    office: str | None = None
    description: str | None = None
    posted_date: str | None = None
    response_deadline: str | None = None
    award_amount: str | None = None
    naics_code: str | None = None
    category: str | None = None


class DocumentItemSchema(BaseModel):
    """Schema for individual document item."""

    filename: str
    url: str
    type: str | None = None


class DocumentsListSchema(BaseModel):
    """Schema for documents list extraction."""

    documents: list[DocumentItemSchema] = []


class QAItemSchema(BaseModel):
    """Schema for individual Q&A item."""

    question_number: str | None = Field(default=None, alias="questionNumber")
    question: str
    answer: str | None = None
    asked_date: str | None = Field(default=None, alias="askedDate")
    answered_date: str | None = Field(default=None, alias="answeredDate")

    model_config = {"populate_by_name": True}


class QAListSchema(BaseModel):
    """Schema for Q&A list extraction."""

    qa_items: list[QAItemSchema] = Field(default=[], alias="qaItems")

    model_config = {"populate_by_name": True}


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
        model_api_key: str | None = None,
    ):
        """
        Initialize BeaconBid scraper.

        Args:
            document_storage_path: Base path for storing downloaded documents
            browserbase_project_id: Browserbase project ID (or from env BROWSERBASE_PROJECT_ID)
            browserbase_api_key: Browserbase API key (or from env BROWSERBASE_API_KEY)
            model_api_key: LLM API key for Stagehand (or from env OPENAI_API_KEY)
        """
        super().__init__(document_storage_path)

        self.browserbase_project_id = browserbase_project_id or os.getenv(
            "BROWSERBASE_PROJECT_ID", "80ee6cd7-7ffd-4409-97ca-20d5a466bfdb"
        )
        self.browserbase_api_key = browserbase_api_key or os.getenv(
            "BROWSERBASE_API_KEY", ""
        )
        self.model_api_key = model_api_key or os.getenv("OPENAI_API_KEY", "")

        if not self.browserbase_api_key:
            logger.warning("Browserbase API key not configured. Scraping will fail.")
        if not self.model_api_key:
            logger.warning(
                "Model API key not configured. Stagehand AI features may fail."
            )

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
            # Import stagehand - it's a Python package that wraps the Stagehand SDK
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
        Scrape RFP data from a BeaconBid URL.

        Args:
            url: BeaconBid solicitation URL

        Returns:
            ScrapedRFP with extracted data
        """
        if not self.is_valid_url(url):
            raise ValueError(f"URL not supported by BeaconBid scraper: {url}")

        logger.info("Scraping BeaconBid URL: %s", url)
        stagehand = None

        try:
            stagehand = await self._create_stagehand_session()
            page = stagehand.page

            # Navigate to the URL
            await page.goto(url)
            await asyncio.sleep(2)  # Wait for dynamic content

            # Extract RFP metadata using Stagehand's AI extraction
            rfp_data = await self._extract_rfp_metadata(stagehand)

            # Extract documents with base URL for resolving relative links
            documents = await self._extract_documents(stagehand, url)

            # Extract Q&A
            qa_items = await self._extract_qa(stagehand)

            # Build the ScrapedRFP (handle both snake_case and camelCase keys)
            def get_field(data: dict, snake_key: str, camel_key: str | None = None):
                """Get field value with fallback to camelCase key."""
                if camel_key is None:
                    # Convert snake_case to camelCase
                    parts = snake_key.split("_")
                    camel_key = parts[0] + "".join(p.capitalize() for p in parts[1:])
                return data.get(snake_key) or data.get(camel_key)

            scraped_rfp = ScrapedRFP(
                source_url=url,
                source_platform=self.PLATFORM_NAME,
                title=rfp_data.get("title", "Untitled RFP"),
                solicitation_number=get_field(rfp_data, "solicitation_number"),
                description=rfp_data.get("description"),
                agency=rfp_data.get("agency"),
                office=rfp_data.get("office"),
                posted_date=self._parse_date(get_field(rfp_data, "posted_date")),
                response_deadline=self._parse_date(
                    get_field(rfp_data, "response_deadline")
                ),
                award_amount=self._parse_amount(get_field(rfp_data, "award_amount")),
                estimated_value=self._parse_amount(
                    get_field(rfp_data, "estimated_value")
                ),
                naics_code=get_field(rfp_data, "naics_code"),
                category=rfp_data.get("category"),
                documents=documents,
                qa_items=qa_items,
                raw_data=rfp_data,
            )

            scraped_rfp.compute_checksum()
            logger.info("Successfully scraped RFP: %s", scraped_rfp.title)
            return scraped_rfp

        except Exception as e:
            logger.error("Error scraping BeaconBid URL %s: %s", url, e)
            raise ScraperParseError(f"Failed to scrape BeaconBid: {e}") from e

        finally:
            if stagehand:
                try:
                    await stagehand.close()
                except Exception as e:
                    logger.warning("Error closing Stagehand session: %s", e)

    async def _extract_rfp_metadata(self, stagehand: Any) -> dict[str, Any]:
        """
        Extract RFP metadata using Stagehand's AI extraction.

        Args:
            stagehand: Active Stagehand session

        Returns:
            Dict with extracted metadata
        """
        try:
            from stagehand import ExtractOptions

            # Use Stagehand page's extract() for AI-powered data extraction
            result = await stagehand.page.extract(
                ExtractOptions(
                    instruction="""Extract the RFP (Request for Proposal) information from this page.
                Find and extract:
                - title: The main title/name of the solicitation
                - solicitation_number: The official solicitation or RFP number
                - agency: The government agency or organization posting this RFP
                - office: The specific office or department (if shown)
                - description: A summary or description of what the RFP is for
                - posted_date: When the RFP was posted/published (look for "Posted", "Published", "Issue Date" labels)
                - response_deadline: The deadline for submitting proposals/bids (look for "Due Date", "Deadline", "Closing Date", "Response Due" labels). Include the full date and time if available.
                - award_amount: Any mentioned contract value or estimated amount
                - naics_code: Any NAICS code mentioned
                - category: The category or type of work (e.g., IT Services, Construction)

                IMPORTANT: For dates, look for:
                - Posted/Issue dates near the top of the page
                - Due dates/deadlines often highlighted or in red
                - Date formats like MM/DD/YYYY, Month DD, YYYY, or ISO format
                """,
                    schema_definition=RFPMetadataSchema,
                )
            )

            # Extract data from result
            data = result.data if hasattr(result, "data") else result
            data = self._to_dict(data)
            logger.info("Extracted metadata: %s", data)
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
            List of ScrapedDocument objects (without local paths - not downloaded yet)
        """
        try:
            from stagehand import ExtractOptions

            # Use Stagehand page to find document links
            result = await stagehand.page.extract(
                ExtractOptions(
                    instruction="""Find all downloadable documents/attachments on this page.

For each document, you MUST extract these fields carefully:
- filename: The visible name/label of the file (e.g., "Informal General Terms.docx")
- url: The ACTUAL href attribute from the <a> tag - each document MUST have a UNIQUE URL
- type: Document category (solicitation, amendment, attachment, etc.)

CRITICAL RULES:
1. Each document link has a UNIQUE href attribute - extract it exactly as it appears in the HTML
2. Do NOT use the same URL for multiple documents - each file has its own download link
3. Look at the actual href="..." value in the HTML, not the display text
4. URLs may contain encoded characters like %20 for spaces - keep them as-is
5. If a link points to a PDF, docx, xlsx, or other file, extract that specific URL

Example of correct extraction:
- Link: <a href="/download/doc123.pdf">Terms and Conditions.pdf</a>
  → filename: "Terms and Conditions.pdf", url: "/download/doc123.pdf"
- Link: <a href="/files/attachment_456.docx">Signature Page.docx</a>
  → filename: "Signature Page.docx", url: "/files/attachment_456.docx"

Look for download links in tables, lists, or attachment sections on the page.
                """,
                    schema_definition=DocumentsListSchema,
                )
            )

            documents = []
            data = result.data if hasattr(result, "data") else result
            data = self._to_dict(data)
            doc_list = data.get("documents", [])

            logger.info("Stagehand extracted %d document entries", len(doc_list))
            print(f"[EXTRACT] Stagehand returned {len(doc_list)} documents:")
            for i, d in enumerate(doc_list):
                print(
                    f"[EXTRACT]   { i + 1 }. {d.get('filename', 'unknown')} -> {d.get('url', 'NO URL')[:80]}"
                )

            for doc in doc_list:
                filename = doc.get("filename", "unknown")
                file_ext = Path(filename).suffix.lower().lstrip(".")
                raw_url = doc.get("url", "")

                logger.info(
                    f"Processing document: {filename}, raw URL: {raw_url[:100] if raw_url else 'None'}"
                )

                # Resolve and validate the URL
                resolved_url = self._resolve_document_url(raw_url, base_url)

                # Always add the document so users know it exists, even if URL is invalid
                # The download will be attempted later and may fail
                documents.append(
                    ScrapedDocument(
                        filename=filename,
                        source_url=resolved_url or raw_url,  # Use raw if resolve fails
                        file_type=file_ext if file_ext else None,
                        document_type=self._classify_document_type(
                            doc.get("type", ""), filename
                        ),
                    )
                )

                if resolved_url:
                    logger.info(
                        f"Document URL resolved: {raw_url[:50]}... -> {resolved_url[:50]}..."
                    )
                else:
                    logger.warning(
                        f"Could not resolve document URL for {filename}: {raw_url[:100] if raw_url else 'empty'}"
                    )

            logger.info("Found %d documents", len(documents))
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

        # Clean the URL
        url = url.strip()

        # Skip invalid/placeholder URLs
        if url in ["#", "javascript:void(0)", "javascript:;", ""]:
            return None

        # Skip URLs that are clearly not download links
        if url.startswith("mailto:") or url.startswith("tel:"):
            return None

        # Check if it's already an absolute URL
        parsed = urlparse(url)
        if parsed.scheme in ("http", "https"):
            return url

        # Resolve relative URL
        try:
            resolved = urljoin(base_url, url)
            # Validate the resolved URL
            parsed_resolved = urlparse(resolved)
            if parsed_resolved.scheme in ("http", "https") and parsed_resolved.netloc:
                return resolved
        except Exception as e:
            logger.warning("Failed to resolve URL %s: %s", url, e)

        return None

    async def _extract_qa(self, stagehand: Any) -> list[ScrapedQA]:
        """
        Extract Q&A entries from the RFP page.

        Args:
            stagehand: Active Stagehand session

        Returns:
            List of ScrapedQA objects
        """
        try:
            from stagehand import ExtractOptions

            # First, try to navigate to Q&A section if it exists
            try:
                await stagehand.page.act(
                    "Click on the Q&A tab or Questions and Answers section if visible"
                )
                await asyncio.sleep(1)  # Wait for content to load
            except Exception:
                logger.debug("No Q&A tab found, checking current page")

            # Extract Q&A content
            result = await stagehand.page.extract(
                ExtractOptions(
                    instruction="""Find all Questions and Answers (Q&A) on this page.
                For each Q&A entry, extract:
                - question_number: The question number (Q1, Q2, etc.) if shown
                - question: The question text
                - answer: The answer text (may be empty if not yet answered)
                - asked_date: When the question was asked (if shown)
                - answered_date: When it was answered (if shown)
                """,
                    schema_definition=QAListSchema,
                )
            )

            qa_items = []
            data = result.data if hasattr(result, "data") else result
            data = self._to_dict(data)
            # Handle both camelCase (qaItems) and snake_case (qa_items) keys
            qa_list = data.get("qaItems", []) or data.get("qa_items", [])

            for qa in qa_list:
                question = qa.get("question") or qa.get("questionText") or ""
                if question:  # Only add if there's a question
                    qa_items.append(
                        ScrapedQA(
                            question_number=qa.get("question_number")
                            or qa.get("questionNumber"),
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
        Download all documents for an RFP using browser-based downloads.

        BeaconBid requires clicking download links in the browser context,
        as direct URL fetching returns 405 errors.

        Args:
            rfp: ScrapedRFP containing document info
            rfp_id: Unique ID for organizing storage

        Returns:
            List of ScrapedDocument with local file paths
        """
        print(f"[DOWNLOAD] download_documents called for RFP {rfp_id}")
        print(
            f"[DOWNLOAD] Documents to download: {[d.filename for d in rfp.documents] if rfp.documents else 'None'}"
        )
        storage_path = self.get_document_storage_path(rfp_id)
        downloaded_docs = []

        if not rfp.documents:
            print(f"[DOWNLOAD] No documents to download for RFP {rfp_id}")
            logger.info("No documents to download for RFP %s", rfp_id)
            return downloaded_docs

        # Try browser-based download first (click links)
        try:
            print(
                "[DOWNLOAD] Starting browser-based download via _download_via_browser..."
            )
            downloaded_docs = await self._download_via_browser(rfp, storage_path)
            if downloaded_docs:
                print(
                    f"[DOWNLOAD] Successfully downloaded {len(downloaded_docs)} documents via browser"
                )
                logger.info(
                    f"Successfully downloaded {len(downloaded_docs)} documents via browser"
                )
                return downloaded_docs
            else:
                print("[DOWNLOAD] Browser download returned empty list")
        except Exception as e:
            print(f"[DOWNLOAD] Browser-based download failed with exception: {e}")
            logger.warning(
                f"Browser-based download failed: {e}, falling back to direct download"
            )

        # Fallback to direct URL download
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

    async def _download_via_browser(
        self, rfp: ScrapedRFP, storage_path: Path
    ) -> list[ScrapedDocument]:
        """
        Download all documents by clicking the 'Download Package' button.

        BeaconBid has a 'Download Package' button that downloads all attachments as a ZIP.
        This is much simpler and more reliable than clicking individual document links.

        Browserbase stores downloads in their cloud - files must be retrieved via API after session.
        See: https://docs.browserbase.com/features/downloads
        """
        downloaded_docs = []
        stagehand = None
        session_id = None

        try:
            print("[DOWNLOAD] === Starting browser session for Download Package ===")
            logger.info("Starting browser session for Download Package button")

            stagehand = await self._create_stagehand_session()
            page = stagehand.page

            # Get session ID for later download retrieval
            if hasattr(stagehand, "session_id"):
                session_id = stagehand.session_id
            elif hasattr(stagehand, "browserbase_session_id"):
                session_id = stagehand.browserbase_session_id
            elif hasattr(stagehand, "_session_id"):
                session_id = stagehand._session_id

            print(f"[DOWNLOAD] Session ID: {session_id}")
            logger.info("Browserbase session ID: %s", session_id)

            # Configure CDP for downloads
            browser = getattr(stagehand, "browser", None) or getattr(
                stagehand, "_browser", None
            )
            if browser:
                try:
                    cdp_session = await browser.new_browser_cdp_session()
                    await cdp_session.send(
                        "Browser.setDownloadBehavior",
                        {
                            "behavior": "allow",
                            "downloadPath": "downloads",
                            "eventsEnabled": True,
                        },
                    )
                except Exception as cdp_err:
                    logger.warning("Could not configure CDP session: %s", cdp_err)

            # Navigate to the RFP page
            await page.goto(rfp.source_url)
            await asyncio.sleep(2)

            # Click the "Download Package" button to get all attachments at once
            print("[DOWNLOAD] Clicking 'Download Package' button...")
            await stagehand.page.act(
                "Click the 'Download Package' button to download all attachments"
            )

            # Wait for the package download to complete (ZIP file with all docs)
            print("[DOWNLOAD] Waiting 15s for package download to complete...")
            await asyncio.sleep(15)
            print("[DOWNLOAD] Download Package click completed")

        except Exception as e:
            print(f"[DOWNLOAD] Session failed: {e}")
            logger.error("Download session failed: %s", e)

        finally:
            # Close the Stagehand session - this triggers upload to Browserbase cloud
            if stagehand:
                try:
                    await stagehand.close()
                    logger.info("Stagehand session closed")
                except Exception as e:
                    logger.warning("Error closing Stagehand session: %s", e)

        # Wait for upload to Browserbase cloud
        await asyncio.sleep(3)

        # Retrieve the package from Browserbase cloud storage
        if session_id:
            try:
                print(
                    f"[DOWNLOAD] Retrieving package from Browserbase session: {session_id}"
                )
                downloaded_docs = await self._retrieve_browserbase_downloads(
                    session_id, rfp.documents, storage_path
                )
                print(
                    f"[DOWNLOAD] ✓ Retrieved {len(downloaded_docs)} documents from package"
                )
            except Exception as e:
                print(f"[DOWNLOAD] Failed to retrieve package: {e}")
                logger.exception("Failed to retrieve from Browserbase: %s", e)
        else:
            print("[DOWNLOAD] No session ID - cannot retrieve downloads")

        print(
            f"[DOWNLOAD] === Total downloaded: {len(downloaded_docs)}/{len(rfp.documents)} ==="
        )
        return downloaded_docs

    async def _retrieve_browserbase_downloads(
        self,
        session_id: str,
        documents: list[ScrapedDocument],
        storage_path: Path,
        retry_seconds: int = 30,
    ) -> list[ScrapedDocument]:
        """
        Retrieve downloaded files from Browserbase cloud storage.

        Args:
            session_id: Browserbase session ID
            documents: List of expected documents
            storage_path: Local path to save files
            retry_seconds: How long to retry if no downloads found

        Returns:
            List of documents with updated file paths
        """
        import io
        import time
        import zipfile

        from browserbase import Browserbase

        downloaded_docs = []
        end_time = time.time() + retry_seconds

        bb = Browserbase(api_key=self.browserbase_api_key)
        print("[DOWNLOAD] Browserbase client created, polling for downloads...")
        logger.info("Retrieving downloads from Browserbase session: %s", session_id)

        while time.time() < end_time:
            try:
                response = bb.sessions.downloads.list(session_id)

                if (
                    response
                    and hasattr(response, "status_code")
                    and response.status_code == 200
                ):
                    content = response.read()
                    # Check if we have actual content (ZIP header is 22+ bytes)
                    if len(content) > 22:
                        print(
                            f"[DOWNLOAD] Retrieved {len(content)} bytes from Browserbase"
                        )
                        logger.info("Retrieved %d bytes from Browserbase", len(content))

                        # Extract ZIP contents
                        with zipfile.ZipFile(io.BytesIO(content), "r") as zip_ref:
                            file_names = zip_ref.namelist()
                            print(
                                f"[DOWNLOAD] ZIP contains {len(file_names)} files: {file_names}"
                            )
                            logger.info("ZIP contains files: %s", file_names)

                            for zip_filename in file_names:
                                # Browserbase adds timestamp suffix: sample-1719265797164.pdf
                                # Try to match with our expected documents
                                for doc in documents:
                                    base_name = doc.filename.rsplit(".", 1)[0]
                                    if (
                                        base_name in zip_filename
                                        or doc.filename in zip_filename
                                    ):
                                        # Extract and save the file
                                        safe_filename = self._sanitize_filename(
                                            doc.filename
                                        )
                                        local_path = storage_path / safe_filename

                                        with zip_ref.open(zip_filename) as src:
                                            file_content = src.read()
                                            async with aiofiles.open(
                                                local_path, "wb"
                                            ) as dst:
                                                await dst.write(file_content)

                                        file_size = len(file_content)
                                        doc.file_path = str(local_path)
                                        doc.file_size = file_size
                                        doc.checksum = self.compute_file_checksum(
                                            str(local_path)
                                        )
                                        doc.downloaded_at = datetime.now(timezone.utc)

                                        downloaded_docs.append(doc)
                                        logger.info(
                                            f"Saved from Browserbase: {safe_filename} ({file_size} bytes)"
                                        )
                                        break

                        return downloaded_docs

                elif hasattr(response, "content"):
                    # Alternative response format
                    content = response.content
                    if len(content) > 22:
                        # Same extraction logic
                        with zipfile.ZipFile(io.BytesIO(content), "r") as zip_ref:
                            for zip_filename in zip_ref.namelist():
                                for doc in documents:
                                    base_name = doc.filename.rsplit(".", 1)[0]
                                    if (
                                        base_name in zip_filename
                                        or doc.filename in zip_filename
                                    ):
                                        safe_filename = self._sanitize_filename(
                                            doc.filename
                                        )
                                        local_path = storage_path / safe_filename

                                        with zip_ref.open(zip_filename) as src:
                                            file_content = src.read()
                                            async with aiofiles.open(
                                                local_path, "wb"
                                            ) as dst:
                                                await dst.write(file_content)

                                        file_size = len(file_content)
                                        doc.file_path = str(local_path)
                                        doc.file_size = file_size
                                        doc.checksum = self.compute_file_checksum(
                                            str(local_path)
                                        )
                                        doc.downloaded_at = datetime.now(timezone.utc)

                                        downloaded_docs.append(doc)
                                        logger.info(
                                            f"Saved from Browserbase: {safe_filename} ({file_size} bytes)"
                                        )
                                        break

                        return downloaded_docs

            except Exception as e:
                logger.debug("Error fetching downloads (will retry): %s", e)

            await asyncio.sleep(2)  # Wait before retrying

        logger.warning("No downloads found from Browserbase within %ds", retry_seconds)
        return downloaded_docs

    async def _download_single_document(
        self, session: aiohttp.ClientSession, doc: ScrapedDocument, storage_path: Path
    ) -> ScrapedDocument | None:
        """Download a single document with retry logic."""
        last_error: Exception | None = None

        # Validate URL before attempting download
        if not doc.source_url or not doc.source_url.startswith(("http://", "https://")):
            logger.error(
                f"Invalid document URL: {doc.source_url} for file {doc.filename}"
            )
            return None

        for attempt in range(1, self.DOWNLOAD_MAX_RETRIES + 1):
            try:
                logger.info(
                    "Downloading (attempt %d/%d): %s from %s",
                    attempt,
                    self.DOWNLOAD_MAX_RETRIES,
                    doc.filename,
                    doc.source_url[:100],  # Log first 100 chars of URL
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
            # Always return updated_rfp so caller can compare against database
            # (e.g., documents may need to be saved even if page content unchanged)
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

        Attempts to preserve timezone information when present. If timezone info is found,
        the datetime will use that timezone. Otherwise, defaults to UTC for consistency.

        For RFP dates (especially response_deadline), all dates are stored as timezone-aware
        (defaulting to UTC if no timezone is specified). This ensures consistent handling
        and prevents ambiguity when comparing dates across different agencies/timezones.

        Args:
            date_str: Date string in various formats, optionally with timezone info

        Returns:
            timezone-aware datetime object (UTC if no timezone specified)
        """
        if not date_str:
            return None

        # First, try dateutil.parser which handles timezones well
        try:
            from dateutil import parser as date_parser

            parsed = date_parser.parse(date_str, fuzzy=True, default=None)
            if parsed:
                # If parsed date is timezone-naive, assume UTC for consistency
                # (Most government RFPs use Eastern Time, but UTC is safer for storage)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed
        except ImportError:
            # dateutil not available, fall back to manual parsing
            logger.debug("dateutil not available, using manual date parsing")
        except (ValueError, TypeError) as e:
            logger.debug("dateutil parsing failed: %s, trying manual parsing", e)

        # Fallback: Manual parsing with timezone handling
        cleaned = date_str.strip()
        detected_tz = None

        # Map timezone abbreviations to timezone objects
        tz_map = {
            "CST": timezone(timedelta(hours=-6)),  # Central Standard Time
            "CDT": timezone(timedelta(hours=-5)),  # Central Daylight Time
            "EST": timezone(timedelta(hours=-5)),  # Eastern Standard Time
            "EDT": timezone(timedelta(hours=-4)),  # Eastern Daylight Time
            "PST": timezone(timedelta(hours=-8)),  # Pacific Standard Time
            "PDT": timezone(timedelta(hours=-7)),  # Pacific Daylight Time
            "MST": timezone(timedelta(hours=-7)),  # Mountain Standard Time
            "MDT": timezone(timedelta(hours=-6)),  # Mountain Daylight Time
            "UTC": timezone.utc,
            "GMT": timezone.utc,
        }

        # Detect and extract timezone abbreviation
        for tz_abbr, tz_obj in tz_map.items():
            if cleaned.endswith(f" {tz_abbr}"):
                detected_tz = tz_obj
                cleaned = cleaned[: -len(tz_abbr) - 1]  # Remove " TZ" from end
                break
            elif cleaned.endswith(tz_abbr):
                detected_tz = tz_obj
                cleaned = cleaned[: -len(tz_abbr)]
                break

        # Remove "at" between date and time
        cleaned = cleaned.replace(" at ", " ")

        # Common date formats
        formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%m-%d-%Y",
            "%B %d, %Y",
            "%b %d, %Y",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%B %d, %Y %I:%M:%S %p",  # December 2, 2025 10:00:00 AM
            "%B %d, %Y %H:%M:%S",  # December 2, 2025 10:00:00
            "%b %d, %Y %I:%M:%S %p",
            "%b %d, %Y %H:%M:%S",
        ]

        for fmt in formats:
            try:
                parsed = datetime.strptime(cleaned.strip(), fmt)
                # Attach detected timezone if found, otherwise assume UTC for consistency
                if detected_tz:
                    parsed = parsed.replace(tzinfo=detected_tz)
                else:
                    # Default to UTC for timezone-naive dates to ensure consistency
                    # This assumes government RFPs are typically in US timezones but
                    # storing in UTC prevents ambiguity
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
            # Remove currency symbols and commas
            cleaned = amount_str.replace("$", "").replace(",", "").strip()
            # Handle "K" and "M" suffixes
            if cleaned.upper().endswith("K"):
                return float(cleaned[:-1]) * 1000
            elif cleaned.upper().endswith("M"):
                return float(cleaned[:-1]) * 1_000_000
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
