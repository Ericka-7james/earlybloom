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

# Matches the actual FK column name in user_saved_jobs and user_hidden_jobs.
TRACKER_JOB_FK_COLUMN = "job_cache_id"
USER_SAVED_JOBS_TABLE = "user_saved_jobs"
USER_HIDDEN_JOBS_TABLE = "user_hidden_jobs"


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

        return self._filter_unexpired_rows(result.data or [])

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

        return self._filter_unexpired_rows(result.data or [])

    def list_active_jobs_by_cache_row_ids(
        self,
        cache_row_ids: list[str],
    ) -> list[Dict[str, Any]]:
        """Return active jobs matching jobs_cache primary-key row ids."""
        if not cache_row_ids:
            return []

        result = (
            self.client.table("jobs_cache")
            .select("*")
            .eq("is_active", True)
            .in_("id", cache_row_ids)
            .execute()
        )

        return self._filter_unexpired_rows(result.data or [])

    def list_active_jobs_by_public_ids(
        self,
        public_job_ids: list[str],
    ) -> list[Dict[str, Any]]:
        """Return active jobs matching frontend/public job ids."""
        if not public_job_ids:
            return []

        normalized_ids = [
            str(job_id).strip() for job_id in public_job_ids if str(job_id).strip()
        ]
        if not normalized_ids:
            return []

        rows: list[Dict[str, Any]] = []

        result = (
            self.client.table("jobs_cache")
            .select("*")
            .eq("is_active", True)
            .in_("normalized_job_id", normalized_ids)
            .execute()
        )
        rows.extend(result.data or [])

        found_keys = {
            str(row.get("normalized_job_id") or row.get("stable_key") or "").strip()
            for row in rows
        }
        missing_ids = [job_id for job_id in normalized_ids if job_id not in found_keys]

        if missing_ids:
            fallback = (
                self.client.table("jobs_cache")
                .select("*")
                .eq("is_active", True)
                .in_("stable_key", missing_ids)
                .execute()
            )
            rows.extend(fallback.data or [])

        deduped_by_row_id: dict[str, Dict[str, Any]] = {}
        for row in rows:
            row_id = str(row.get("id") or "").strip()
            if row_id:
                deduped_by_row_id[row_id] = row

        return self._filter_unexpired_rows(list(deduped_by_row_id.values()))

    def get_active_job_by_public_id(self, public_job_id: str) -> Dict[str, Any]:
        """Resolve a frontend/public job id to the matching active jobs_cache row."""
        public_job_id = str(public_job_id or "").strip()
        if not public_job_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="job_id is required.",
            )

        rows = self.list_active_jobs_by_public_ids([public_job_id])
        if not rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job could not be found in the shared jobs cache.",
            )

        return rows[0]

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

    def delete_long_expired_jobs(
        self,
        *,
        grace_hours: int = 48,
    ) -> list[Dict[str, Any]]:
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
            stable_key = str(row.get("stable_key") or "").strip() or None

            return NormalizedJob(
                id=str(
                    row.get("normalized_job_id")
                    or stable_key
                    or row.get("id")
                    or ""
                ),
                title=str(row.get("title") or ""),
                company=str(row.get("company") or ""),
                location=str(row.get("location") or ""),
                location_display=str(
                    row.get("location_display") or row.get("location") or ""
                ),
                remote=bool(row.get("remote")),
                remote_type=str(row.get("remote_type") or "unknown"),
                url=str(row.get("url") or ""),
                source=str(row.get("source") or "unknown"),
                source_job_id=row.get("source_job_id"),
                summary=str(row.get("summary") or ""),
                description=str(row.get("description") or ""),
                responsibilities=_coerce_string_list(row.get("responsibilities")),
                qualifications=_coerce_string_list(row.get("qualifications")),
                required_skills=_coerce_string_list(row.get("required_skills")),
                preferred_skills=_coerce_string_list(row.get("preferred_skills")),
                employment_type=row.get("employment_type"),
                experience_level=str(row.get("experience_level") or "unknown"),
                role_type=str(row.get("role_type") or "unknown"),
                salary_min=_coerce_int(row.get("salary_min")),
                salary_max=_coerce_int(row.get("salary_max")),
                salary_currency=row.get("salary_currency"),
                stable_key=stable_key,
                provider_payload_hash=row.get("provider_payload_hash"),
            )
        except Exception:
            return None

    def save_job_for_user(self, *, user_id: str, public_job_id: str) -> Dict[str, Any]:
        job_row = self.get_active_job_by_public_id(public_job_id)
        self._upsert_relation(
            table_name=USER_SAVED_JOBS_TABLE,
            user_id=user_id,
            jobs_cache_row_id=str(job_row.get("id")),
        )
        return job_row

    def unsave_job_for_user(self, *, user_id: str, public_job_id: str) -> None:
        job_row = self.get_active_job_by_public_id(public_job_id)
        self._delete_relation(
            table_name=USER_SAVED_JOBS_TABLE,
            user_id=user_id,
            jobs_cache_row_id=str(job_row.get("id")),
        )

    def hide_job_for_user(self, *, user_id: str, public_job_id: str) -> Dict[str, Any]:
        job_row = self.get_active_job_by_public_id(public_job_id)
        self._upsert_relation(
            table_name=USER_HIDDEN_JOBS_TABLE,
            user_id=user_id,
            jobs_cache_row_id=str(job_row.get("id")),
        )
        return job_row

    def unhide_job_for_user(self, *, user_id: str, public_job_id: str) -> None:
        job_row = self.get_active_job_by_public_id(public_job_id)
        self._delete_relation(
            table_name=USER_HIDDEN_JOBS_TABLE,
            user_id=user_id,
            jobs_cache_row_id=str(job_row.get("id")),
        )

    def list_saved_jobs_for_user(self, *, user_id: str) -> list[Dict[str, Any]]:
        return self._list_related_jobs(
            table_name=USER_SAVED_JOBS_TABLE,
            user_id=user_id,
        )

    def list_hidden_jobs_for_user(self, *, user_id: str) -> list[Dict[str, Any]]:
        return self._list_related_jobs(
            table_name=USER_HIDDEN_JOBS_TABLE,
            user_id=user_id,
        )

    def apply_viewer_state_to_jobs(
        self,
        *,
        user_id: str,
        jobs: list[Dict[str, Any]],
        exclude_hidden: bool = False,
    ) -> list[Dict[str, Any]]:
        """Annotate jobs with the viewer's saved/hidden state and optionally filter hidden."""
        if not jobs:
            return []

        public_job_ids = [
            str(job.get("id") or "").strip()
            for job in jobs
            if str(job.get("id") or "").strip()
        ]
        if not public_job_ids:
            return jobs

        cache_rows = self.list_active_jobs_by_public_ids(public_job_ids)
        cache_id_by_public_id: dict[str, str] = {}

        for row in cache_rows:
            public_id = str(
                row.get("normalized_job_id")
                or row.get("stable_key")
                or ""
            ).strip()
            cache_row_id = str(row.get("id") or "").strip()

            if public_id and cache_row_id:
                cache_id_by_public_id[public_id] = cache_row_id

        cache_row_ids = list(cache_id_by_public_id.values())
        saved_state = self._relation_state_by_cache_row_id(
            table_name=USER_SAVED_JOBS_TABLE,
            user_id=user_id,
            cache_row_ids=cache_row_ids,
        )
        hidden_state = self._relation_state_by_cache_row_id(
            table_name=USER_HIDDEN_JOBS_TABLE,
            user_id=user_id,
            cache_row_ids=cache_row_ids,
        )

        annotated: list[Dict[str, Any]] = []

        for job in jobs:
            public_id = str(job.get("id") or "").strip()
            cache_row_id = cache_id_by_public_id.get(public_id)

            saved_at = saved_state.get(cache_row_id) if cache_row_id else None
            hidden_at = hidden_state.get(cache_row_id) if cache_row_id else None

            if exclude_hidden and hidden_at:
                continue

            viewer_state = {
                "is_saved": bool(saved_at),
                "is_hidden": bool(hidden_at),
                "saved_at": saved_at,
                "hidden_at": hidden_at,
            }

            next_job = dict(job)
            next_job["viewer_state"] = viewer_state
            annotated.append(next_job)

        return annotated

    def _list_related_jobs(
        self,
        *,
        table_name: str,
        user_id: str,
    ) -> list[Dict[str, Any]]:
        relation_rows = self._load_relation_rows(
            table_name=table_name,
            user_id=user_id,
        )
        if not relation_rows:
            return []

        ordered_cache_ids: list[str] = []
        relation_created_at_by_cache_id: dict[str, str | None] = {}

        for relation in relation_rows:
            cache_id = str(relation.get(TRACKER_JOB_FK_COLUMN) or "").strip()
            if not cache_id:
                continue

            ordered_cache_ids.append(cache_id)
            relation_created_at_by_cache_id[cache_id] = str(
                relation.get("created_at") or ""
            ).strip() or None

        job_rows = self.list_active_jobs_by_cache_row_ids(ordered_cache_ids)
        jobs_by_cache_id = {
            str(row.get("id") or "").strip(): row
            for row in job_rows
            if str(row.get("id") or "").strip()
        }

        hydrated: list[Dict[str, Any]] = []
        for cache_id in ordered_cache_ids:
            row = jobs_by_cache_id.get(cache_id)
            if not row:
                continue

            next_row = dict(row)
            next_row["relation_created_at"] = relation_created_at_by_cache_id.get(
                cache_id
            )
            hydrated.append(next_row)

        return hydrated

    def _relation_state_by_cache_row_id(
        self,
        *,
        table_name: str,
        user_id: str,
        cache_row_ids: list[str],
    ) -> dict[str, str | None]:
        rows = self._load_relation_rows(
            table_name=table_name,
            user_id=user_id,
            cache_row_ids=cache_row_ids,
        )

        state: dict[str, str | None] = {}
        for row in rows:
            cache_row_id = str(row.get(TRACKER_JOB_FK_COLUMN) or "").strip()
            if not cache_row_id:
                continue
            state[cache_row_id] = str(row.get("created_at") or "").strip() or None

        return state

    def _load_relation_rows(
        self,
        *,
        table_name: str,
        user_id: str,
        cache_row_ids: list[str] | None = None,
    ) -> list[Dict[str, Any]]:
        query = (
            self.client.table(table_name)
            .select(f"{TRACKER_JOB_FK_COLUMN}, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
        )

        if cache_row_ids:
            query = query.in_(TRACKER_JOB_FK_COLUMN, cache_row_ids)

        result = query.execute()
        return result.data or []

    def _upsert_relation(
        self,
        *,
        table_name: str,
        user_id: str,
        jobs_cache_row_id: str,
    ) -> None:
        payload = {
            "user_id": user_id,
            TRACKER_JOB_FK_COLUMN: jobs_cache_row_id,
        }

        self.client.table(table_name).upsert(
            payload,
            on_conflict=f"user_id,{TRACKER_JOB_FK_COLUMN}",
        ).execute()

    def _delete_relation(
        self,
        *,
        table_name: str,
        user_id: str,
        jobs_cache_row_id: str,
    ) -> None:
        (
            self.client.table(table_name)
            .delete()
            .eq("user_id", user_id)
            .eq(TRACKER_JOB_FK_COLUMN, jobs_cache_row_id)
            .execute()
        )

    def _filter_unexpired_rows(self, rows: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        filtered: list[Dict[str, Any]] = []

        for row in rows:
            expires_at = _parse_timestamptz(row.get("expires_at"))
            if expires_at is not None and expires_at <= now:
                continue
            filtered.append(row)

        return filtered

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
            "location_display": job.location_display or job.location,
            "remote": bool(job.remote),
            "remote_type": job.remote_type,
            "url": str(job.url),
            "source": job.source,
            "source_job_id": job.source_job_id,
            "summary": job.summary or "",
            "description": job.description or "",
            "responsibilities": job.responsibilities or [],
            "qualifications": job.qualifications or [],
            "required_skills": job.required_skills or [],
            "preferred_skills": job.preferred_skills or [],
            "employment_type": job.employment_type,
            "experience_level": job.experience_level,
            "role_type": job.role_type,
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "salary_currency": job.salary_currency,
            "provider_payload_hash": job.provider_payload_hash,
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