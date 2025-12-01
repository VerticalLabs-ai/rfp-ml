"""
Natural Language Parser for RFP Discovery.

Parses natural language queries into structured search parameters,
supporting conversational searches like "Construction contracts in California".
"""
import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ParsedQuery:
    """Structured representation of a parsed natural language query."""

    original_query: str
    semantic_query: str  # Cleaned query for embedding search
    extracted_filters: dict[str, Any] = field(default_factory=dict)
    keywords: list[str] = field(default_factory=list)
    intent: str = "search"  # search, filter, question
    confidence: float = 1.0


class NLQueryParser:
    """
    Parses natural language queries into structured search parameters.

    Supports:
    - Location extraction: "in California", "near DC"
    - Agency extraction: "from DOD", "Army contracts"
    - NAICS code extraction: "NAICS 541511"
    - Amount extraction: "over $1M", "under 500k"
    - Date extraction: "due next week", "deadline in March"
    - Set-aside extraction: "small business", "8(a)"
    """

    # Location patterns
    STATE_ABBREVS = {
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
        "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
        "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
        "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
        "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
        "DC", "PR", "VI", "GU"
    }

    STATE_NAMES = {
        "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
        "california": "CA", "colorado": "CO", "connecticut": "CT",
        "delaware": "DE", "florida": "FL", "georgia": "GA", "hawaii": "HI",
        "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
        "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME",
        "maryland": "MD", "massachusetts": "MA", "michigan": "MI",
        "minnesota": "MN", "mississippi": "MS", "missouri": "MO",
        "montana": "MT", "nebraska": "NE", "nevada": "NV",
        "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM",
        "new york": "NY", "north carolina": "NC", "north dakota": "ND",
        "ohio": "OH", "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA",
        "rhode island": "RI", "south carolina": "SC", "south dakota": "SD",
        "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT",
        "virginia": "VA", "washington": "WA", "west virginia": "WV",
        "wisconsin": "WI", "wyoming": "WY", "district of columbia": "DC",
        "puerto rico": "PR", "virgin islands": "VI", "guam": "GU"
    }

    # Common agency abbreviations
    AGENCIES = {
        "dod": "Department of Defense",
        "army": "Department of the Army",
        "navy": "Department of the Navy",
        "air force": "Department of the Air Force",
        "dhs": "Department of Homeland Security",
        "hhs": "Department of Health and Human Services",
        "va": "Department of Veterans Affairs",
        "gsa": "General Services Administration",
        "nasa": "National Aeronautics and Space Administration",
        "doe": "Department of Energy",
        "epa": "Environmental Protection Agency",
        "fema": "Federal Emergency Management Agency",
        "usda": "Department of Agriculture",
        "dot": "Department of Transportation",
        "faa": "Federal Aviation Administration",
        "irs": "Internal Revenue Service",
        "ssa": "Social Security Administration",
        "hud": "Department of Housing and Urban Development",
        "state": "Department of State",
        "treasury": "Department of the Treasury",
        "justice": "Department of Justice",
        "doj": "Department of Justice",
        "interior": "Department of the Interior",
        "commerce": "Department of Commerce",
        "labor": "Department of Labor",
        "education": "Department of Education",
    }

    # Set-aside patterns
    SET_ASIDES = {
        "small business": "SBA",
        "8a": "8(a)",
        "8(a)": "8(a)",
        "hubzone": "HUBZone",
        "sdvosb": "SDVOSB",
        "service-disabled veteran": "SDVOSB",
        "wosb": "WOSB",
        "woman-owned": "WOSB",
        "women-owned": "WOSB",
        "edwosb": "EDWOSB",
        "economically disadvantaged": "EDWOSB",
        "vosb": "VOSB",
        "veteran-owned": "VOSB",
    }

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for extraction."""
        # Location patterns
        self.location_pattern = re.compile(
            r'\b(?:in|near|from|at|around)\s+([A-Za-z\s]+?)(?:\s+(?:state|area|region))?\b',
            re.IGNORECASE
        )

        # NAICS pattern - require "naics" or "code" prefix to avoid false positives with years
        self.naics_pattern = re.compile(
            r'\b(?:naics|naics\s+code|code)\s+(\d{2,6})\b',
            re.IGNORECASE
        )

        # Amount patterns
        self.amount_patterns = [
            re.compile(r'\b(?:over|above|more than|greater than|>\s*)\s*\$?([\d,]+(?:\.\d+)?)\s*([kmb])?(?:illion)?\b', re.IGNORECASE),
            re.compile(r'\b(?:under|below|less than|<\s*)\s*\$?([\d,]+(?:\.\d+)?)\s*([kmb])?(?:illion)?\b', re.IGNORECASE),
            re.compile(r'\b\$?([\d,]+(?:\.\d+)?)\s*([kmb])?(?:illion)?\s*(?:to|-)\s*\$?([\d,]+(?:\.\d+)?)\s*([kmb])?(?:illion)?\b', re.IGNORECASE),
        ]

        # Date patterns
        self.deadline_pattern = re.compile(
            r'\b(?:due|deadline|closes?|closing|by|before)\s+(.+?)(?:\.|,|$)',
            re.IGNORECASE
        )

    def parse(self, query: str) -> ParsedQuery:
        """
        Parse a natural language query into structured parameters.

        Args:
            query: Natural language search query

        Returns:
            ParsedQuery with extracted filters and semantic query
        """
        if not query or not query.strip():
            return ParsedQuery(
                original_query="",
                semantic_query="",
                confidence=0.0
            )

        query = query.strip()
        filters: dict[str, Any] = {}
        keywords: list[str] = []

        # Extract location
        location = self._extract_location(query)
        if location:
            filters["location"] = location

        # Extract agency
        agency = self._extract_agency(query)
        if agency:
            filters["agency"] = agency

        # Extract NAICS
        naics = self._extract_naics(query)
        if naics:
            filters["naics_code"] = naics

        # Extract amount range
        amount_range = self._extract_amount(query)
        if amount_range:
            filters["amount_range"] = amount_range

        # Extract set-aside
        set_aside = self._extract_set_aside(query)
        if set_aside:
            filters["set_aside"] = set_aside

        # Build semantic query (remove filter terms for cleaner embedding)
        semantic_query = self._build_semantic_query(query)

        # Extract keywords
        keywords = self._extract_keywords(semantic_query)

        # Determine intent
        intent = self._determine_intent(query)

        # Calculate confidence based on extraction success
        confidence = self._calculate_confidence(query, filters, semantic_query)

        return ParsedQuery(
            original_query=query,
            semantic_query=semantic_query,
            extracted_filters=filters,
            keywords=keywords,
            intent=intent,
            confidence=confidence
        )

    def _extract_location(self, query: str) -> str | None:
        """Extract location from query."""
        query_lower = query.lower()

        # Check for state names
        for state_name, abbrev in self.STATE_NAMES.items():
            if state_name in query_lower:
                return abbrev

        # Check for state abbreviations
        words = query.upper().split()
        for word in words:
            clean_word = re.sub(r'[^A-Z]', '', word)
            if clean_word in self.STATE_ABBREVS:
                return clean_word

        # Try pattern matching
        match = self.location_pattern.search(query)
        if match:
            location = match.group(1).strip()
            # Check if it's a known state
            location_lower = location.lower()
            if location_lower in self.STATE_NAMES:
                return self.STATE_NAMES[location_lower]
            return location

        return None

    def _extract_agency(self, query: str) -> str | None:
        """Extract agency from query."""
        query_lower = query.lower()

        for abbrev, full_name in self.AGENCIES.items():
            if abbrev in query_lower or full_name.lower() in query_lower:
                return full_name

        # Pattern for "from [agency]" or "[agency] contracts"
        agency_pattern = re.compile(
            r'\b(?:from|for|with|by)\s+(?:the\s+)?([A-Za-z\s]+?)(?:\s+contracts?|\s+rfps?|\s+opportunities?)?\b',
            re.IGNORECASE
        )
        match = agency_pattern.search(query)
        if match:
            potential_agency = match.group(1).strip().lower()
            if potential_agency in self.AGENCIES:
                return self.AGENCIES[potential_agency]

        return None

    def _extract_naics(self, query: str) -> str | None:
        """Extract NAICS code from query."""
        match = self.naics_pattern.search(query)
        if match:
            code = match.group(1)
            if 2 <= len(code) <= 6:
                return code
        return None

    def _extract_amount(self, query: str) -> dict[str, float] | None:
        """Extract amount range from query."""
        result: dict[str, float] = {}

        # Check for "over X"
        over_match = self.amount_patterns[0].search(query)
        if over_match:
            amount = self._parse_amount(over_match.group(1), over_match.group(2))
            if amount:
                result["min"] = amount

        # Check for "under X"
        under_match = self.amount_patterns[1].search(query)
        if under_match:
            amount = self._parse_amount(under_match.group(1), under_match.group(2))
            if amount:
                result["max"] = amount

        # Check for range "X to Y"
        range_match = self.amount_patterns[2].search(query)
        if range_match:
            min_amount = self._parse_amount(range_match.group(1), range_match.group(2))
            max_amount = self._parse_amount(range_match.group(3), range_match.group(4))
            if min_amount:
                result["min"] = min_amount
            if max_amount:
                result["max"] = max_amount

        return result if result else None

    def _parse_amount(self, amount_str: str, multiplier: str | None) -> float | None:
        """Parse amount string with optional multiplier."""
        try:
            amount = float(amount_str.replace(",", ""))
            if multiplier:
                multiplier = multiplier.lower()
                if multiplier == "k":
                    amount *= 1_000
                elif multiplier == "m":
                    amount *= 1_000_000
                elif multiplier == "b":
                    amount *= 1_000_000_000
            return amount
        except (ValueError, TypeError):
            return None

    def _extract_set_aside(self, query: str) -> str | None:
        """Extract set-aside type from query."""
        query_lower = query.lower()

        for pattern, set_aside in self.SET_ASIDES.items():
            if pattern in query_lower:
                return set_aside

        return None

    def _build_semantic_query(self, query: str) -> str:
        """Build clean semantic query by removing filter terms."""
        semantic = query

        # Remove common filter phrases
        patterns_to_remove = [
            r'\b(?:in|near|from|at|around)\s+[A-Za-z\s]+?(?:\s+state|\s+area)?\b',
            r'\bnaics\s*(?:code)?\s*\d+\b',
            r'\b(?:over|under|above|below)\s*\$?[\d,]+[kmb]?\b',
            r'\bdue\s+.+?(?:\.|,|$)',
            r'\bfor\s+(?:the\s+)?(?:' + '|'.join(self.AGENCIES.keys()) + r')\b',
        ]

        for pattern in patterns_to_remove:
            semantic = re.sub(pattern, '', semantic, flags=re.IGNORECASE)

        # Clean up extra whitespace
        semantic = ' '.join(semantic.split())

        return semantic.strip() or query

    def _extract_keywords(self, query: str) -> list[str]:
        """Extract important keywords from query."""
        # Remove common stop words
        stop_words = {
            "a", "an", "the", "and", "or", "but", "in", "on", "at", "to",
            "for", "of", "with", "by", "from", "as", "is", "was", "are",
            "were", "been", "be", "have", "has", "had", "do", "does", "did",
            "will", "would", "could", "should", "may", "might", "must",
            "shall", "can", "need", "want", "looking", "find", "search",
            "show", "me", "i", "we", "you", "contracts", "rfp", "rfps",
            "opportunities", "solicitations",
        }

        words = re.findall(r'\b[a-zA-Z]{3,}\b', query.lower())
        keywords = [w for w in words if w not in stop_words]

        return list(dict.fromkeys(keywords))  # Remove duplicates, preserve order

    def _determine_intent(self, query: str) -> str:
        """Determine the intent of the query."""
        query_lower = query.lower()

        # Question intent
        if any(q in query_lower for q in ["what", "how", "why", "when", "where", "which", "?"]):
            return "question"

        # Filter intent (specific criteria)
        if any(f in query_lower for f in ["only", "just", "exclusively", "filter", "limit"]):
            return "filter"

        # Default search intent
        return "search"

    def _calculate_confidence(
        self,
        query: str,
        filters: dict,
        semantic_query: str
    ) -> float:
        """Calculate confidence score for the parse."""
        confidence = 1.0

        # Reduce confidence for very short queries
        if len(query.split()) < 3:
            confidence *= 0.8

        # Increase confidence if filters were extracted
        if filters:
            confidence = min(1.0, confidence + 0.1 * len(filters))

        # Reduce confidence if semantic query is too different
        if len(semantic_query) < len(query) * 0.3:
            confidence *= 0.7

        return round(confidence, 2)


# Singleton instance
_parser: NLQueryParser | None = None


def get_nl_parser() -> NLQueryParser:
    """Get or create NL parser singleton."""
    global _parser
    if _parser is None:
        _parser = NLQueryParser()
    return _parser
