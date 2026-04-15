import { supabase } from "./supabaseClient";

export const RESUME_STORAGE_KEY = "earlybloom_resume_upload";
export const RESUME_MODAL_DISMISSED_KEY = "earlybloom_resume_modal_dismissed";
export const RESUME_RAW_TEXT_SESSION_KEY = "earlybloom_resume_raw_text";
export const RESUME_BUCKET_NAME = "resume-uploads";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");

/**
 * Convert backend error payloads into readable messages.
 *
 * Args:
 *   errorPayload: Parsed backend error payload.
 *   fallbackMessage: Message used when no specific detail is available.
 *
 * Returns:
 *   Readable error message.
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
    if (typeof detail?.msg === "string" && detail.msg.trim()) {
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
 * Build local UI cache state for a resume upload.
 *
 * Args:
 *   file: Uploaded file object.
 *   resumeRecord: Stored resume record if available.
 *
 * Returns:
 *   Resume UI cache payload.
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
    isLocalOnly: resumeRecord?.isLocalOnly ?? false,
  };
}

/**
 * Cache resume UI state locally.
 *
 * Args:
 *   cachedResume: Resume UI cache payload.
 *
 * Returns:
 *   void
 */
export function cacheResumeUiState(cachedResume) {
  window.localStorage.setItem(RESUME_STORAGE_KEY, JSON.stringify(cachedResume));
  window.sessionStorage.setItem(RESUME_MODAL_DISMISSED_KEY, "true");
}

/**
 * Read cached resume UI state.
 *
 * Returns:
 *   Cached resume UI state, if present.
 */
export function readCachedResumeUiState() {
  try {
    const cachedResume = window.localStorage.getItem(RESUME_STORAGE_KEY);
    return cachedResume ? JSON.parse(cachedResume) : null;
  } catch {
    return null;
  }
}

/**
 * Clear cached resume UI state.
 *
 * Returns:
 *   void
 */
export function clearCachedResumeUiState() {
  window.localStorage.removeItem(RESUME_STORAGE_KEY);
  window.sessionStorage.removeItem(RESUME_MODAL_DISMISSED_KEY);
  window.sessionStorage.removeItem(RESUME_RAW_TEXT_SESSION_KEY);
}

/**
 * Cache extracted raw resume text in session storage.
 *
 * Args:
 *   rawText: Extracted raw text.
 *
 * Returns:
 *   void
 */
export function cacheResumeRawText(rawText) {
  if (!rawText) {
    window.sessionStorage.removeItem(RESUME_RAW_TEXT_SESSION_KEY);
    return;
  }

  window.sessionStorage.setItem(RESUME_RAW_TEXT_SESSION_KEY, rawText);
}

/**
 * Read cached raw resume text.
 *
 * Returns:
 *   Cached raw text if present.
 */
export function readCachedResumeRawText() {
  try {
    return window.sessionStorage.getItem(RESUME_RAW_TEXT_SESSION_KEY);
  } catch {
    return null;
  }
}

/**
 * Fetch the current authenticated backend session using HTTP-only cookies.
 *
 * Returns:
 *   Auth session payload from the backend.
 *
 * Throws:
 *   Error: If the backend session cannot be confirmed.
 */
export async function requireBackendSession() {
  if (!API_BASE_URL) {
    throw new Error("Missing VITE_API_BASE_URL.");
  }

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
      "Unable to reach the server. Check that the backend is running and try again.",
    );
  }

  if (!response.ok) {
    throw new Error(
      "Your session is not available in this browser. Refresh the page and sign in again.",
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
      "Your session is not available in this browser. Refresh the page and sign in again.",
    );
  }

  return payload;
}

/**
 * Legacy-compatible session helper.
 *
 * ResumeUploadModal currently imports requireAuthenticatedSession, so keep this
 * exported name while routing it through the backend cookie session.
 *
 * Returns:
 *   Confirmed backend session payload.
 */
export async function requireAuthenticatedSession() {
  return requireBackendSession();
}

/**
 * Best-effort browser Supabase session lookup for legacy direct Storage flows.
 *
 * Returns:
 *   Supabase auth session or null.
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
 * Build standard backend headers for cookie-auth API calls.
 *
 * Returns:
 *   Authenticated request headers for backend API calls.
 *
 * Throws:
 *   Error: If the API base URL is missing or no cookie session exists.
 */
export async function buildAuthenticatedApiHeaders() {
  if (!API_BASE_URL) {
    throw new Error("Missing VITE_API_BASE_URL.");
  }

  await requireBackendSession();

  return {
    "Content-Type": "application/json",
    Accept: "application/json",
  };
}

/**
 * Build the canonical storage path for a user's single active resume.
 *
 * Args:
 *   userId: Authenticated user ID.
 *   fileName: Original file name.
 *
 * Returns:
 *   Stable storage object path.
 */
