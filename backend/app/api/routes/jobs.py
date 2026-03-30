from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter

from app.services.job_ingestion import get_jobs as get_jobs_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=Dict[str, List[Dict[str, Any]]])
def list_jobs() -> Dict[str, List[Dict[str, Any]]]:
    return {"jobs": get_jobs_service()}