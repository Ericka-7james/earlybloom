from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from supabase import Client, create_client

from app.core.config import get_settings
from app.schemas.jobs import NormalizedJob

settings = get_settings()
SUPABASE_URL = (settings.SUPABASE_URL or "").strip()
SUPABASE_SECRET_KEY = (settings.SUPABASE_SECRET_KEY or "").strip()

if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
    raise RuntimeError(
        "Missing SUPABASE_URL or SUPABASE_SECRET_KEY for backend database access."
    )

_supabase_admin: Client | None = None


def get_supabase_admin() -> Client:
    """Return a cached Supabase admin client."""
    global _supabase_admin

    if _supabase_admin is None:
        _supabase_admin = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

    return _supabase_admin


def get_user_id_from_bearer_token(authorization_header: Optional[str]) -> str:
    """Resolve the authenticated Supabase user ID from a bearer token."""
    if not authorization_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header.",
        )

    prefix = "Bearer "
    if not authorization_header.startswith(prefix):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format.",
        )

    access_token = authorization_header[len(prefix):].strip()
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )

    supabase = get_supabase_admin()

    try:
        response = supabase.auth.get_user(access_token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate Supabase access token.",
        ) from exc

    user = getattr(response, "user", None)
    user_id = getattr(user, "id", None)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Supabase user could not be resolved from token.",
        )

    return str(user_id)


