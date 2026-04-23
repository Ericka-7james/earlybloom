/**
 * @fileoverview Jobs API client for EarlyBloom.
 *
 * This module is responsible for:
 * - loading jobs data
 * - loading the resolved scoring profile used by the jobs page
 * - performing save/hide tracker mutations
 * - normalizing backend payloads into a stable frontend shape
 *
 * Authentication:
 * - The backend cookie session is the primary auth mechanism.
 * - Requests use `credentials: "include"` for backend-owned session cookies.
 * - This module intentionally does not depend on browser-local Supabase tokens.
 */

import { MOCK_RAW_JOBS } from "../../mock/jobs/jobs.raw";
import { MOCK_USER_PROFILE } from "../../mock/jobs/jobs.user-profile";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");
const USE_MOCK_JOBS =
  String(import.meta.env.VITE_USE_MOCK_JOBS || "false").toLowerCase() === "true";

const DEFAULT_RESOLVED_USER_PROFILE = {
  desiredLevels: ["entry-level", "junior"],
  preferredRoleTypes: [],
  preferredWorkplaceTypes: [],
  preferredLocations: [],
  skills: [],
  isLgbtFriendlyOnly: false,
};

const GET_RESPONSE_TTL_MS = 30_000;
const _inflightGetRequests = new Map();
const _responseCache = new Map();

/**
 * Returns whether jobs requests should use mock data.
 *
 * @returns {boolean} True when mock jobs mode is enabled.
 */
export function shouldUseMockJobs() {
  return USE_MOCK_JOBS;
}

/**
 * Ensures the backend API base URL exists.
 *
 * @throws {Error} When VITE_API_BASE_URL is missing.
 * @returns {void}
 */
function ensureApiBaseUrl() {
  if (!API_BASE_URL) {
    throw new Error("Missing VITE_API_BASE_URL.");
  }
}

/**
 * Returns whether an error represents an aborted request.
 *
 * @param {unknown} error Possible error.
 * @returns {boolean} True when this is an AbortError.
 */
function isAbortError(error) {
  return (
    error instanceof DOMException
      ? error.name === "AbortError"
      : error instanceof Error && error.name === "AbortError"
  );
}

/**
 * Extracts an array of jobs from a flexible backend payload shape.
 *
 * @param {any} payload Raw jobs payload.
 * @returns {Array<object>} Jobs array.
 */
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

/**
 * Reads a readable error message from a failed fetch response.
 *
 * @param {Response} response Fetch response object.
 * @param {string} fallbackMessage Fallback message.
 * @returns {Promise<string>} Readable error message.
 */
async function readErrorMessage(response, fallbackMessage) {
  try {
    const errorPayload = await response.json();

    if (typeof errorPayload?.detail === "string" && errorPayload.detail.trim()) {
      return errorPayload.detail;
    }

    if (typeof errorPayload?.message === "string" && errorPayload.message.trim()) {
      return errorPayload.message;
    }
  } catch {
    // Fall through to text parsing.
  }

  try {
    const text = await response.text();
    if (text?.trim()) {
      return text;
    }
  } catch {
    // Keep fallback message.
  }

  return fallbackMessage;
}

/**
 * Performs a backend jobs request and returns parsed JSON.
 *
 * GET requests are deduped in-flight and briefly cached in memory to reduce
 * repeated fetches during the same browsing session.
 *
 * Important abort behavior:
 * - do not share an in-flight GET request across callers that provide their own
 *   AbortSignal, because one caller's cleanup can otherwise poison another caller
 * - allow request cancellation to propagate as AbortError instead of being
 *   re-labeled as a network failure
 *
 * @param {string} path Backend API path.
 * @param {RequestInit} [options] Fetch options.
 * @returns {Promise<any>} Parsed JSON payload or null for 204 responses.
 */
async function requestJson(path, options = {}) {
  ensureApiBaseUrl();

  const method = String(options.method || "GET").toUpperCase();
  const isGetRequest = method === "GET";
  const fullUrl = `${API_BASE_URL}${path}`;
  const cacheKey = `${method}:${fullUrl}`;
  const hasExternalSignal = options.signal instanceof AbortSignal;

  if (isGetRequest) {
    const cached = getCachedResponse(cacheKey);
    if (cached !== undefined) {
      return cached;
    }

    if (!hasExternalSignal) {
      const inflight = _inflightGetRequests.get(cacheKey);
      if (inflight) {
        return inflight;
      }
    }
  }

  const requestPromise = (async () => {
    let response;

    try {
      response = await fetch(fullUrl, {
        credentials: "include",
        ...options,
        headers: {
          Accept: "application/json",
          ...(options.headers || {}),
        },
      });
    } catch (error) {
      if (isAbortError(error)) {
        throw error;
      }

      throw new Error(
        "Unable to reach the server. Check that the backend is running and try again."
      );
    }

    if (!response.ok) {
      const fallbackMessage = `${method} ${path} failed (${response.status}).`;
      const message = await readErrorMessage(response, fallbackMessage);
      const error = new Error(message);
      error.status = response.status;
      throw error;
    }

    if (response.status === 204) {
      if (isGetRequest) {
        setCachedResponse(cacheKey, null);
      }
      return null;
    }

    const payload = await response.json();

    if (isGetRequest) {
      setCachedResponse(cacheKey, payload);
    }

    return payload;
  })();

  if (isGetRequest && !hasExternalSignal) {
    _inflightGetRequests.set(cacheKey, requestPromise);

    try {
      return await requestPromise;
    } finally {
      _inflightGetRequests.delete(cacheKey);
    }
  }

  return requestPromise;
}

