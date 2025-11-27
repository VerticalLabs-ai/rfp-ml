"""
Category detection utilities for RFP classification.
Centralizes the category determination logic used across multiple modules.
"""
from enum import Enum
from typing import Dict, Any


class CategoryType(str, Enum):
    """Supported RFP categories."""
    BOTTLED_WATER = "bottled_water"
    CONSTRUCTION = "construction"
    DELIVERY = "delivery"
    MAINTENANCE = "maintenance"
    IT_SERVICES = "it_services"
    PROFESSIONAL_SERVICES = "professional_services"
    GENERAL = "general"


# Category detection keywords mapped to categories
CATEGORY_KEYWORDS: Dict[CategoryType, list[str]] = {
    CategoryType.BOTTLED_WATER: ["water", "beverage", "bottle"],
    CategoryType.CONSTRUCTION: ["construction", "building", "infrastructure", "renovation", "paving"],
    CategoryType.DELIVERY: ["delivery", "transport", "logistics", "shipping"],
    CategoryType.MAINTENANCE: ["maintenance", "repair", "service"],
    CategoryType.IT_SERVICES: ["software", "technology", "system", "network", "it", "cloud"],
}

# NAICS code prefixes mapped to categories
NAICS_CATEGORY_MAP: Dict[str, CategoryType] = {
    "54": CategoryType.PROFESSIONAL_SERVICES,  # Professional, Scientific, Technical Services
    "23": CategoryType.CONSTRUCTION,            # Construction
    "48": CategoryType.DELIVERY,                # Transportation
    "49": CategoryType.DELIVERY,                # Postal and Warehousing
    "51": CategoryType.IT_SERVICES,             # Information
    "81": CategoryType.MAINTENANCE,             # Other Services (Repair/Maintenance)
}


def determine_category(rfp_data: Dict[str, Any]) -> str:
    """
    Determine the category of an RFP based on title, description, and NAICS code.

    Args:
        rfp_data: Dictionary containing RFP information with optional keys:
            - title: RFP title
            - description: RFP description
            - naics_code: NAICS classification code

    Returns:
        Category string (one of CategoryType values)

    Examples:
        >>> determine_category({"title": "Bottled Water Supply"})
        'bottled_water'
        >>> determine_category({"description": "Road construction project"})
        'construction'
        >>> determine_category({"naics_code": "541512"})
        'professional_services'
    """
    title = str(rfp_data.get("title", "")).lower()
    description = str(rfp_data.get("description", "")).lower()
    naics_code = str(rfp_data.get("naics_code", ""))

    combined_text = title + " " + description

    # Check keyword-based categories first (more specific)
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in combined_text for keyword in keywords):
            return category.value

    # Fall back to NAICS code mapping
    for prefix, category in NAICS_CATEGORY_MAP.items():
        if naics_code.startswith(prefix):
            return category.value

    # Default category
    return CategoryType.PROFESSIONAL_SERVICES.value


def get_category_keywords(category: str) -> list[str]:
    """
    Get the keywords associated with a category.

    Args:
        category: Category string

    Returns:
        List of keywords for the category, or empty list if not found
    """
    try:
        cat_type = CategoryType(category)
        return CATEGORY_KEYWORDS.get(cat_type, [])
    except ValueError:
        return []
