from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ResumeLink(BaseModel):
    """Represents a labeled external link found on a resume."""

    model_config = ConfigDict(extra="forbid")

    label: Optional[str] = None
    url: str


class ResumeLocation(BaseModel):
    """Represents normalized location information for a resume."""

    model_config = ConfigDict(extra="forbid")

    raw: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None


class ResumeBasics(BaseModel):
    """Represents core personal information extracted from a resume."""

    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: ResumeLocation = Field(default_factory=ResumeLocation)
    links: List[ResumeLink] = Field(default_factory=list)


class ResumeEducation(BaseModel):
    """Represents an education entry extracted from a resume."""

    model_config = ConfigDict(extra="forbid")

    school: Optional[str] = None
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool = False


class ResumeExperience(BaseModel):
    """Represents a work experience entry extracted from a resume."""

    model_config = ConfigDict(extra="forbid")

    company: Optional[str] = None
    role: Optional[str] = None
    employment_type: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool = False
    location: Optional[str] = None
    bullet_points: List[str] = Field(default_factory=list)
    normalized_skills: List[str] = Field(default_factory=list)


class ResumeProject(BaseModel):
    """Represents a project entry extracted from a resume."""

    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = None
    description: Optional[str] = None
    tech_stack: List[str] = Field(default_factory=list)
    links: List[ResumeLink] = Field(default_factory=list)


class ResumeSkills(BaseModel):
    """Represents extracted resume skills."""

    model_config = ConfigDict(extra="forbid")

    raw: List[str] = Field(default_factory=list)
    normalized: List[str] = Field(default_factory=list)


class ResumeSummary(BaseModel):
    """Represents high-level ATS-style summary signals."""

    model_config = ConfigDict(extra="forbid")

    estimated_years_experience: int = 0
    seniority: str = "early_career"
    primary_role_signals: List[str] = Field(default_factory=list)
    top_skill_keywords: List[str] = Field(default_factory=list)


class ResumeMeta(BaseModel):
    """Represents parser metadata for a parsed resume."""

    model_config = ConfigDict(extra="forbid")

    parser_version: str = "v1"
    source_file_type: str = "application/pdf"
    parsed_at: datetime
    extraction_method: str = "text"
    confidence: float = 0.0

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        """Clamp parser confidence into the valid range.

        Args:
            value: Raw confidence value.

        Returns:
            A confidence value between 0.0 and 1.0.
        """
        return max(0.0, min(1.0, value))


class ParsedResume(BaseModel):
    """Represents the full structured parsed resume payload."""

    model_config = ConfigDict(extra="forbid")

    basics: ResumeBasics = Field(default_factory=ResumeBasics)
    education: List[ResumeEducation] = Field(default_factory=list)
    experience: List[ResumeExperience] = Field(default_factory=list)
    projects: List[ResumeProject] = Field(default_factory=list)
    skills: ResumeSkills = Field(default_factory=ResumeSkills)
    summary: ResumeSummary = Field(default_factory=ResumeSummary)
    meta: ResumeMeta

    def to_jsonb(self) -> Dict[str, Any]:
        """Convert the parsed resume into a JSON-serializable dictionary.

        Returns:
            JSON-serializable parsed resume data.
        """
        return self.model_dump(mode="json")


class ParseResumeRequest(BaseModel):
    """Represents a request to parse extracted resume text."""

    model_config = ConfigDict(extra="forbid")

    raw_text: str = Field(min_length=1, max_length=500_000)
    file_type: str = Field(default="application/pdf", max_length=128)
    extraction_method: str = Field(default="text", max_length=64)


class ParseResumeResponse(BaseModel):
    """Represents the API response returned after parsing a resume."""

    model_config = ConfigDict(extra="forbid")

    resume_id: str
    parse_status: str
    warnings: List[str] = Field(default_factory=list)
    parsed_json: Dict[str, Any]
    raw_text_preview: str
    ats_tags: List[str] = Field(default_factory=list)


class ResumeLogResponse(BaseModel):
    """Represents a resume processing log entry."""

    model_config = ConfigDict(extra="forbid")

    id: str
    resume_id: str
    user_id: str
    event_type: str
    event_status: str
    message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ResumeRecordResponse(BaseModel):
    """Represents a stored resume record returned to the client."""

    model_config = ConfigDict(extra="forbid")

    id: str
    user_id: str
    original_filename: Optional[str] = None
    file_size_bytes: Optional[int] = None
    file_type: Optional[str] = None
    upload_source: Optional[str] = None
    storage_path: Optional[str] = None
    parse_status: str
    raw_text: Optional[str] = None
    parsed_json: Optional[Dict[str, Any]] = None
    ats_tags: List[str] = Field(default_factory=list)
    parse_warnings: List[str] = Field(default_factory=list)
    latest_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime