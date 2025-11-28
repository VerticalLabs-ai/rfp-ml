"""
Text processing utilities for RFP data.
"""
import math
import re
from typing import Union


def preprocess_text(text: str, max_length: int = 2000) -> str:
    """
    Preprocess text for embedding or analysis.

    Args:
        text: Input text to preprocess
        max_length: Maximum character length (truncates if exceeded)

    Returns:
        Cleaned and normalized text
    """
    if not isinstance(text, str):
        return ""

    # Basic cleaning
    text = text.strip()
    text = text.replace("\n", " ").replace("\r", " ")
    text = " ".join(text.split())  # Normalize whitespace

    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length] + "..."

    return text


def clean_amount(value: Union[str, int, float, None]) -> float:
    """
    Clean and convert award amount values to float.

    Args:
        value: Raw amount value (can be string with $, commas, etc.)

    Returns:
        Cleaned float value, or 0.0 if conversion fails

    Examples:
        >>> clean_amount("$1,234,567.89")
        1234567.89
        >>> clean_amount(50000)
        50000.0
        >>> clean_amount(None)
        0.0
    """
    if value is None:
        return 0.0

    if isinstance(value, float) and math.isnan(value):
        return 0.0

    if isinstance(value, (int, float)):
        return float(value)

    try:
        # Remove currency symbols, commas, and whitespace
        cleaned = str(value).replace("$", "").replace(",", "").strip()
        return float(cleaned)
    except (ValueError, TypeError):
        return 0.0


def extract_keywords(text: str, min_length: int = 3) -> list[str]:
    """
    Extract keywords from text.

    Args:
        text: Input text
        min_length: Minimum word length to include

    Returns:
        List of lowercase keywords
    """
    if not text:
        return []

    # Remove non-alphanumeric characters except spaces
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
    words = cleaned.split()

    # Filter by length and remove duplicates while preserving order
    seen = set()
    keywords = []
    for word in words:
        if len(word) >= min_length and word not in seen:
            seen.add(word)
            keywords.append(word)

    return keywords


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length with a suffix.

    Args:
        text: Input text
        max_length: Maximum length including suffix
        suffix: Suffix to append when truncated

    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text or ""

    # Handle edge case where max_length is too small
    if max_length <= 0:
        return ""
    if max_length <= len(suffix):
        return suffix[:max_length]

    return text[: max_length - len(suffix)] + suffix
