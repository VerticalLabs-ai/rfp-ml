"""
Tests for the scraper infrastructure including GenericWebScraper and SAMGovScraper.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.scrapers import (
    BaseScraper,
    GenericWebScraper,
    SAMGovScraper,
    BeaconBidScraper,
    ScrapedRFP,
    ScrapedDocument,
    ScrapedQA,
)


class TestGenericWebScraper:
    """Tests for GenericWebScraper."""

    def test_accepts_https_urls(self):
        """Should accept any HTTPS URL."""
        scraper = GenericWebScraper()
        assert scraper.is_valid_url("https://example.gov/rfp/123")
        assert scraper.is_valid_url("https://procurement.state.gov/bid")
        assert scraper.is_valid_url("https://www.some-portal.com/opportunities")

    def test_accepts_http_urls(self):
        """Should accept HTTP URLs."""
        scraper = GenericWebScraper()
        assert scraper.is_valid_url("http://legacy.gov/contracts")

    def test_rejects_invalid_urls(self):
        """Should reject non-HTTP(S) URLs."""
        scraper = GenericWebScraper()
        assert not scraper.is_valid_url("ftp://example.com")
        assert not scraper.is_valid_url("not-a-url")
        assert not scraper.is_valid_url("")
        assert not scraper.is_valid_url("javascript:void(0)")

    def test_platform_name(self):
        """Should have generic platform name."""
        scraper = GenericWebScraper()
        assert scraper.PLATFORM_NAME == "generic"

    def test_detect_platform_sam_gov(self):
        """Should detect SAM.gov from URL."""
        scraper = GenericWebScraper()
        assert scraper._detect_platform("https://sam.gov/opp/123/view") == "sam.gov"
        assert scraper._detect_platform("https://beta.sam.gov/opp/123/view") == "sam.gov"

    def test_detect_platform_beaconbid(self):
        """Should detect BeaconBid from URL."""
        scraper = GenericWebScraper()
        assert scraper._detect_platform("https://beaconbid.com/solicitations/123") == "beaconbid"

    def test_detect_platform_gov_domain(self):
        """Should identify .gov domains."""
        scraper = GenericWebScraper()
        platform = scraper._detect_platform("https://procurement.texas.gov/rfp/123")
        assert ".gov" in platform or platform == "procurement.texas.gov"

    def test_detect_platform_generic(self):
        """Should return 'generic' for unknown domains."""
        scraper = GenericWebScraper()
        assert scraper._detect_platform("https://somesite.com/rfp") == "generic"


class TestSAMGovScraper:
    """Tests for SAMGovScraper."""

    def test_supported_domains(self):
        """Should support SAM.gov domains."""
        scraper = SAMGovScraper()
        assert scraper.is_valid_url("https://sam.gov/opp/123/view")
        assert scraper.is_valid_url("https://beta.sam.gov/opp/123/view")
        assert scraper.is_valid_url("https://www.sam.gov/opp/123/view")

    def test_rejects_other_domains(self):
        """Should reject non-SAM.gov domains."""
        scraper = SAMGovScraper()
        assert not scraper.is_valid_url("https://beaconbid.com/solicitations/123")
        assert not scraper.is_valid_url("https://example.com/rfp")

    def test_extract_opportunity_id_standard(self):
        """Should extract opportunity ID from standard URL."""
        scraper = SAMGovScraper()
        opp_id = scraper._extract_opportunity_id("https://sam.gov/opp/abc123-def456/view")
        assert opp_id == "abc123-def456"

    def test_extract_opportunity_id_beta(self):
        """Should extract opportunity ID from beta URL."""
        scraper = SAMGovScraper()
        # SAM.gov opportunity IDs are typically lowercase hex with dashes
        opp_id = scraper._extract_opportunity_id("https://beta.sam.gov/opp/abc123-def456/view")
        assert opp_id == "abc123-def456"

    def test_extract_opportunity_id_none(self):
        """Should return None for URLs without opportunity ID."""
        scraper = SAMGovScraper()
        assert scraper._extract_opportunity_id("https://sam.gov/search") is None
        assert scraper._extract_opportunity_id("https://sam.gov") is None

    def test_platform_name(self):
        """Should have sam.gov platform name."""
        scraper = SAMGovScraper()
        assert scraper.PLATFORM_NAME == "sam.gov"

    def test_classify_by_naics_professional_services(self):
        """Should classify professional services by NAICS."""
        scraper = SAMGovScraper()
        # NAICS 54xxxx = Professional Services
        assert scraper._classify_by_naics("541511") == "Professional Services"

    def test_classify_by_naics_it(self):
        """Should classify IT services by NAICS."""
        scraper = SAMGovScraper()
        # NAICS 51xxxx = Information Technology
        assert scraper._classify_by_naics("518210") == "Information Technology"

    def test_classify_by_naics_construction(self):
        """Should classify construction by NAICS."""
        scraper = SAMGovScraper()
        assert scraper._classify_by_naics("236220") == "Construction"

    def test_classify_by_naics_none(self):
        """Should return None for missing NAICS."""
        scraper = SAMGovScraper()
        assert scraper._classify_by_naics(None) is None
        assert scraper._classify_by_naics("") is None


class TestBeaconBidScraper:
    """Tests for BeaconBidScraper."""

    def test_supported_domains(self):
        """Should support BeaconBid domains."""
        scraper = BeaconBidScraper()
        assert scraper.is_valid_url("https://beaconbid.com/solicitations/123")
        assert scraper.is_valid_url("https://www.beaconbid.com/solicitations/123")

    def test_rejects_other_domains(self):
        """Should reject non-BeaconBid domains."""
        scraper = BeaconBidScraper()
        assert not scraper.is_valid_url("https://sam.gov/opp/123/view")
        assert not scraper.is_valid_url("https://example.com/rfp")

    def test_platform_name(self):
        """Should have beaconbid platform name."""
        scraper = BeaconBidScraper()
        assert scraper.PLATFORM_NAME == "beaconbid"


class TestGetScraper:
    """Tests for the get_scraper() function."""

    def test_returns_beaconbid_for_beaconbid_url(self):
        """Should return BeaconBidScraper for BeaconBid URLs."""
        from api.app.routes.scraper import get_scraper

        scraper = get_scraper("https://beaconbid.com/solicitations/123")
        assert isinstance(scraper, BeaconBidScraper)

    def test_returns_sam_gov_for_sam_url(self):
        """Should return SAMGovScraper for SAM.gov URLs."""
        from api.app.routes.scraper import get_scraper

        scraper = get_scraper("https://sam.gov/opp/abc123/view")
        assert isinstance(scraper, SAMGovScraper)

    def test_returns_generic_for_unknown_url(self):
        """Should return GenericWebScraper for unknown URLs."""
        from api.app.routes.scraper import get_scraper

        scraper = get_scraper("https://some-state-portal.gov/rfp/123")
        assert isinstance(scraper, GenericWebScraper)

    def test_returns_none_for_invalid_url(self):
        """Should return None for invalid URLs."""
        from api.app.routes.scraper import get_scraper

        scraper = get_scraper("not-a-url")
        assert scraper is None

        scraper = get_scraper("ftp://example.com")
        assert scraper is None


class TestScrapedDataClasses:
    """Tests for the scraped data classes."""

    def test_scraped_rfp_checksum(self):
        """Should compute consistent checksum."""
        rfp = ScrapedRFP(
            source_url="https://example.com/rfp/1",
            source_platform="test",
            title="Test RFP",
            description="Test description",
        )

        checksum1 = rfp.compute_checksum()
        checksum2 = rfp.compute_checksum()

        assert checksum1 == checksum2
        assert len(checksum1) == 32  # MD5 hex length

    def test_scraped_rfp_checksum_changes(self):
        """Should produce different checksum when content changes."""
        rfp1 = ScrapedRFP(
            source_url="https://example.com/rfp/1",
            source_platform="test",
            title="Test RFP",
        )

        rfp2 = ScrapedRFP(
            source_url="https://example.com/rfp/1",
            source_platform="test",
            title="Different Title",
        )

        assert rfp1.compute_checksum() != rfp2.compute_checksum()

    def test_scraped_document_defaults(self):
        """Should have sensible defaults."""
        doc = ScrapedDocument(
            filename="test.pdf",
            source_url="https://example.com/test.pdf",
        )

        assert doc.file_path is None
        assert doc.file_size is None
        assert doc.checksum is None
        assert doc.downloaded_at is None

    def test_scraped_qa_defaults(self):
        """Should have sensible defaults."""
        qa = ScrapedQA(question_text="What is the deadline?")

        assert qa.question_number is None
        assert qa.answer_text is None
        assert qa.asked_date is None
        assert qa.answered_date is None


class TestDateParsing:
    """Tests for date parsing in scrapers."""

    def test_parse_iso_date(self):
        """Should parse ISO format dates."""
        scraper = GenericWebScraper()
        parsed = scraper._parse_date("2024-12-15")
        assert parsed is not None
        assert parsed.year == 2024
        assert parsed.month == 12
        assert parsed.day == 15

    def test_parse_us_date(self):
        """Should parse US format dates."""
        scraper = GenericWebScraper()
        parsed = scraper._parse_date("12/15/2024")
        assert parsed is not None
        assert parsed.year == 2024
        assert parsed.month == 12

    def test_parse_written_date(self):
        """Should parse written dates."""
        scraper = GenericWebScraper()
        parsed = scraper._parse_date("December 15, 2024")
        assert parsed is not None
        assert parsed.year == 2024
        assert parsed.month == 12

    def test_parse_none_date(self):
        """Should return None for empty/None dates."""
        scraper = GenericWebScraper()
        assert scraper._parse_date(None) is None
        assert scraper._parse_date("") is None


class TestAmountParsing:
    """Tests for amount parsing in scrapers."""

    def test_parse_dollar_amount(self):
        """Should parse dollar amounts."""
        scraper = GenericWebScraper()
        assert scraper._parse_amount("$1,000,000") == 1000000
        assert scraper._parse_amount("$50,000") == 50000

    def test_parse_k_suffix(self):
        """Should parse K suffix."""
        scraper = GenericWebScraper()
        assert scraper._parse_amount("500K") == 500000
        assert scraper._parse_amount("$500k") == 500000

    def test_parse_m_suffix(self):
        """Should parse M suffix."""
        scraper = GenericWebScraper()
        assert scraper._parse_amount("5M") == 5000000
        assert scraper._parse_amount("$5m") == 5000000

    def test_parse_none_amount(self):
        """Should return None for empty/None amounts."""
        scraper = GenericWebScraper()
        assert scraper._parse_amount(None) is None
        assert scraper._parse_amount("") is None


class TestDocumentClassification:
    """Tests for document type classification."""

    def test_classify_solicitation(self):
        """Should classify solicitation documents."""
        scraper = GenericWebScraper()
        assert scraper._classify_document_type("solicitation", "file.pdf") == "solicitation"
        assert scraper._classify_document_type("", "RFP_Document.pdf") == "solicitation"

    def test_classify_amendment(self):
        """Should classify amendment documents."""
        scraper = GenericWebScraper()
        assert scraper._classify_document_type("amendment", "file.pdf") == "amendment"
        assert scraper._classify_document_type("", "Amendment_001.pdf") == "amendment"

    def test_classify_qa(self):
        """Should classify Q&A documents."""
        scraper = GenericWebScraper()
        assert scraper._classify_document_type("q&a", "file.pdf") == "qa_response"
        assert scraper._classify_document_type("", "QA_Responses.pdf") == "qa_response"

    def test_classify_attachment(self):
        """Should default to attachment."""
        scraper = GenericWebScraper()
        assert scraper._classify_document_type("", "random_file.pdf") == "attachment"


class TestFilenameSanitization:
    """Tests for filename sanitization."""

    def test_sanitize_removes_unsafe_chars(self):
        """Should remove unsafe characters."""
        scraper = GenericWebScraper()
        assert scraper._sanitize_filename("file<>name.pdf") == "file__name.pdf"
        assert scraper._sanitize_filename('file"name.pdf') == "file_name.pdf"
        assert scraper._sanitize_filename("file|name.pdf") == "file_name.pdf"

    def test_sanitize_preserves_safe_chars(self):
        """Should preserve safe characters."""
        scraper = GenericWebScraper()
        assert scraper._sanitize_filename("file-name_v1.pdf") == "file-name_v1.pdf"
        assert scraper._sanitize_filename("File Name (1).pdf") == "File Name (1).pdf"
