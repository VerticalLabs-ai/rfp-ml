"""
Database seeding for initial data setup.
"""
import logging

from sqlalchemy.orm import Session

from app.models.database import CompanyProfile

logger = logging.getLogger(__name__)

# IBYTE Enterprises company profile data
IBYTE_PROFILE = {
    "name": "IBYTE Enterprises",
    "legal_name": "IBYTE Enterprises, LLC",
    "is_default": True,
    "uei": "LF25E13Q29E6",
    "duns_number": "132971889",
    "cage_code": None,  # Add when available
    "headquarters": "1801 E 51st St. Ste 365-359, Austin, TX 78723",
    "website": "https://www.ibyteent.com",
    "primary_contact_name": "Valorie A Rodriguez",
    "primary_contact_email": "vrodriguez@ibyteent.com",
    "primary_contact_phone": "512-800-3890",
    "established_year": 2022,
    "employee_count": "1-10",
    "certifications": [
        "Small Business",
        "Woman Owned Small Business (WOSB)",
        "PMP Certificate #3889480"
    ],
    "naics_codes": [
        {"code": "236220", "description": "Commercial and Institutional Building Construction"},
        {"code": "541512", "description": "Computer Systems Design Services"},
        {"code": "541519", "description": "Other Computer Related Services"},
        {"code": "541611", "description": "Administrative Management and General Management Consulting Services"},
        {"code": "541618", "description": "Other Management Consulting Services"},
        {"code": "518210", "description": "Data Processing, Hosting, and Related Services"},
        {"code": "541511", "description": "Custom Computer Programming Services"},
        {"code": "541330", "description": "Engineering Services"},
        {"code": "541310", "description": "Architectural Services"}
    ],
    "core_competencies": [
        "IT Infrastructure & Cloud Services",
        "Project Management",
        "Software Development",
        "Digital Transformation",
        "Construction Management",
        "Data Analytics",
        "Government Contracting"
    ],
    "past_performance": []  # Can be populated with contract history
}


def seed_company_profile(db: Session) -> None:
    """Seed IBYTE Enterprises company profile if it doesn't exist."""
    existing = db.query(CompanyProfile).filter(
        CompanyProfile.name == IBYTE_PROFILE["name"]
    ).first()

    if existing:
        logger.info(f"Company profile '{IBYTE_PROFILE['name']}' already exists, skipping seed")
        return

    # Create new profile
    profile = CompanyProfile(
        name=IBYTE_PROFILE["name"],
        legal_name=IBYTE_PROFILE["legal_name"],
        is_default=IBYTE_PROFILE["is_default"],
        uei=IBYTE_PROFILE["uei"],
        duns_number=IBYTE_PROFILE["duns_number"],
        cage_code=IBYTE_PROFILE["cage_code"],
        headquarters=IBYTE_PROFILE["headquarters"],
        website=IBYTE_PROFILE["website"],
        primary_contact_name=IBYTE_PROFILE["primary_contact_name"],
        primary_contact_email=IBYTE_PROFILE["primary_contact_email"],
        primary_contact_phone=IBYTE_PROFILE["primary_contact_phone"],
        established_year=IBYTE_PROFILE["established_year"],
        employee_count=IBYTE_PROFILE["employee_count"],
        certifications=IBYTE_PROFILE["certifications"],
        naics_codes=IBYTE_PROFILE["naics_codes"],
        core_competencies=IBYTE_PROFILE["core_competencies"],
        past_performance=IBYTE_PROFILE["past_performance"]
    )

    db.add(profile)
    db.commit()
    logger.info(f"✅ Seeded company profile: {IBYTE_PROFILE['name']}")


def run_seeds(db: Session) -> None:
    """Run all database seeds."""
    logger.info("Running database seeds...")
    seed_company_profile(db)
    logger.info("Database seeding complete")