/**
 * Returns a cached GET response when still fresh.
 *
 * @param {string} cacheKey Request cache key.
 * @returns {any | undefined} Cached payload, or undefined when stale/missing.
 */
function getCachedResponse(cacheKey) {
  const entry = _responseCache.get(cacheKey);
  if (!entry) {
    return undefined;
  }

  if (Date.now() - entry.storedAt > GET_RESPONSE_TTL_MS) {
    _responseCache.delete(cacheKey);
    return undefined;
  }

  return entry.payload;
}

/**
 * Stores a GET response in the lightweight client cache.
 *
 * @param {string} cacheKey Request cache key.
 * @param {any} payload Parsed response payload.
 * @returns {void}
 */
function setCachedResponse(cacheKey, payload) {
  _responseCache.set(cacheKey, {
    storedAt: Date.now(),
    payload,
  });

  if (_responseCache.size > 10) {
    const oldestKey = _responseCache.keys().next().value;
    if (oldestKey) {
      _responseCache.delete(oldestKey);
    }
  }
}

/**
 * Clears cached GET responses. Useful after mutations.
 *
 * @returns {void}
 */
function clearJobsRequestCache() {
  _responseCache.clear();
}

/**
 * Builds the public jobs path with optional query parameters.
 *
 * @param {{ locationQuery?: string }} [options] Query options.
 * @returns {string} Jobs path.
 */
function buildJobsPath(options = {}) {
  const { locationQuery = "" } = options;
  const params = new URLSearchParams();

  if (String(locationQuery || "").trim()) {
    params.set("location", String(locationQuery).trim());
  }

  const query = params.toString();
  return query ? `/jobs?${query}` : "/jobs";
}

/**
 * Normalizes a backend job payload into the frontend display shape.
 *
 * @param {object} job Raw backend job object.
 * @param {number} index Fallback index used for synthetic IDs.
 * @returns {object} Normalized frontend job object.
 */
function normalizeBackendJob(job, index) {
  const normalizedRemoteType = job.remote_type ?? job.remoteType ?? null;
  const normalizedCurrency =
    job.salary_currency ?? job.salaryCurrency ?? job.currency ?? "USD";
  const normalizedId =
    job.id ?? job.external_id ?? job.job_id ?? job.jobId ?? `backend-job-${index}`;

  const viewerState = job.viewer_state ?? job.viewerState ?? {};

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
    location_display: job.location_display ?? job.location ?? "Location not listed",

    description: job.description ?? "",
    summary: job.summary ?? "",
    requirements: Array.isArray(job.requirements) ? job.requirements : [],
    responsibilities: Array.isArray(job.responsibilities)
      ? job.responsibilities
      : [],
    qualifications: Array.isArray(job.qualifications) ? job.qualifications : [],
    required_skills: Array.isArray(job.required_skills)
      ? job.required_skills
      : [],
    preferred_skills: Array.isArray(job.preferred_skills)
      ? job.preferred_skills
      : [],
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

    stable_key: job.stable_key ?? null,
    provider_payload_hash: job.provider_payload_hash ?? null,

    is_saved:
      viewerState.is_saved ?? viewerState.isSaved ?? job.is_saved ?? false,
    is_hidden:
      viewerState.is_hidden ?? viewerState.isHidden ?? job.is_hidden ?? false,
    saved_at:
      viewerState.saved_at ?? viewerState.savedAt ?? job.saved_at ?? null,
    hidden_at:
      viewerState.hidden_at ?? viewerState.hiddenAt ?? job.hidden_at ?? null,

    rawBackendJob: job,
  };
}

/**
 * Normalizes the resolved jobs profile returned by the backend.
 *
 * @param {object | null | undefined} profile Raw resolved profile payload.
 * @returns {object} Stable frontend resolved-profile shape.
 */
