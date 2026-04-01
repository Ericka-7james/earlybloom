from __future__ import annotations

from fastapi import APIRouter, Query

from app.schemas.jobs import JobsListResponse, JobResponse
from app.services.jobs.job_ingestion import get_jobs

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=JobsListResponse)
def list_jobs(
    remote_only: bool = Query(default=False),
) -> JobsListResponse:
    """
    Return jobs for the frontend.

    Behavior:
    - Uses live providers when JOB_DATA_MODE=live
    - Uses mock data when JOB_DATA_MODE=mock
    - Falls back to mock data if live ingestion returns nothing usable
    """
    jobs = get_jobs(remote_only=remote_only)
    return JobsListResponse(jobs=[JobResponse(**job) for job in jobs])