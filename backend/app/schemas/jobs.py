"""Schemas for jobs API responses and internal normalization."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


RemoteType = Literal["remote", "hybrid", "onsite", "unknown"]
ExperienceLevel = Literal[
    "entry-level",
    "junior",
    "mid-level",
    "senior",
    "unknown",
]


class NormalizedJob(BaseModel):
    """Shared normalized job payload used throughout the backend."""

    id: str = Field(..., description="Stable identifier for deduplication and UI use")
    title: str
    company: str
    location: str
    remote: bool = False
    remote_type: RemoteType = "unknown"
    url: HttpUrl | str
    source: str

    summary: str = ""
    description: str = ""

    responsibilities: list[str] = Field(default_factory=list)
    qualifications: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)

    employment_type: str | None = None
    experience_level: ExperienceLevel = "unknown"

    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = "USD"


class JobsResponse(BaseModel):
    """Response payload for the jobs endpoint."""

    jobs: list[NormalizedJob]
    total: int