function normalizeResolvedJobProfile(profile) {
  if (!profile || typeof profile !== "object") {
    return { ...DEFAULT_RESOLVED_USER_PROFILE };
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
    preferredLocations: Array.isArray(profile.preferredLocations)
      ? profile.preferredLocations
      : Array.isArray(profile.preferred_locations)
        ? profile.preferred_locations
        : DEFAULT_RESOLVED_USER_PROFILE.preferredLocations,
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

/**
 * Normalizes the mock jobs profile used during mock mode.
 *
 * @param {object | null | undefined} mockProfile Raw mock user profile.
 * @returns {object} Stable frontend resolved-profile shape.
 */
function normalizeMockUserProfile(mockProfile) {
  if (!mockProfile || typeof mockProfile !== "object") {
    return { ...DEFAULT_RESOLVED_USER_PROFILE };
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
    preferredLocations: Array.isArray(mockProfile.preferredLocations)
      ? mockProfile.preferredLocations
      : Array.isArray(mockProfile.preferred_locations)
        ? mockProfile.preferred_locations
        : DEFAULT_RESOLVED_USER_PROFILE.preferredLocations,
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

/**
 * Normalizes a backend jobs payload into a frontend jobs array.
 *
 * @param {any} payload Raw jobs payload.
 * @returns {Array<object>} Normalized jobs.
 */
function normalizeJobsPayload(payload) {
  const jobs = extractJobsArray(payload);
  return jobs.map(normalizeBackendJob);
}

/**
 * Fetches the public jobs feed.
 *
 * @param {{ signal?: AbortSignal, force?: boolean, locationQuery?: string }} [options] Fetch options.
 * @returns {Promise<Array<object>>} Normalized jobs array.
 */
export async function fetchJobs(options = {}) {
  const { signal, force = false, locationQuery = "" } = options;

  if (USE_MOCK_JOBS) {
    return MOCK_RAW_JOBS;
  }

  if (force) {
    clearJobsRequestCache();
  }

  const payload = await requestJson(buildJobsPath({ locationQuery }), {
    method: "GET",
    signal,
  });

  return normalizeJobsPayload(payload);
}

/**
 * Fetches the resolved jobs profile used for scoring and filtering.
 *
 * @param {{ signal?: AbortSignal, force?: boolean }} [options] Fetch options.
 * @returns {Promise<object>} Resolved jobs profile.
 */
export async function fetchResolvedJobProfile(options = {}) {
  const { signal, force = false } = options;

  if (USE_MOCK_JOBS) {
    return normalizeMockUserProfile(MOCK_USER_PROFILE);
  }

  if (force) {
    clearJobsRequestCache();
  }

  const payload = await requestJson("/jobs/profile", {
    method: "GET",
    signal,
  });

  return normalizeResolvedJobProfile(payload);
}

/**
 * Saves a job for the current authenticated user.
 *
 * @param {string} jobId Public job ID.
 * @returns {Promise<object>} Save mutation response.
 */
export async function saveJob(jobId) {
  const result = await requestJson("/jobs/saved", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ job_id: jobId }),
  });

  clearJobsRequestCache();
  return result;
}

/**
 * Removes a saved-job relationship for the current authenticated user.
 *
 * @param {string} jobId Public job ID.
 * @returns {Promise<object>} Unsave mutation response.
 */
export async function unsaveJob(jobId) {
  const result = await requestJson(`/jobs/saved/${encodeURIComponent(jobId)}`, {
    method: "DELETE",
  });

  clearJobsRequestCache();
  return result;
}

/**
 * Hides a job for the current authenticated user.
 *
 * @param {string} jobId Public job ID.
 * @returns {Promise<object>} Hide mutation response.
 */
export async function hideJob(jobId) {
  const result = await requestJson("/jobs/hidden", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ job_id: jobId }),
  });

  clearJobsRequestCache();
  return result;
}

/**
 * Removes a hidden-job relationship for the current authenticated user.
 *
 * @param {string} jobId Public job ID.
 * @returns {Promise<object>} Unhide mutation response.
 */
export async function unhideJob(jobId) {
  const result = await requestJson(`/jobs/hidden/${encodeURIComponent(jobId)}`, {
    method: "DELETE",
  });

  clearJobsRequestCache();
  return result;
}

/**
 * Fetches saved jobs for the current authenticated user.
 *
 * @param {{ signal?: AbortSignal, force?: boolean }} [options] Fetch options.
 * @returns {Promise<Array<object>>} Normalized saved jobs.
 */
export async function fetchSavedJobs(options = {}) {
  const { signal, force = false } = options;

  if (USE_MOCK_JOBS) {
    return [];
  }

  if (force) {
    clearJobsRequestCache();
  }

  const payload = await requestJson("/jobs/saved", {
    method: "GET",
    signal,
  });

  return normalizeJobsPayload(payload);
}

/**
 * Fetches hidden jobs for the current authenticated user.
 *
 * @param {{ signal?: AbortSignal, force?: boolean }} [options] Fetch options.
 * @returns {Promise<Array<object>>} Normalized hidden jobs.
 */
export async function fetchHiddenJobs(options = {}) {
  const { signal, force = false } = options;

  if (USE_MOCK_JOBS) {
    return [];
  }

  if (force) {
    clearJobsRequestCache();
  }

  try {
    const payload = await requestJson("/jobs/hidden", {
      method: "GET",
      signal,
    });

    return normalizeJobsPayload(payload);
  } catch (error) {
    if (error instanceof Error) {
      throw new Error(error.message || "Unable to load hidden jobs right now.");
    }

    throw new Error("Unable to load hidden jobs right now.");
  }
}