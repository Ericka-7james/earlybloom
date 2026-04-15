/**
 * @fileoverview Resume utilities and backend API helpers for EarlyBloom.
 *
 * Responsibilities:
 * - manage local resume UI cache
 * - confirm backend cookie-auth session state
 * - persist resume records through the backend
 * - request backend resume parsing
 * - provide optional legacy helpers for direct browser storage access
 *
 * The backend cookie session is the application's source of truth for auth.
 * Browser Supabase session access is treated as optional and legacy.
 */

import { supabase } from "./supabaseClient";

export const RESUME_STORAGE_KEY = "earlybloom_resume_upload";
export const RESUME_MODAL_DISMISSED_KEY = "earlybloom_resume_modal_dismissed";
export const RESUME_RAW_TEXT_SESSION_KEY = "earlybloom_resume_raw_text";
export const RESUME_BUCKET_NAME = "resume-uploads";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");

/**
 * Ensures the backend API base URL is configured.
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
 * Reads a readable error message from a backend error payload.
 *
 * @param {any} errorPayload Parsed backend error payload.
 * @param {string} fallbackMessage Fallback message.
 * @returns {string} Readable error message.
 */
function normalizeApiErrorMessage(errorPayload, fallbackMessage) {
  const detail = errorPayload?.detail;

  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail) && detail.length > 0) {
    return detail
      .map((item) => {
        if (typeof item === "string") {
          return item;
        }

        if (item?.msg && Array.isArray(item?.loc)) {
          return `${item.loc.join(".")}: ${item.msg}`;
        }

        if (item?.msg) {
          return item.msg;
        }

        try {
          return JSON.stringify(item);
        } catch {
          return String(item);
        }
      })
      .join(" | ");
  }

  if (detail && typeof detail === "object") {
    if (typeof detail.msg === "string" && detail.msg.trim()) {
      return detail.msg;
    }

    try {
      return JSON.stringify(detail);
    } catch {
      return fallbackMessage;
    }
  }

  if (
    typeof errorPayload?.message === "string" &&
    errorPayload.message.trim()
  ) {
    return errorPayload.message;
  }

  return fallbackMessage;
}

/**
 * Reads a readable error message from a failed fetch response.
 *
 * @param {Response} response Fetch response object.
 * @param {string} fallbackMessage Fallback message.
 * @returns {Promise<string>} Readable error message.
 */
async function readResponseErrorMessage(response, fallbackMessage) {
  try {
    const errorPayload = await response.json();
    return normalizeApiErrorMessage(errorPayload, fallbackMessage);
  } catch {
    try {
      const text = await response.text();
      if (text?.trim()) {
        return text;
      }
    } catch {
      // Keep fallback message.
    }
  }

  return fallbackMessage;
}

/**
 * Returns whether browser storage APIs are available.
 *
 * @returns {boolean} True when window-based storage can be used.
 */
function canUseBrowserStorage() {
  return typeof window !== "undefined";
}

/**
 * Builds a cached UI representation of a resume record.
 *
 * @param {File | null} file Uploaded file object, if available.
 * @param {object | null} resumeRecord Saved resume record, if available.
 * @returns {{
 *   id: string | null,
 *   name: string,
 *   size: number | null,
 *   type: string,
 *   uploadedAt: string,
 *   parseStatus: string,
 *   atsTags: string[],
 *   isLocalOnly: boolean
 * }} Resume UI cache payload.
 */
export function buildResumeUiCache(file, resumeRecord = null) {
  return {
    id: resumeRecord?.id ?? null,
    name: file?.name || resumeRecord?.original_filename || "resume.pdf",
    size: file?.size ?? null,
    type: file?.type || resumeRecord?.file_type || "application/pdf",
    uploadedAt: resumeRecord?.updated_at || new Date().toISOString(),
    parseStatus: resumeRecord?.parse_status ?? "pending",
    atsTags: Array.isArray(resumeRecord?.ats_tags) ? resumeRecord.ats_tags : [],
    isLocalOnly: Boolean(resumeRecord?.isLocalOnly),
  };
}

