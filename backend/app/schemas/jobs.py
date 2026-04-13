"""Schemas for jobs API responses and internal normalization."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


RemoteType = Literal["remote", "hybrid", "onsite", "unknown"]
ExperienceLevel = Literal[
    "entry-level",
    "junior",
    "mid-level",
    "senior",
    "unknown",
]
RoleType = Literal[
    "frontend",
    "backend",
    "full-stack",
    "software-engineering",
    "mobile",
    "data",
    "data-engineering",
    "data-analyst",
    "machine-learning",
    "ai",
    "devops",
    "sre",
    "cloud",
    "infrastructure",
    "cybersecurity",
    "qa",
    "test-automation",
    "product",
    "product-design",
    "ux",
    "solutions-engineering",
    "technical-support",
    "it",
    "business-analyst",
    "platform",
    "developer-tools",
    "unknown",
]


class NormalizedJob(BaseModel):
    """Shared normalized job payload used throughout the backend."""

    id: str = Field(..., description="Stable identifier for deduplication and UI use")
    title: str
    company: str
    location: str = ""
    location_display: str = ""

    remote: bool = False
    remote_type: RemoteType = "unknown"

    url: HttpUrl | str
    source: str
    source_job_id: str | None = None

    summary: str = ""
    description: str = ""

    responsibilities: list[str] = Field(default_factory=list)
    qualifications: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)

    employment_type: str | None = None
    experience_level: ExperienceLevel = "unknown"
    role_type: RoleType = "unknown"

    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = "USD"

    # Internal shared-cache metadata
    stable_key: str | None = None
    provider_payload_hash: str | None = None

    @field_validator(
        "title",
        "company",
        "location",
        "location_display",
        "summary",
        "description",
        mode="before",
    )
    @classmethod
    def normalize_text_fields(cls, value: object) -> str:
        """Normalize string-like text fields into compact readable text."""
        return " ".join(str(value or "").strip().split())

    @field_validator("source", mode="before")
    @classmethod
    def normalize_source(cls, value: object) -> str:
        """Normalize source name casing."""
        return str(value or "unknown").strip().lower()

    @field_validator(
        "source_job_id",
        "employment_type",
        "salary_currency",
        "stable_key",
        "provider_payload_hash",
        mode="before",
    )
    @classmethod
    def normalize_optional_strings(cls, value: object) -> str | None:
        """Normalize optional string fields and collapse empty strings to None."""
        text = str(value or "").strip()
        return text or None

    @field_validator(
        "responsibilities",
        "qualifications",
        "required_skills",
        "preferred_skills",
        mode="before",
    )
    @classmethod
    def normalize_string_lists(cls, value: object) -> list[str]:
        """Normalize list fields into cleaned string lists."""
        if not isinstance(value, list):
            return []

        cleaned: list[str] = []
        seen: set[str] = set()

        for item in value:
            text = " ".join(str(item or "").strip().split())
            if not text:
                continue

            key = text.casefold()
            if key in seen:
                continue

            seen.add(key)
            cleaned.append(text)

        return cleaned

    @field_validator("salary_min", "salary_max", mode="before")
    @classmethod
    def normalize_salary_numbers(cls, value: object) -> int | None:
        """Coerce salary-like values to integers when possible."""
        if value is None or value == "":
            return None

        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None


class JobViewerState(BaseModel):
    """Viewer-specific save/hide state layered on top of shared jobs."""

    is_saved: bool = False
    is_hidden: bool = False
    saved_at: str | None = None
    hidden_at: str | None = None


class PublicJob(NormalizedJob):
    """Public job payload returned to the frontend."""

    viewer_state: JobViewerState = Field(default_factory=JobViewerState)


class JobsResponse(BaseModel):
    """Response payload for jobs-like endpoints."""

    jobs: list[PublicJob]
    total: int


class JobQueryParams(BaseModel):
    """Normalized query params used to build shared query-cache keys."""

    remote_only: bool = False
    levels: list[str] = Field(default_factory=list)
    role_types: list[str] = Field(default_factory=list)

    @field_validator("levels", "role_types", mode="before")
    @classmethod
    def normalize_query_lists(cls, value: object) -> list[str]:
        """Normalize query list params into stripped lowercase values."""
        if value is None:
            return []

        if not isinstance(value, list):
            value = [value]

        normalized: list[str] = []
        seen: set[str] = set()

        for item in value:
            text = str(item or "").strip().lower()
            if not text or text in seen:
                continue
            seen.add(text)
            normalized.append(text)

        return normalized


class JobTrackerMutationRequest(BaseModel):
    """Signed-in tracker mutation request body."""

    job_id: str = Field(..., min_length=1)


class JobTrackerMutationResponse(BaseModel):
    """Tracker mutation response payload."""

    job_id: str
    viewer_state: JobViewerState


class ResolvedJobProfileResponse(BaseModel):
    """Frontend-friendly resolved profile shape used by the jobs page."""

    desiredLevels: list[str] = Field(
        default_factory=lambda: ["entry-level", "junior"]
    )
    preferredRoleTypes: list[str] = Field(default_factory=list)
    preferredWorkplaceTypes: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    isLgbtFriendlyOnly: bool = False


class JobIngestionSummary(BaseModel):
    """Optional debug/admin shape for ingestion status visibility."""

    provider: str
    query_key: str
    status: str
    raw_count: int = 0
    normalized_count: int = 0
    deduped_count: int = 0
    error_message: str | None = None