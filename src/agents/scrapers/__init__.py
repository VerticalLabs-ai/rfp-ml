"""
RFP Scrapers package for extracting RFP data from various portals.
"""
from .base_scraper import BaseScraper, ScrapedDocument, ScrapedQA, ScrapedRFP
from .beaconbid_scraper import BeaconBidScraper
from .generic_web_scraper import GenericWebScraper
from .sam_gov_scraper import SAMGovScraper

__all__ = [
    "BaseScraper",
    "ScrapedRFP",
    "ScrapedDocument",
    "ScrapedQA",
    "BeaconBidScraper",
    "GenericWebScraper",
    "SAMGovScraper",
]
