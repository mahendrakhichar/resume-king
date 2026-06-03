"""Pydantic schemas for resume-related API requests and responses."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, Any, List

from pydantic import BaseModel, Field, model_validator


# ─── Parsed Resume Sub-Models ───────────────────────────────────────

class ContactInfo(BaseModel):
    """Parsed contact information from a resume."""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    location: Optional[str] = None


class Education(BaseModel):
    """A single education entry."""
    institution: Optional[str] = "Unknown"
    degree: Optional[str] = "Unknown"
    field_of_study: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    gpa: Optional[str] = None
    highlights: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def clean_null_lists(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "highlights" in data and data["highlights"] is None:
                data["highlights"] = []
        return data


class Experience(BaseModel):
    """A single work experience entry."""
    company: Optional[str] = "Unknown"
    title: Optional[str] = "Unknown"
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool = False
    bullets: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def clean_null_lists(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "bullets" in data and data["bullets"] is None:
                data["bullets"] = []
            if "is_current" in data and (data["is_current"] is None or data["is_current"] == ""):
                data["is_current"] = False
        return data


class Project(BaseModel):
    """A single project entry."""
    name: Optional[str] = "Unknown"
    description: Optional[str] = None
    technologies: list[str] = Field(default_factory=list)
    url: Optional[str] = None
    bullets: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def clean_null_lists(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for field in ["technologies", "bullets"]:
                if field in data and data[field] is None:
                    data[field] = []
        return data


class Certification(BaseModel):
    """A single certification entry."""
    name: Optional[str] = "Unknown"
    issuer: Optional[str] = None
    date: Optional[str] = None
    url: Optional[str] = None


class ParsedResume(BaseModel):
    """Fully parsed and structured resume data."""
    contact: ContactInfo = Field(default_factory=ContactInfo)
    summary: Optional[str] = None
    skills: list[str] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def clean_null_lists(cls, data: Any) -> Any:
        if isinstance(data, dict):
            list_fields = ["skills", "experience", "education", "projects", "certifications", "achievements", "languages"]
            for field in list_fields:
                if field in data and data[field] is None:
                    data[field] = []
            
            # Resilient parsing of achievements: if it is a list of dicts instead of list of strings, extract description or name
            if "achievements" in data and isinstance(data["achievements"], list):
                cleaned_achievements = []
                for item in data["achievements"]:
                    if isinstance(item, dict):
                        val = item.get("description") or item.get("name") or item.get("text") or str(item)
                        if val:
                            cleaned_achievements.append(val)
                    elif isinstance(item, str):
                        cleaned_achievements.append(item)
                data["achievements"] = cleaned_achievements

            # Resilient experience parsing pre-cleaning
            if "experience" in data and isinstance(data["experience"], list):
                for exp in data["experience"]:
                    if isinstance(exp, dict):
                        if "is_current" in exp and (exp["is_current"] is None or exp["is_current"] == ""):
                            exp["is_current"] = False
        return data


# ─── API Schemas ────────────────────────────────────────────────────

class ResumeUploadResponse(BaseModel):
    """Response after uploading and parsing a resume."""
    id: uuid.UUID
    original_filename: str
    file_type: str
    parsed_data: Optional[ParsedResume] = None
    raw_text: Optional[str] = None
    version: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ResumeListItem(BaseModel):
    """Lightweight resume item for list views."""
    id: uuid.UUID
    original_filename: str
    file_type: str
    version: int
    is_tailored: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ResumeDetail(BaseModel):
    """Full resume details including parsed data."""
    id: uuid.UUID
    original_filename: str
    file_type: str
    parsed_data: Optional[ParsedResume] = None
    raw_text: Optional[str] = None
    version: int
    is_tailored: bool
    parent_id: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = {"from_attributes": True}
