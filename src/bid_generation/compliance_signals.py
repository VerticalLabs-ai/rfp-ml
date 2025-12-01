"""
Compliance Signals Detector
Detects special compliance requirements from RFP content and Q&A sections.
Includes FEMA domestic preference detection and other federal compliance signals.
"""
import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ComplianceSignals:
    """Detected compliance signals from RFP analysis"""
    fema_domestic_preference: bool = False
    fema_grant_funded: bool = False
    federal_funding: bool = False
    sam_registration_required: bool = False
    security_clearance_required: bool = False
    section_508_compliance: bool = False
    hipaa_compliance: bool = False
    pci_compliance: bool = False
    fedramp_required: bool = False
    domestic_preference_text: str = ""
    detected_signals: list[str] = field(default_factory=list)
    raw_matches: list[dict[str, str]] = field(default_factory=list)


class ComplianceSignalDetector:
    """
    Detects compliance requirements and special conditions from RFP content.
    """

    # FEMA Domestic Preference patterns
    FEMA_PATTERNS = [
        r"fema.*domestic\s*preference",
        r"domestic\s*preference.*fema",
        r"2\s*c\.?f\.?r\.?\s*§?\s*200\.322",
        r"cfr\s*200\.322",
        r"domestic\s*preferences?\s*for\s*procurement",
        r"fema.*preparedness\s*grants?\s*manual",
        r"preparedness\s*grants?\s*manual.*fema",
        r"u\.?s\.?[\-\s]*based\s*personnel",
        r"domestic\s*hosting",
        r"u\.?s\.?[\-\s]*based\s*hosting",
        r"preference.*given.*u\.?s\.?[\-\s]*based",
        r"homeland\s*security.*grant",
        r"fema\s*grant",
        r"empg\s*grant",  # Emergency Management Performance Grant
        r"hsgp",  # Homeland Security Grant Program
        r"shsp",  # State Homeland Security Program
        r"uasi",  # Urban Areas Security Initiative
    ]

    # Federal funding patterns
    FEDERAL_FUNDING_PATTERNS = [
        r"federal\s*fund",
        r"federally\s*funded",
        r"grant\s*funded",
        r"federal\s*grant",
        r"federal\s*assistance",
        r"federal\s*award",
    ]

    # Security patterns
    SECURITY_PATTERNS = [
        r"security\s*clearance",
        r"secret\s*clearance",
        r"top\s*secret",
        r"classified\s*information",
        r"fedramp",
        r"fed[\-\s]*ramp",
    ]

    # Accessibility patterns
    ACCESSIBILITY_PATTERNS = [
        r"section\s*508",
        r"508\s*compliance",
        r"ada\s*compliance",
        r"wcag",
        r"accessibility\s*standards",
    ]

    # Healthcare patterns
    HEALTHCARE_PATTERNS = [
        r"hipaa",
        r"phi\b",  # Protected Health Information
        r"health\s*information",
        r"pci[\-\s]*dss",
        r"payment\s*card\s*industry",
    ]

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def detect_signals(
        self,
        rfp_data: dict[str, Any],
        qa_items: list[dict[str, Any]] | None = None,
    ) -> ComplianceSignals:
        """
        Analyze RFP content and Q&A to detect compliance signals.

        Args:
            rfp_data: RFP information including title, description, etc.
            qa_items: List of Q&A entries from the RFP

        Returns:
            ComplianceSignals with detected requirements
        """
        signals = ComplianceSignals()

        # Combine all text for analysis
        text_to_analyze = self._build_analysis_text(rfp_data, qa_items)

        # Detect FEMA domestic preference
        fema_matches = self._detect_patterns(text_to_analyze, self.FEMA_PATTERNS)
        if fema_matches:
            signals.fema_domestic_preference = True
            signals.fema_grant_funded = True
            signals.detected_signals.append("FEMA Domestic Preference")
            signals.raw_matches.extend([{"pattern": "fema", "match": m} for m in fema_matches])

            # Extract the specific domestic preference text for context
            signals.domestic_preference_text = self._extract_domestic_preference_context(
                text_to_analyze, fema_matches
            )

        # Detect federal funding
        federal_matches = self._detect_patterns(text_to_analyze, self.FEDERAL_FUNDING_PATTERNS)
        if federal_matches:
            signals.federal_funding = True
            signals.detected_signals.append("Federal Funding")
            signals.raw_matches.extend([{"pattern": "federal", "match": m} for m in federal_matches])

        # Detect security requirements
        security_matches = self._detect_patterns(text_to_analyze, self.SECURITY_PATTERNS)
        if security_matches:
            if any("fedramp" in m.lower() for m in security_matches):
                signals.fedramp_required = True
                signals.detected_signals.append("FedRAMP Required")
            if any("clearance" in m.lower() or "classified" in m.lower() for m in security_matches):
                signals.security_clearance_required = True
                signals.detected_signals.append("Security Clearance Required")

        # Detect accessibility requirements
        accessibility_matches = self._detect_patterns(text_to_analyze, self.ACCESSIBILITY_PATTERNS)
        if accessibility_matches:
            signals.section_508_compliance = True
            signals.detected_signals.append("Section 508 Compliance")

        # Detect healthcare compliance
        healthcare_matches = self._detect_patterns(text_to_analyze, self.HEALTHCARE_PATTERNS)
        if healthcare_matches:
            if any("hipaa" in m.lower() or "phi" in m.lower() or "health" in m.lower() for m in healthcare_matches):
                signals.hipaa_compliance = True
                signals.detected_signals.append("HIPAA Compliance")
            if any("pci" in m.lower() or "payment" in m.lower() for m in healthcare_matches):
                signals.pci_compliance = True
                signals.detected_signals.append("PCI-DSS Compliance")

        # Check for SAM registration
        if re.search(r"sam\.gov|sam\s*registration|system\s*for\s*award\s*management", text_to_analyze, re.IGNORECASE):
            signals.sam_registration_required = True
            signals.detected_signals.append("SAM Registration Required")

        self.logger.info(f"Detected compliance signals: {signals.detected_signals}")
        return signals

    def _build_analysis_text(
        self,
        rfp_data: dict[str, Any],
        qa_items: list[dict[str, Any]] | None,
    ) -> str:
        """Build combined text for analysis."""
        parts = []

        # Add RFP title and description
        if rfp_data.get("title"):
            parts.append(rfp_data["title"])
        if rfp_data.get("description"):
            parts.append(rfp_data["description"])
        if rfp_data.get("agency"):
            parts.append(rfp_data["agency"])

        # Add Q&A content
        if qa_items:
            for qa in qa_items:
                if qa.get("question_text"):
                    parts.append(qa["question_text"])
                if qa.get("answer_text"):
                    parts.append(qa["answer_text"])

        return " ".join(parts).lower()

    def _detect_patterns(self, text: str, patterns: list[str]) -> list[str]:
        """Detect patterns in text and return matches."""
        matches = []
        for pattern in patterns:
            found = re.findall(pattern, text, re.IGNORECASE)
            matches.extend(found)
        return matches

    def _extract_domestic_preference_context(
        self,
        text: str,
        matches: list[str]
    ) -> str:
        """Extract surrounding context for domestic preference mentions."""
        contexts = []

        # Find sentences containing domestic preference mentions
        sentences = re.split(r'[.!?]+', text)
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(match.lower() in sentence_lower for match in matches):
                contexts.append(sentence.strip())

        # Return unique contexts
        unique_contexts = list(dict.fromkeys(contexts))[:3]  # Limit to 3 most relevant
        return " ".join(unique_contexts)

    def to_dict(self, signals: ComplianceSignals) -> dict[str, Any]:
        """Convert signals to dictionary for API responses."""
        return {
            "fema_domestic_preference": signals.fema_domestic_preference,
            "fema_grant_funded": signals.fema_grant_funded,
            "federal_funding": signals.federal_funding,
            "sam_registration_required": signals.sam_registration_required,
            "security_clearance_required": signals.security_clearance_required,
            "section_508_compliance": signals.section_508_compliance,
            "hipaa_compliance": signals.hipaa_compliance,
            "pci_compliance": signals.pci_compliance,
            "fedramp_required": signals.fedramp_required,
            "domestic_preference_text": signals.domestic_preference_text,
            "detected_signals": signals.detected_signals,
        }


def create_compliance_detector() -> ComplianceSignalDetector:
    """Factory function to create a compliance signal detector."""
    return ComplianceSignalDetector()


if __name__ == "__main__":
    # Test the detector
    detector = create_compliance_detector()

    test_rfp = {
        "title": "3 Multi-Year Public Facing Regional Websites",
        "description": "Website development for Homeland Security and Public Safety",
        "agency": "City of Houston Mayor's Office of Homeland Security",
    }

    test_qa = [
        {
            "question_text": "Will preference be given to US-based companies?",
            "answer_text": "Preference will be given to U.S.-based personnel and hosting environments consistent with FEMA's Domestic Preference for Procurement guidance in the Preparedness Grants Manual."
        },
        {
            "question_text": "Is this grant funded?",
            "answer_text": "This project is funded through FEMA preparedness grants."
        }
    ]

    signals = detector.detect_signals(test_rfp, test_qa)
    print(f"FEMA Domestic Preference: {signals.fema_domestic_preference}")
    print(f"Detected Signals: {signals.detected_signals}")
    print(f"Domestic Preference Text: {signals.domestic_preference_text}")
