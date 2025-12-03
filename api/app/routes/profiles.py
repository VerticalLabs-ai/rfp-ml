"""
Company Profile management API endpoints.
"""

import re
from datetime import datetime

from app.dependencies import DBDep
from app.models.database import CompanyProfile
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

router = APIRouter()


# Pydantic schemas
class CompanyProfileBase(BaseModel):
    name: str
    legal_name: str | None = None
    is_default: bool = False

    # Identifiers
    uei: str | None = None
    cage_code: str | None = None
    duns_number: str | None = None

    # Contact Information
    headquarters: str | None = None
    website: str | None = None
    primary_contact_name: str | None = None
    primary_contact_email: str | None = None
    primary_contact_phone: str | None = None

    # Business Information
    established_year: int | None = None
    employee_count: str | None = None
    certifications: list[str] = []
    naics_codes: list[str] = []
    core_competencies: list[str] = []
    past_performance: list[dict] = []

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Name cannot be empty")
        if len(v) > 255:
            raise ValueError("Name exceeds maximum length of 255 characters")
        return v.strip()

    @field_validator("uei")
    @classmethod
    def validate_uei(cls, v: str | None) -> str | None:
        if v and not re.match(r"^[A-Z0-9]{12}$", v.upper()):
            raise ValueError("UEI must be 12 alphanumeric characters")
        return v.upper() if v else v

    @field_validator("cage_code")
    @classmethod
    def validate_cage_code(cls, v: str | None) -> str | None:
        if v and not re.match(r"^[A-Z0-9]{5}$", v.upper()):
            raise ValueError("CAGE code must be 5 alphanumeric characters")
        return v.upper() if v else v

    @field_validator("naics_codes")
    @classmethod
    def validate_naics_codes(cls, v: list[str]) -> list[str]:
        for code in v:
            if not re.match(r"^\d{6}$", code):
                raise ValueError(
                    f"Invalid NAICS code format: {code}. Must be 6 digits."
                )
        return v


class CompanyProfileCreate(CompanyProfileBase):
    pass


class CompanyProfileUpdate(BaseModel):
    name: str | None = None
    legal_name: str | None = None
    is_default: bool | None = None
    uei: str | None = None
    cage_code: str | None = None
    duns_number: str | None = None
    headquarters: str | None = None
    website: str | None = None
    primary_contact_name: str | None = None
    primary_contact_email: str | None = None
    primary_contact_phone: str | None = None
    established_year: int | None = None
    employee_count: str | None = None
    certifications: list[str] | None = None
    naics_codes: list[str] | None = None
    core_competencies: list[str] | None = None
    past_performance: list[dict] | None = None


class CompanyProfileResponse(CompanyProfileBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=list[CompanyProfileResponse])
async def list_profiles(skip: int = 0, limit: int = 100, db: DBDep = ...):
    """Get all company profiles."""
    profiles = db.query(CompanyProfile).offset(skip).limit(limit).all()
    return profiles


@router.post("", response_model=CompanyProfileResponse)
async def create_profile(
    profile_data: CompanyProfileCreate, db: DBDep = ...,
):
    """Create a new company profile."""
    # Check for duplicate name
    existing = (
        db.query(CompanyProfile)
        .filter(CompanyProfile.name == profile_data.name)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400, detail="Profile with this name already exists"
        )

    # If this is the default, unset other defaults
    if profile_data.is_default:
        db.query(CompanyProfile).update({CompanyProfile.is_default: False})

    profile = CompanyProfile(**profile_data.model_dump())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/{profile_id}", response_model=CompanyProfileResponse)
async def get_profile(profile_id: int, db: DBDep):
    """Get a company profile by ID."""
    profile = db.query(CompanyProfile).filter(CompanyProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.put("/{profile_id}", response_model=CompanyProfileResponse)
async def update_profile(
    profile_id: int, profile_data: CompanyProfileUpdate, db: DBDep = ...,
):
    """Update a company profile."""
    profile = db.query(CompanyProfile).filter(CompanyProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    update_data = profile_data.model_dump(exclude_unset=True)

    # Check for duplicate name if name is being updated
    if "name" in update_data and update_data["name"] != profile.name:
        existing = (
            db.query(CompanyProfile)
            .filter(CompanyProfile.name == update_data["name"])
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=400, detail="Profile with this name already exists"
            )

    # If setting as default, unset other defaults
    if update_data.get("is_default"):
        db.query(CompanyProfile).filter(CompanyProfile.id != profile_id).update(
            {CompanyProfile.is_default: False}
        )

    for key, value in update_data.items():
        setattr(profile, key, value)

    db.commit()
    db.refresh(profile)
    return profile


@router.delete("/{profile_id}")
async def delete_profile(profile_id: int, db: DBDep):
    """Delete a company profile."""
    profile = db.query(CompanyProfile).filter(CompanyProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    db.delete(profile)
    db.commit()
    return {"message": "Profile deleted successfully"}


@router.post("/{profile_id}/default", response_model=CompanyProfileResponse)
async def set_default_profile(profile_id: int, db: DBDep):
    """Set a profile as the default."""
    profile = db.query(CompanyProfile).filter(CompanyProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Unset all other defaults
    db.query(CompanyProfile).update({CompanyProfile.is_default: False})

    # Set this profile as default
    profile.is_default = True
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/default/current", response_model=CompanyProfileResponse)
async def get_default_profile(db: DBDep):
    """Get the default company profile."""
    profile = db.query(CompanyProfile).filter(CompanyProfile.is_default == True).first()
    if not profile:
        raise HTTPException(status_code=404, detail="No default profile set")
    return profile
