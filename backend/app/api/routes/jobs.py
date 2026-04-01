"""Jobs API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.jobs import JobsResponse
from app.services.jobs.job_ingestion import JobIngestionService

router = APIRouter(prefix="/jobs", tags=["jobs"])
logger = logging.getLogger(__name__)


def get_job_ingestion_service() -> JobIngestionService:
    """Provide a configured job ingestion service.

    Provider registration is isolated in the providers package so new sources
    can be added without changing the API route layer.
    """
    from app.services.jobs.providers import get_configured_providers

    return JobIngestionService(providers=get_configured_providers())


@router.get("", response_model=JobsResponse)
async def list_jobs(
    job_ingestion_service: JobIngestionService = Depends(get_job_ingestion_service),
) -> JobsResponse:
    """Return normalized jobs for downstream scoring, filtering, and UI display."""
    try:
        jobs = await job_ingestion_service.ingest_jobs()
        return JobsResponse(jobs=jobs, total=len(jobs))
    except Exception as exc:
        logger.exception("Failed to list jobs.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load jobs at this time.",
        ) from exc