/**
 * Caches resume UI state locally.
 *
 * @param {object} cachedResume Resume UI cache payload.
 * @returns {void}
 */
export function cacheResumeUiState(cachedResume) {
  if (!canUseBrowserStorage()) {
    return;
  }

  window.localStorage.setItem(RESUME_STORAGE_KEY, JSON.stringify(cachedResume));
  window.sessionStorage.setItem(RESUME_MODAL_DISMISSED_KEY, "true");
}

/**
 * Reads the cached resume UI state from local storage.
 *
 * @returns {object | null} Cached resume UI state, if present.
 */
export function readCachedResumeUiState() {
  if (!canUseBrowserStorage()) {
    return null;
  }

  try {
    const cachedResume = window.localStorage.getItem(RESUME_STORAGE_KEY);
    return cachedResume ? JSON.parse(cachedResume) : null;
  } catch {
    return null;
  }
}

/**
 * Clears local resume cache state.
 *
 * @returns {void}
 */
export function clearCachedResumeUiState() {
  if (!canUseBrowserStorage()) {
    return;
  }

  window.localStorage.removeItem(RESUME_STORAGE_KEY);
  window.sessionStorage.removeItem(RESUME_MODAL_DISMISSED_KEY);
  window.sessionStorage.removeItem(RESUME_RAW_TEXT_SESSION_KEY);
}

/**
 * Caches extracted raw resume text in session storage.
 *
 * @param {string | null | undefined} rawText Extracted resume text.
 * @returns {void}
 */
export function cacheResumeRawText(rawText) {
  if (!canUseBrowserStorage()) {
    return;
  }

  if (!rawText) {
    window.sessionStorage.removeItem(RESUME_RAW_TEXT_SESSION_KEY);
    return;
  }

  window.sessionStorage.setItem(RESUME_RAW_TEXT_SESSION_KEY, rawText);
}

/**
 * Reads cached extracted resume text from session storage.
 *
 * @returns {string | null} Cached raw text.
 */
export function readCachedResumeRawText() {
  if (!canUseBrowserStorage()) {
    return null;
  }

  try {
    return window.sessionStorage.getItem(RESUME_RAW_TEXT_SESSION_KEY);
  } catch {
    return null;
  }
}

/**
 * Confirms the current backend cookie-auth session.
 *
 * @throws {Error} When the backend session cannot be confirmed.
 * @returns {Promise<object>} Auth session payload.
 */
export async function requireBackendSession() {
  ensureApiBaseUrl();

  let response;

  try {
    response = await fetch(`${API_BASE_URL}/auth/session`, {
      method: "GET",
      credentials: "include",
      headers: {
        Accept: "application/json",
      },
    });
  } catch {
    throw new Error(
      "Unable to reach the server. Check that the backend is running and try again."
    );
  }

  if (!response.ok) {
    throw new Error(
      "Your session is not available in this browser. Refresh the page and sign in again."
    );
  }

  let payload = null;

  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!payload?.authenticated || !payload?.user?.id) {
    throw new Error(
      "Your session is not available in this browser. Refresh the page and sign in again."
    );
  }

  return payload;
}

/**
 * Backward-compatible alias for backend session confirmation.
 *
 * @returns {Promise<object>} Confirmed backend session payload.
 */
export async function requireAuthenticatedSession() {
  return requireBackendSession();
}

/**
 * Performs a best-effort read of the browser Supabase session.
 *
 * This helper exists for legacy direct-storage workflows and should not be used
 * as the primary application auth source.
 *
 * @returns {Promise<object | null>} Supabase session when available.
 */