class JobCacheRepository:
    """Repository for shared normalized jobs cache stored in Supabase."""

    def __init__(self, client: Client | None = None) -> None:
        self.client = client or get_supabase_admin()

    def list_active_jobs(self, *, limit: int = 250) -> list[Dict[str, Any]]:
        """Return active cached jobs, newest seen first."""
        result = (
            self.client.table("jobs_cache")
            .select("*")
            .eq("is_active", True)
            .order("last_seen_at", desc=True)
            .limit(limit)
            .execute()
        )

        rows = result.data or []
        now = datetime.now(timezone.utc)
        filtered: list[Dict[str, Any]] = []

        for row in rows:
            expires_at = _parse_timestamptz(row.get("expires_at"))
            if expires_at is not None and expires_at <= now:
                continue
            filtered.append(row)

        return filtered

    def list_active_jobs_by_ids(self, job_ids: list[str]) -> list[Dict[str, Any]]:
        """Return active jobs matching the provided stable keys."""
        if not job_ids:
            return []

        result = (
            self.client.table("jobs_cache")
            .select("*")
            .eq("is_active", True)
            .in_("stable_key", job_ids)
            .execute()
        )

        rows = result.data or []
        now = datetime.now(timezone.utc)
        filtered: list[Dict[str, Any]] = []

        for row in rows:
            expires_at = _parse_timestamptz(row.get("expires_at"))
            if expires_at is not None and expires_at <= now:
                continue
            filtered.append(row)

        return filtered

    def upsert_jobs(
        self,
        jobs: list[NormalizedJob],
        *,
        ttl_days: int = 14,
        ingestion_run_id: str | None = None,
    ) -> list[Dict[str, Any]]:
        """Upsert normalized jobs into the shared jobs cache."""
        if not jobs:
            return []

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=ttl_days)

        payload = [
            self._job_to_row(
                job=job,
                last_seen_at=now,
                expires_at=expires_at,
                ingestion_run_id=ingestion_run_id,
            )
            for job in jobs
        ]

        result = (
            self.client.table("jobs_cache")
            .upsert(payload, on_conflict="stable_key")
            .execute()
        )

        return result.data or []

    def get_query_cache(self, *, cache_key: str) -> Dict[str, Any] | None:
        result = (
            self.client.table("job_query_cache")
            .select("*")
            .eq("cache_key", cache_key)
            .limit(1)
            .execute()
        )

        rows = result.data or []
        if not rows:
            return None

        row = rows[0]
        expires_at = _parse_timestamptz(row.get("expires_at"))
        now = datetime.now(timezone.utc)

        if expires_at is not None and expires_at <= now:
            return None

        return row

    def upsert_query_cache(
        self,
        *,
        cache_key: str,
        query_params: Dict[str, Any],
        job_ids: list[str],
        viewer_scope: str = "public",
        ttl_seconds: int = 300,
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=ttl_seconds)

        result = (
            self.client.table("job_query_cache")
            .upsert(
                {
                    "cache_key": cache_key,
                    "query_params": query_params,
                    "job_ids": job_ids,
                    "viewer_scope": viewer_scope,
                    "expires_at": expires_at.isoformat(),
                },
                on_conflict="cache_key",
            )
            .execute()
        )

        data = result.data or []
        return data[0] if data else {}

    def create_ingestion_run(
        self,
        *,
        provider: str,
        query_key: str,
        status_value: str = "running",
        metadata: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        result = (
            self.client.table("job_ingestion_runs")
            .insert(
                {
                    "provider": provider,
                    "query_key": query_key,
                    "status": status_value,
                    "metadata": metadata or {},
                }
            )
            .execute()
        )

        data = result.data or []
        return data[0] if data else {}

    def complete_ingestion_run(
        self,
        *,
        run_id: str,
        status_value: str,
        raw_count: int = 0,
        normalized_count: int = 0,
        deduped_count: int = 0,
        error_message: str | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        result = (
            self.client.table("job_ingestion_runs")
            .update(
                {
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "status": status_value,
                    "raw_count": raw_count,
                    "normalized_count": normalized_count,
                    "deduped_count": deduped_count,
                    "error_message": error_message,
                    "metadata": metadata or {},
                }
            )
            .eq("id", run_id)
            .execute()
        )

        data = result.data or []
        return data[0] if data else {}

    def has_recent_successful_run(
        self,
        *,
        provider: str,
        query_key: str,
        within_seconds: int,
    ) -> bool:
        cutoff_iso = (
            datetime.now(timezone.utc) - timedelta(seconds=within_seconds)
        ).isoformat()

        result = (
            self.client.table("job_ingestion_runs")
            .select("id")
            .eq("provider", provider)
            .eq("query_key", query_key)
            .eq("status", "success")
            .gte("completed_at", cutoff_iso)
            .limit(1)
            .execute()
        )

        return bool(result.data)

    def has_running_ingestion(
        self,
        *,
        provider: str,
        query_key: str,
        within_seconds: int,
    ) -> bool:
        cutoff_iso = (
            datetime.now(timezone.utc) - timedelta(seconds=within_seconds)
        ).isoformat()

        result = (
            self.client.table("job_ingestion_runs")
            .select("id")
            .eq("provider", provider)
            .eq("query_key", query_key)
            .eq("status", "running")
            .gte("started_at", cutoff_iso)
            .limit(1)
            .execute()
        )

        return bool(result.data)

    def mark_expired_jobs_inactive(self) -> list[Dict[str, Any]]:
        """Mark expired jobs inactive."""
        now_iso = datetime.now(timezone.utc).isoformat()

        result = (
            self.client.table("jobs_cache")
            .update({"is_active": False})
            .eq("is_active", True)
            .lte("expires_at", now_iso)
            .execute()
        )

        return result.data or []

    def delete_long_expired_jobs(self, *, grace_hours: int = 48) -> list[Dict[str, Any]]:
        """Delete jobs that have been expired longer than the grace window."""
        cutoff_iso = (
            datetime.now(timezone.utc) - timedelta(hours=grace_hours)
        ).isoformat()

        result = (
            self.client.table("jobs_cache")
            .delete()
            .lte("expires_at", cutoff_iso)
            .execute()
        )

        return result.data or []

    def cleanup_expired_jobs(self, *, grace_hours: int = 48) -> Dict[str, int]:
        marked_inactive = self.mark_expired_jobs_inactive()
        deleted = self.delete_long_expired_jobs(grace_hours=grace_hours)

        return {
            "marked_inactive": len(marked_inactive),
            "deleted": len(deleted),
        }

    def row_to_normalized_job(self, row: Dict[str, Any]) -> NormalizedJob | None:
        """Convert a jobs_cache row into a NormalizedJob model."""
        try:
            return NormalizedJob(
                id=str(
                    row.get("normalized_job_id")
                    or row.get("stable_key")
                    or row.get("id")
                    or ""
                ),
                title=str(row.get("title") or ""),
                company=str(row.get("company") or ""),
                location=str(row.get("location") or ""),
                remote=bool(row.get("remote")),
                remote_type=str(row.get("remote_type") or "unknown"),
                url=str(row.get("url") or ""),
                source=str(row.get("source") or "unknown"),
                summary=str(row.get("summary") or ""),
                description=str(row.get("description") or ""),
                responsibilities=_coerce_string_list(row.get("responsibilities")),
                qualifications=_coerce_string_list(row.get("qualifications")),
                required_skills=_coerce_string_list(row.get("required_skills")),
                preferred_skills=_coerce_string_list(row.get("preferred_skills")),
                employment_type=row.get("employment_type"),
                experience_level=str(row.get("experience_level") or "unknown"),
                salary_min=_coerce_int(row.get("salary_min")),
                salary_max=_coerce_int(row.get("salary_max")),
                salary_currency=row.get("salary_currency"),
            )
        except Exception:
            return None

    def build_query_cache_key(
        self,
        *,
        remote_only: bool,
        levels: list[str] | None,
        role_types: list[str] | None,
    ) -> str:
        payload = {
            "remote_only": bool(remote_only),
            "levels": sorted(str(x).strip().lower() for x in (levels or [])),
            "role_types": sorted(str(x).strip().lower() for x in (role_types or [])),
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return sha256(raw.encode("utf-8")).hexdigest()

    def _job_to_row(
        self,
        *,
        job: NormalizedJob,
        last_seen_at: datetime,
        expires_at: datetime,
        ingestion_run_id: str | None,
    ) -> Dict[str, Any]:
        stable_key = str(job.id).strip()
        if not stable_key:
            stable_key = _fallback_stable_key(job)

        return {
            "stable_key": stable_key,
            "normalized_job_id": stable_key,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "location_display": job.location,
            "remote": bool(job.remote),
            "remote_type": job.remote_type,
            "url": str(job.url),
            "source": job.source,
            "source_job_id": None,
            "summary": job.summary or "",
            "description": job.description or "",
            "responsibilities": job.responsibilities or [],
            "qualifications": job.qualifications or [],
            "required_skills": job.required_skills or [],
            "preferred_skills": job.preferred_skills or [],
            "employment_type": job.employment_type,
            "experience_level": job.experience_level,
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "salary_currency": job.salary_currency,
            "last_seen_at": last_seen_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "is_active": True,
            "ingestion_run_id": ingestion_run_id,
        }


class ResumeRepository:
    """Repository for resume records and resume processing logs."""
    def __init__(self, client: Client | None = None) -> None:
        self.client = client or get_supabase_admin()

    def get_resume_for_user(self, resume_id: str, user_id: str) -> Dict[str, Any]:
        result = (
            self.client.table("resumes")
            .select("*")
            .eq("id", resume_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )

        data = result.data or []
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found.",
            )

        return data[0]

    def get_latest_resume_for_user(self, user_id: str) -> Dict[str, Any]:
        result = (
            self.client.table("resumes")
            .select("*")
            .eq("user_id", user_id)
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )

        data = result.data or []
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found.",
            )

        return data[0]

    def update_resume_parse_result(
        self,
        *,
        resume_id: str,
        user_id: str,
        parse_status: str,
        raw_text: Optional[str] = None,
        parsed_json: Optional[Dict[str, Any]] = None,
        parse_warnings: Optional[list[str]] = None,
        latest_error: Optional[str] = None,
        ats_tags: Optional[list[str]] = None,
    ) -> Dict[str, Any]:
        update_payload: Dict[str, Any] = {
            "parse_status": parse_status,
            "parse_warnings": parse_warnings or [],
            "latest_error": latest_error,
        }

        if raw_text is not None:
            update_payload["raw_text"] = raw_text

        if parsed_json is not None:
            update_payload["parsed_json"] = parsed_json

        if ats_tags is not None:
            update_payload["ats_tags"] = ats_tags

        result = (
            self.client.table("resumes")
            .update(update_payload)
            .eq("id", resume_id)
            .eq("user_id", user_id)
            .execute()
        )

        data = result.data or []
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found or update failed.",
            )

        return data[0]

    def create_resume_log(
        self,
        *,
        resume_id: str,
        user_id: str,
        event_type: str,
        event_status: str = "info",
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        result = (
            self.client.table("resume_logs")
            .insert(
                {
                    "resume_id": resume_id,
                    "user_id": user_id,
                    "event_type": event_type,
                    "event_status": event_status,
                    "message": message,
                    "metadata": metadata or {},
                }
            )
            .execute()
        )

        data = result.data or []
        if not data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create resume log.",
            )

        return data[0]

    def list_resume_logs(self, *, resume_id: str, user_id: str) -> list[Dict[str, Any]]:
        result = (
            self.client.table("resume_logs")
            .select("*")
            .eq("resume_id", resume_id)
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )

        return result.data or []


def _fallback_stable_key(job: NormalizedJob) -> str:
    raw = json.dumps(
        {
            "source": str(job.source or "").strip().lower(),
            "title": str(job.title or "").strip().lower(),
            "company": str(job.company or "").strip().lower(),
            "location": str(job.location or "").strip().lower(),
            "url": str(job.url or "").strip().lower(),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(raw.encode("utf-8")).hexdigest()


def _coerce_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _coerce_int(value: Any) -> int | None:
    if value is None or value == "":
        return None

    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _parse_timestamptz(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None

    try:
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        return datetime.fromisoformat(raw)
    except ValueError:
        return None