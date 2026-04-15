from __future__ import annotations

from app.schemas.jobs import NormalizedJob
from app.services.jobs.common.skills_taxonomy import extract_skills_from_text


MAX_JOB_SKILLS = 12


def build_job_skill_text(job: NormalizedJob) -> str:
    return "\n".join(
        part for part in [
            job.title,
            job.summary,
            job.description,
            "\n".join(job.responsibilities or []),
            "\n".join(job.qualifications or []),
            " ".join(job.required_skills or []),
            " ".join(job.preferred_skills or []),
        ]
        if part
    )


def attach_normalized_skills(job: NormalizedJob) -> NormalizedJob:
    blob = build_job_skill_text(job)
    job.skills = extract_skills_from_text(blob)[:MAX_JOB_SKILLS]
    return job