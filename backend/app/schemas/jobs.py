from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class JobResponse(BaseModel):
    id: str
    title: str
    company_name: str
    location: str
    description: str
    source: str
    url: Optional[str] = None
    employment_type: Optional[str] = None
    experience_level: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = "USD"
    requirements: list[str] = []


class JobsListResponse(BaseModel):
    jobs: list[JobResponse]