export async function getOptionalSupabaseSession() {
  try {
    const {
      data: { session },
      error,
    } = await supabase.auth.getSession();

    if (error) {
      return null;
    }

    if (session?.user && session?.access_token) {
      return session;
    }

    const { data: refreshedData, error: refreshError } =
      await supabase.auth.refreshSession();

    if (refreshError) {
      return null;
    }

    const refreshedSession = refreshedData?.session ?? null;

    if (refreshedSession?.user && refreshedSession?.access_token) {
      return refreshedSession;
    }

    return null;
  } catch {
    return null;
  }
}

/**
 * Builds authenticated backend request headers after confirming the session.
 *
 * @throws {Error} When the backend session is unavailable.
 * @returns {Promise<Record<string, string>>} Standard backend API headers.
 */
export async function buildAuthenticatedApiHeaders() {
  ensureApiBaseUrl();
  await requireBackendSession();

  return {
    Accept: "application/json",
    "Content-Type": "application/json",
  };
}

/**
 * Builds the canonical storage path for a user's active resume file.
 *
 * @param {string} userId Authenticated user ID.
 * @param {string} fileName Original uploaded file name.
 * @returns {string} Stable storage path.
 */
export function buildResumeStoragePath(userId, fileName) {
  const extension = String(fileName || "resume.pdf").split(".").pop() || "pdf";
  return `${userId}/resume.${extension.toLowerCase()}`;
}

/**
 * Uploads a resume file to Supabase Storage using legacy browser auth.
 *
 * This helper is optional for launch and should only be used when direct
 * browser storage upload is still required.
 *
 * @param {{ file: File }} params Upload parameters.
 * @returns {Promise<{ storagePath: string, publicUrl: string | null }>} Upload result.
 */
export async function uploadResumeFile({ file }) {
  const backendSession = await requireBackendSession();
  const browserSession = await getOptionalSupabaseSession();

  if (!browserSession?.user?.id) {
    throw new Error(
      "Your app session is active, but browser storage auth is missing. Refresh the page and sign in again."
    );
  }

  const userId = backendSession.user.id;
  const storagePath = buildResumeStoragePath(userId, file.name);

  const { error } = await supabase.storage
    .from(RESUME_BUCKET_NAME)
    .upload(storagePath, file, {
      cacheControl: "3600",
      upsert: true,
      contentType: file.type || "application/pdf",
    });

  if (error) {
    throw error;
  }

  const {
    data: { publicUrl },
  } = supabase.storage.from(RESUME_BUCKET_NAME).getPublicUrl(storagePath);

  return {
    storagePath,
    publicUrl: publicUrl || null,
  };
}

/**
 * Saves the authenticated user's active resume record through the backend.
 *
 * @param {{
 *   originalFilename: string,
 *   fileSizeBytes: number,
 *   fileType?: string,
 *   parseStatus?: string,
 *   rawText?: string | null,
 *   parsedJson?: object | null,
 *   parseWarnings?: string[],
 *   atsTags?: string[],
 *   uploadSource?: string,
 *   storagePath?: string | null
 * }} params Resume record payload.
 * @returns {Promise<object>} Upserted resume record.
 */
export async function saveResumeRecord({
  originalFilename,
  fileSizeBytes,
  fileType = "application/pdf",
  parseStatus = "pending",
  rawText = null,
  parsedJson = null,
  parseWarnings = [],
  atsTags = [],
  uploadSource = "web",
  storagePath = null,
}) {
  const headers = await buildAuthenticatedApiHeaders();

  const response = await fetch(`${API_BASE_URL}/resume/current`, {
    method: "POST",
    credentials: "include",
    headers,
    body: JSON.stringify({
      original_filename: originalFilename,
      file_size_bytes: fileSizeBytes,
      file_type: fileType,
      upload_source: uploadSource,
      storage_path: storagePath,
      parse_status: parseStatus,
      raw_text: rawText,
      parsed_json: parsedJson,
      parse_warnings: parseWarnings,
      ats_tags: atsTags,
    }),
  });

  if (!response.ok) {
    const message = await readResponseErrorMessage(
      response,
      "Failed to save resume record."
    );
    throw new Error(message);
  }

  return await response.json();
}

