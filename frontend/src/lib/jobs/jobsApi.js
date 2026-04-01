import { MOCK_RAW_JOBS } from "../../mock/jobs/jobs.raw";
import { MOCK_USER_PROFILE } from "../../mock/jobs/jobs.user-profile";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");
const USE_MOCK_JOBS =
  String(import.meta.env.VITE_USE_MOCK_JOBS || "false").toLowerCase() === "true";

const DEFAULT_RESOLVED_USER_PROFILE = {
  desiredLevels: ["entry-level", "junior"],
  preferredRoleTypes: [],
  preferredWorkplaceTypes: [],
  skills: [],
  isLgbtFriendlyOnly: false,
};

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
    summary: job.summary ?? "",
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
    remoteType: normalizedRemoteType,
    remote_type: normalizedRemoteType,
    remote:
      typeof job.remote === "boolean"
        ? job.remote
        : normalizedRemoteType === "remote"
        ? true
        : normalizedRemoteType === "hybrid" || normalizedRemoteType === "onsite"
        ? false
        : null,

    roleType: job.roleType ?? job.role_type ?? null,
    role_type: job.role_type ?? job.roleType ?? null,

    employmentType: job.employmentType ?? job.employment_type ?? null,
    employment_type: job.employment_type ?? job.employmentType ?? null,

    experienceLevel:
      job.experienceLevel ??
      job.experience_level ??
      job.seniority_hint ??
      job.seniority ??
      null,
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

function normalizeResolvedJobProfile(profile) {
  if (!profile || typeof profile !== "object") {
    return DEFAULT_RESOLVED_USER_PROFILE;
  }

  return {
    desiredLevels: Array.isArray(profile.desiredLevels)
      ? profile.desiredLevels
      : Array.isArray(profile.desired_levels)
      ? profile.desired_levels
      : DEFAULT_RESOLVED_USER_PROFILE.desiredLevels,
    preferredRoleTypes: Array.isArray(profile.preferredRoleTypes)
      ? profile.preferredRoleTypes
      : Array.isArray(profile.preferred_role_types)
      ? profile.preferred_role_types
      : DEFAULT_RESOLVED_USER_PROFILE.preferredRoleTypes,
    preferredWorkplaceTypes: Array.isArray(profile.preferredWorkplaceTypes)
      ? profile.preferredWorkplaceTypes
      : Array.isArray(profile.preferred_workplace_types)
      ? profile.preferred_workplace_types
      : DEFAULT_RESOLVED_USER_PROFILE.preferredWorkplaceTypes,
    skills: Array.isArray(profile.skills)
      ? profile.skills
      : DEFAULT_RESOLVED_USER_PROFILE.skills,
    isLgbtFriendlyOnly:
      typeof profile.isLgbtFriendlyOnly === "boolean"
        ? profile.isLgbtFriendlyOnly
        : typeof profile.is_lgbt_friendly_only === "boolean"
        ? profile.is_lgbt_friendly_only
        : DEFAULT_RESOLVED_USER_PROFILE.isLgbtFriendlyOnly,
  };
}

function normalizeMockUserProfile(mockProfile) {
  if (!mockProfile || typeof mockProfile !== "object") {
    return DEFAULT_RESOLVED_USER_PROFILE;
  }

  return {
    desiredLevels: Array.isArray(mockProfile.desiredLevels)
      ? mockProfile.desiredLevels
      : Array.isArray(mockProfile.desired_levels)
      ? mockProfile.desired_levels
      : DEFAULT_RESOLVED_USER_PROFILE.desiredLevels,
    preferredRoleTypes: Array.isArray(mockProfile.preferredRoleTypes)
      ? mockProfile.preferredRoleTypes
      : Array.isArray(mockProfile.preferred_role_types)
      ? mockProfile.preferred_role_types
      : DEFAULT_RESOLVED_USER_PROFILE.preferredRoleTypes,
    preferredWorkplaceTypes: Array.isArray(mockProfile.preferredWorkplaceTypes)
      ? mockProfile.preferredWorkplaceTypes
      : Array.isArray(mockProfile.preferred_workplace_types)
      ? mockProfile.preferred_workplace_types
      : DEFAULT_RESOLVED_USER_PROFILE.preferredWorkplaceTypes,
    skills: Array.isArray(mockProfile.skills)
      ? mockProfile.skills
      : Array.isArray(mockProfile.topSkills)
      ? mockProfile.topSkills
      : DEFAULT_RESOLVED_USER_PROFILE.skills,
    isLgbtFriendlyOnly:
      typeof mockProfile.isLgbtFriendlyOnly === "boolean"
        ? mockProfile.isLgbtFriendlyOnly
        : typeof mockProfile.is_lgbt_friendly_only === "boolean"
        ? mockProfile.is_lgbt_friendly_only
        : DEFAULT_RESOLVED_USER_PROFILE.isLgbtFriendlyOnly,
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
    credentials: "include",
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

export async function fetchResolvedJobProfile(options = {}) {
  const { signal } = options;

  if (USE_MOCK_JOBS) {
    return normalizeMockUserProfile(MOCK_USER_PROFILE);
  }

  if (!API_BASE_URL) {
    throw new Error("Missing VITE_API_BASE_URL.");
  }

  const response = await fetch(`${API_BASE_URL}/jobs/profile`, {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
    signal,
    credentials: "include",
  });

  if (!response.ok) {
    let message = `Job profile request failed (${response.status}).`;

    try {
      const errorPayload = await response.json();
      message = errorPayload?.detail || errorPayload?.message || message;
    } catch {
      // Keep fallback message.
    }

    throw new Error(message);
  }

  const payload = await response.json();
  return normalizeResolvedJobProfile(payload);
}