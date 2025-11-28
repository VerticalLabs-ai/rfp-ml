"""
Constants and configuration values for the RFP ML system.
Centralizes magic numbers and configuration defaults.
"""


# =============================================================================
# Pricing Constants
# =============================================================================
class PricingDefaults:
    """Default pricing configuration values."""

    TARGET_MARGIN: float = 0.40  # 40% target margin
    MINIMUM_MARGIN: float = 0.15  # 15% minimum margin
    HIGH_MARGIN_THRESHOLD: float = 0.35  # Above 35% considered high
    LOW_MARGIN_THRESHOLD: float = 0.20  # Below 20% considered low

    # Complexity multipliers
    LOW_COMPLEXITY_MULTIPLIER: float = 1.0
    MEDIUM_COMPLEXITY_MULTIPLIER: float = 1.15
    HIGH_COMPLEXITY_MULTIPLIER: float = 1.30
    VERY_HIGH_COMPLEXITY_MULTIPLIER: float = 1.40

    # Complexity thresholds (requirement count)
    LOW_COMPLEXITY_THRESHOLD: int = 5
    MEDIUM_COMPLEXITY_THRESHOLD: int = 15
    HIGH_COMPLEXITY_THRESHOLD: int = 25


# =============================================================================
# Decision Engine Constants
# =============================================================================
class DecisionDefaults:
    """Default decision criteria weights and thresholds."""

    # Scoring weights (must sum to 1.0)
    MARGIN_WEIGHT: float = 0.30
    COMPLEXITY_WEIGHT: float = 0.25
    DURATION_WEIGHT: float = 0.20
    HISTORICAL_WEIGHT: float = 0.15
    RESOURCE_WEIGHT: float = 0.10

    # Recommendation thresholds
    GO_THRESHOLD: float = 70.0
    REVIEW_THRESHOLD: float = 50.0
    CONFIDENCE_THRESHOLD: float = 70.0

    # Risk adjustments
    RISK_PENALTY_PER_FACTOR: float = 5.0  # 5% penalty per risk factor

    # Sample size for historical confidence
    MIN_SAMPLE_SIZE: int = 10
    CONFIDENCE_SAMPLE_SIZE: int = 20


# =============================================================================
# Compliance Constants
# =============================================================================
class ComplianceDefaults:
    """Default compliance configuration values."""

    # Requirement text minimum length to consider valid
    MIN_REQUIREMENT_LENGTH: int = 20

    # Compliance rate thresholds
    HIGH_COMPLIANCE_RATE: float = 0.80  # 80%
    LOW_COMPLIANCE_RATE: float = 0.70  # 70%

    # Complexity thresholds
    LOW_COMPLEXITY_REQUIREMENTS: int = 10
    HIGH_COMPLEXITY_REQUIREMENTS: int = 25


# =============================================================================
# RAG Constants
# =============================================================================
class RAGDefaults:
    """Default RAG configuration values."""

    # Chunking parameters
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50

    # Retrieval parameters
    TOP_K: int = 5
    SIMILARITY_THRESHOLD: float = 0.3

    # TF-IDF fallback
    TFIDF_MAX_FEATURES: int = 5000


# =============================================================================
# Duration Constants
# =============================================================================
class DurationDefaults:
    """Default duration-related values."""

    # Lead time thresholds (days)
    SHORT_LEAD_TIME: int = 15
    LONG_LEAD_TIME: int = 60

    # Lead time penalties/bonuses
    SHORT_LEAD_PENALTY: float = 0.80  # 20% penalty
    LONG_LEAD_BONUS: float = 1.10  # 10% bonus

    # Contract duration thresholds (months)
    OPTIMAL_MIN_DURATION: int = 6
    OPTIMAL_MAX_DURATION: int = 24
    ACCEPTABLE_MAX_DURATION: int = 36
    LONG_DURATION: int = 60


# =============================================================================
# Contract Value Thresholds
# =============================================================================
class ContractValueDefaults:
    """Default contract value thresholds."""

    SMALL_CONTRACT_MAX: int = 100_000
    MEDIUM_CONTRACT_MAX: int = 1_000_000

    # Win rate estimates by size
    SMALL_WIN_RATE: float = 0.75
    MEDIUM_WIN_RATE: float = 0.60
    LARGE_WIN_RATE: float = 0.45


# =============================================================================
# Triage Constants
# =============================================================================
class TriageDefaults:
    """Default triage configuration values."""

    # Award amount range
    MIN_AWARD_AMOUNT: int = 50_000
    MAX_AWARD_AMOUNT: int = 5_000_000

    # Lead time range (days)
    MIN_LEAD_DAYS: int = 15
    MAX_LEAD_DAYS: int = 60

    # Score thresholds
    HIGH_PRIORITY_SCORE: int = 80
    MEDIUM_PRIORITY_SCORE: int = 50
    MIN_PASSING_SCORE: int = 60
