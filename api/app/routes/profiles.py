"""
Company Profile management API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.models.database import CompanyProfile

router = APIRouter()


# Pydantic schemas
class CompanyProfileBase(BaseModel):
    name: str
    legal_name: Optional[str] = None
    is_default: bool = False

    # Identifiers
    uei: Optional[str] = None
    cage_code: Optional[str] = None
    duns_number: Optional[str] = None

    # Contact Information
    headquarters: Optional[str] = None
    website: Optional[str] = None
    primary_contact_name: Optional[str] = None
    primary_contact_email: Optional[str] = None
    primary_contact_phone: Optional[str] = None

    # Business Information
    established_year: Optional[int] = None
    employee_count: Optional[str] = None
    certifications: List[str] = []
    naics_codes: List[str] = []
    core_competencies: List[str] = []
    past_performance: List[dict] = []


class CompanyProfileCreate(CompanyProfileBase):
    pass


class CompanyProfileUpdate(BaseModel):
    name: Optional[str] = None
    legal_name: Optional[str] = None
    is_default: Optional[bool] = None
    uei: Optional[str] = None
    cage_code: Optional[str] = None
    duns_number: Optional[str] = None
    headquarters: Optional[str] = None
    website: Optional[str] = None
    primary_contact_name: Optional[str] = None
    primary_contact_email: Optional[str] = None
    primary_contact_phone: Optional[str] = None
    established_year: Optional[int] = None
    employee_count: Optional[str] = None
    certifications: Optional[List[str]] = None
    naics_codes: Optional[List[str]] = None
    core_competencies: Optional[List[str]] = None
    past_performance: Optional[List[dict]] = None


class CompanyProfileResponse(CompanyProfileBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=List[CompanyProfileResponse])
async def list_profiles(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all company profiles."""
    profiles = db.query(CompanyProfile).offset(skip).limit(limit).all()
    return profiles


@router.post("", response_model=CompanyProfileResponse)
async def create_profile(
    profile_data: CompanyProfileCreate,
    db: Session = Depends(get_db)
):
    """Create a new company profile."""
    # Check for duplicate name
    existing = db.query(CompanyProfile).filter(CompanyProfile.name == profile_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Profile with this name already exists")

    # If this is the default, unset other defaults
    if profile_data.is_default:
        db.query(CompanyProfile).update({CompanyProfile.is_default: False})

    profile = CompanyProfile(**profile_data.model_dump())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/{profile_id}", response_model=CompanyProfileResponse)
async def get_profile(profile_id: int, db: Session = Depends(get_db)):
    """Get a company profile by ID."""
    profile = db.query(CompanyProfile).filter(CompanyProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.put("/{profile_id}", response_model=CompanyProfileResponse)
async def update_profile(
    profile_id: int,
    profile_data: CompanyProfileUpdate,
    db: Session = Depends(get_db)
):
    """Update a company profile."""
    profile = db.query(CompanyProfile).filter(CompanyProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    update_data = profile_data.model_dump(exclude_unset=True)

    # Check for duplicate name if name is being updated
    if "name" in update_data and update_data["name"] != profile.name:
        existing = db.query(CompanyProfile).filter(CompanyProfile.name == update_data["name"]).first()
        if existing:
            raise HTTPException(status_code=400, detail="Profile with this name already exists")

    # If setting as default, unset other defaults
    if update_data.get("is_default"):
        db.query(CompanyProfile).filter(CompanyProfile.id != profile_id).update({CompanyProfile.is_default: False})

    for key, value in update_data.items():
        setattr(profile, key, value)

    db.commit()
    db.refresh(profile)
    return profile


@router.delete("/{profile_id}")
async def delete_profile(profile_id: int, db: Session = Depends(get_db)):
    """Delete a company profile."""
    profile = db.query(CompanyProfile).filter(CompanyProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    db.delete(profile)
    db.commit()
    return {"message": "Profile deleted successfully"}


@router.post("/{profile_id}/default", response_model=CompanyProfileResponse)
async def set_default_profile(profile_id: int, db: Session = Depends(get_db)):
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
async def get_default_profile(db: Session = Depends(get_db)):
    """Get the default company profile."""
    profile = db.query(CompanyProfile).filter(CompanyProfile.is_default == True).first()
    if not profile:
        raise HTTPException(status_code=404, detail="No default profile set")
    return profile