/**
 * Parses a stored resume record through the backend parser.
 *
 * @param {{
 *   resumeId: string,
 *   rawText: string,
 *   fileType?: string,
 *   extractionMethod?: string
 * }} params Parse request payload.
 * @returns {Promise<object>} Resume parse response.
 */
export async function parseResumeRecord({
  resumeId,
  rawText,
  fileType = "application/pdf",
  extractionMethod = "text",
}) {
  const headers = await buildAuthenticatedApiHeaders();

  const response = await fetch(`${API_BASE_URL}/resume/${resumeId}/parse`, {
    method: "POST",
    credentials: "include",
    headers,
    body: JSON.stringify({
      raw_text: rawText,
      file_type: fileType,
      extraction_method: extractionMethod,
    }),
  });

  if (!response.ok) {
    const message = await readResponseErrorMessage(
      response,
      "Resume parse request failed."
    );
    throw new Error(message);
  }

  return await response.json();
}

/**
 * Fetches the latest tracker resume summary for the authenticated user.
 *
 * @returns {Promise<object | null>} Tracker resume summary, or null.
 */
export async function fetchLatestTrackerResume() {
  const headers = await buildAuthenticatedApiHeaders();

  const response = await fetch(`${API_BASE_URL}/tracker`, {
    method: "GET",
    credentials: "include",
    headers,
  });

  if (!response.ok) {
    const message = await readResponseErrorMessage(
      response,
      "Failed to load tracker resume."
    );
    throw new Error(message);
  }

  const payload = await response.json();
  return payload?.resume && typeof payload.resume === "object"
    ? payload.resume
    : null;
}

/**
 * Fetches the current stored resume record directly from the backend.
 *
 * @returns {Promise<object | null>} Current resume record, or null when absent.
 */
export async function fetchCurrentResumeRecord() {
  const headers = await buildAuthenticatedApiHeaders();

  const response = await fetch(`${API_BASE_URL}/resume/current`, {
    method: "GET",
    credentials: "include",
    headers,
  });

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    const message = await readResponseErrorMessage(
      response,
      "Failed to load current resume."
    );
    throw new Error(message);
  }

  return await response.json();
}

/**
 * Saves a resume record and then attempts to verify the canonical tracker state.
 *
 * If tracker refresh is temporarily unavailable, the direct save result is
 * returned so the UI can keep moving.
 *
 * @param {object} params Same parameters accepted by {@link saveResumeRecord}.
 * @returns {Promise<object>} Verified or fallback resume record.
 */
export async function saveAndVerifyResumeRecord(params) {
  const savedResume = await saveResumeRecord(params);

  let trackerResume = null;

  try {
    trackerResume = await fetchLatestTrackerResume();
  } catch {
    // Allow the direct save result to stand.
  }

  if (trackerResume?.id) {
    return {
      ...savedResume,
      id: trackerResume.id,
      original_filename:
        trackerResume.original_filename || savedResume.original_filename,
      file_type: trackerResume.file_type || savedResume.file_type,
      parse_status: trackerResume.parse_status || savedResume.parse_status,
      updated_at: trackerResume.updated_at || savedResume.updated_at,
      ats_tags: Array.isArray(trackerResume.ats_tags)
        ? trackerResume.ats_tags
        : savedResume.ats_tags || [],
    };
  }

  return savedResume;
}

/**
 * Fetches all stored resumes for the authenticated user.
 *
 * The current launch flow supports a single active resume, so this returns
 * either a one-item list or an empty list.
 *
 * @returns {Promise<object[]>} Resume list.
 */
export async function fetchMyResumes() {
  const currentResume = await fetchCurrentResumeRecord();
  return currentResume ? [currentResume] : [];
}