export function buildResumeStoragePath(userId, fileName) {
  const extension = String(fileName || "resume.pdf").split(".").pop() || "pdf";
  return `${userId}/resume.${extension.toLowerCase()}`;
}

/**
 * Upload a resume file to Supabase Storage, overwriting the prior file if it exists.
 *
 * Note:
 *   This still depends on a browser Supabase session because storage upload is
 *   currently performed directly from the frontend.
 *
 * Args:
 *   params: Upload parameters.
 *   params.file: Resume PDF file.
 *
 * Returns:
 *   Upload result containing storage path and public URL.
 */
export async function uploadResumeFile({ file }) {
  const backendSession = await requireBackendSession();
  const browserSession = await getOptionalSupabaseSession();

  if (!browserSession?.user?.id) {
    throw new Error(
      "Your app session is active, but browser storage auth is missing. Refresh the page and sign in again.",
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
 * Create or update the user's active resume record through the backend.
 *
 * Args:
 *   params: Resume record parameters.
 *   params.originalFilename: Original uploaded file name.
 *   params.fileSizeBytes: File size in bytes.
 *   params.fileType: File MIME type.
 *   params.parseStatus: Parse status.
 *   params.rawText: Extracted raw text.
 *   params.parsedJson: Parsed resume JSON.
 *   params.parseWarnings: Parse warnings.
 *   params.atsTags: ATS tags.
 *   params.uploadSource: Upload source label.
 *   params.storagePath: Storage object path.
 *
 * Returns:
 *   Upserted resume row from the backend.
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
    let message = "Failed to save resume record.";

    try {
      const errorPayload = await response.json();
      message = normalizeApiErrorMessage(errorPayload, message);
    } catch {
      try {
        const text = await response.text();
        if (text?.trim()) {
          message = text;
        }
      } catch {
        // Keep default message.
      }
    }

    throw new Error(message);
  }

  return await response.json();
}

/**
 * Parse a stored resume record through the backend parser.
 *
 * Args:
 *   params: Parse parameters.
 *   params.resumeId: Resume row ID.
 *   params.rawText: Extracted raw text.
 *   params.fileType: File MIME type.
 *   params.extractionMethod: Extraction method label.
 *
 * Returns:
 *   Parse response payload.
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
    let message = "Resume parse request failed.";

    try {
      const errorPayload = await response.json();
      message = normalizeApiErrorMessage(errorPayload, message);
    } catch {
      try {
        const text = await response.text();
        if (text?.trim()) {
          message = text;
        }
      } catch {
        // Keep default message.
      }
    }

    throw new Error(message);
  }

  return await response.json();
}

/**
 * Fetch the canonical latest tracker resume from the backend.
 *
 * Returns:
 *   Latest resume summary from the tracker payload, or null when none exists.
 */
export async function fetchLatestTrackerResume() {
  const headers = await buildAuthenticatedApiHeaders();

  const response = await fetch(`${API_BASE_URL}/tracker`, {
    method: "GET",
    credentials: "include",
    headers,
  });

  if (!response.ok) {
    let message = "Failed to load tracker resume.";

    try {
      const errorPayload = await response.json();
      message = normalizeApiErrorMessage(errorPayload, message);
    } catch {
      try {
        const text = await response.text();
        if (text?.trim()) {
          message = text;
        }
      } catch {
        // Keep default message.
      }
    }

    throw new Error(message);
  }

  const payload = await response.json();
  return payload?.resume && typeof payload.resume === "object"
    ? payload.resume
    : null;
}

/**
 * Fetch the current resume record directly from the backend resume route.
 *
 * Returns:
 *   Current resume record, or null if not found.
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
    let message = "Failed to load current resume.";

    try {
      const errorPayload = await response.json();
      message = normalizeApiErrorMessage(errorPayload, message);
    } catch {
      try {
        const text = await response.text();
        if (text?.trim()) {
          message = text;
        }
      } catch {
        // Keep default message.
      }
    }

    throw new Error(message);
  }

  return await response.json();
}

/**
 * Save a resume record, then verify the backend tracker can see it.
 *
 * Args:
 *   params: Same parameters accepted by saveResumeRecord.
 *
 * Returns:
 *   Verified resume record, preferably from backend tracker state.
 */
export async function saveAndVerifyResumeRecord(params) {
  const savedResume = await saveResumeRecord(params);

  let trackerResume = null;

  try {
    trackerResume = await fetchLatestTrackerResume();
  } catch {
    // Allow the direct save result to stand if tracker refresh is temporarily unavailable.
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
 * Fetch all stored resumes for the authenticated user.
 *
 * Returns:
 *   Resume records ordered by most recent.
 */
export async function fetchMyResumes() {
  const currentResume = await fetchCurrentResumeRecord();
  return currentResume ? [currentResume] : [];
}