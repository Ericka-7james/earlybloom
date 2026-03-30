import { MOCK_RAW_JOBS } from "../../mock/jobs/jobs.raw";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");
const USE_MOCK_JOBS =
  String(import.meta.env.VITE_USE_MOCK_JOBS || "false").toLowerCase() === "true";

export function shouldUseMockJobs() {
  return USE_MOCK_JOBS;
}

function extractJobsArray(payload) {
  if (Array.isArray(payload)) {
    return payload;
  }

  if (Array.isArray(payload?.jobs)) {
    return payload.jobs;
  }

  if (Array.isArray(payload?.data)) {
    return payload.data;
  }

  return [];
}

function normalizeBackendJob(job, index) {
  const normalizedRemoteType = job.remote_type ?? job.remoteType ?? null;
  const normalizedCurrency =
    job.salary_currency ?? job.salaryCurrency ?? job.currency ?? "USD";
  const normalizedId =
    job.id ?? job.external_id ?? job.job_id ?? job.jobId ?? `backend-job-${index}`;

  return {
    id: normalizedId,
    jobId: normalizedId,
    external_id: job.external_id ?? null,
    slug: job.slug ?? null,

    title: job.title ?? "Untitled role",
    company: job.company ?? job.company_name ?? job.companyName ?? "Unknown company",
    company_name:
      job.company_name ?? job.companyName ?? job.company ?? "Unknown company",
    location: job.location ?? "Location not listed",

    description: job.description ?? "",
    requirements: Array.isArray(job.requirements) ? job.requirements : [],
    tags: Array.isArray(job.tags) ? job.tags : [],

    workplaceType:
      job.workplaceType ??
      job.workplace_type ??
      normalizedRemoteType ??
      null,
    workplace:
      job.workplace ??
      job.workplaceType ??
      job.workplace_type ??
      normalizedRemoteType ??
      null,
    remote_type: normalizedRemoteType,
    remote:
      normalizedRemoteType === "remote"
        ? true
        : normalizedRemoteType === "hybrid" || normalizedRemoteType === "onsite"
        ? false
        : null,

    roleType: job.roleType ?? job.role_type ?? null,

    employmentType: job.employmentType ?? job.employment_type ?? null,
    employment_type: job.employment_type ?? job.employmentType ?? null,

    experience_level:
      job.experience_level ??
      job.experienceLevel ??
      job.seniority_hint ??
      job.seniority ??
      null,
    seniority_hint: job.seniority_hint ?? null,

    source: job.source ?? "backend",
    source_name: job.source_name ?? job.source ?? "backend",
    sourceUrl: job.sourceUrl ?? job.source_url ?? job.url ?? job.apply_url ?? null,
    source_url: job.source_url ?? job.sourceUrl ?? job.url ?? job.apply_url ?? null,
    url: job.url ?? job.apply_url ?? null,
    apply_url: job.apply_url ?? job.url ?? null,

    postedAt: job.postedAt ?? job.posted_at ?? null,
    posted_at: job.posted_at ?? job.postedAt ?? null,
    created_at: job.created_at ?? job.createdAt ?? null,

    salary_min: job.salary_min ?? null,
    salary_max: job.salary_max ?? null,
    salary_currency: normalizedCurrency,
    currency: normalizedCurrency,

    compensation:
      job.compensation ??
      (job.salary_min || job.salary_max
        ? {
            salaryMinUsd: job.salary_min ?? null,
            salaryMaxUsd: job.salary_max ?? null,
            currency: normalizedCurrency,
            salaryVisible: true,
          }
        : null),

    rawBackendJob: job,
  };
}

export async function fetchJobs(options = {}) {
  const { signal } = options;

  if (USE_MOCK_JOBS) {
    return MOCK_RAW_JOBS;
  }

  if (!API_BASE_URL) {
    throw new Error("Missing VITE_API_BASE_URL.");
  }

  const response = await fetch(`${API_BASE_URL}/jobs`, {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
    signal,
  });

  if (!response.ok) {
    let message = `Jobs request failed (${response.status}).`;

    try {
      const errorPayload = await response.json();
      message = errorPayload?.detail || errorPayload?.message || message;
    } catch {
      // Keep fallback message.
    }

    throw new Error(message);
  }

  const payload = await response.json();
  const jobs = extractJobsArray(payload);

  return jobs.map(normalizeBackendJob);
}