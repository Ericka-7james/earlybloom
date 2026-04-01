import { supabase } from "./supabaseClient";

export const RESUME_STORAGE_KEY = "earlybloom_resume_upload";
export const RESUME_MODAL_DISMISSED_KEY = "earlybloom_resume_modal_dismissed";
export const RESUME_RAW_TEXT_SESSION_KEY = "earlybloom_resume_raw_text";
export const RESUME_BUCKET_NAME = "resume-uploads";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

/**
 * Build local UI cache state for a resume upload.
 *
 * @param {File} file Uploaded file object.
 * @param {Object | null} resumeRecord Stored resume record if available.
 * @returns {Object} Resume UI cache payload.
 */
export function buildResumeUiCache(file, resumeRecord = null) {
  return {
    id: resumeRecord?.id ?? null,
    name: file.name,
    size: file.size,
    type: file.type || "application/pdf",
    uploadedAt: new Date().toISOString(),
    parseStatus: resumeRecord?.parse_status ?? "pending",
    atsTags: Array.isArray(resumeRecord?.ats_tags) ? resumeRecord.ats_tags : [],
    isLocalOnly: resumeRecord?.isLocalOnly ?? false,
  };
}

/**
 * Cache resume UI state locally.
 *
 * @param {Object} cachedResume Resume UI cache payload.
 * @returns {void}
 */
export function cacheResumeUiState(cachedResume) {
  window.localStorage.setItem(
    RESUME_STORAGE_KEY,
    JSON.stringify(cachedResume)
  );

  window.sessionStorage.setItem(RESUME_MODAL_DISMISSED_KEY, "true");
}

/**
 * Read cached resume UI state.
 *
 * @returns {Object | null} Cached resume UI state, if present.
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
 * @returns {void}
 */
export function clearCachedResumeUiState() {
  window.localStorage.removeItem(RESUME_STORAGE_KEY);
  window.sessionStorage.removeItem(RESUME_MODAL_DISMISSED_KEY);
  window.sessionStorage.removeItem(RESUME_RAW_TEXT_SESSION_KEY);
}

/**
 * Cache extracted raw resume text in session storage.
 *
 * @param {string | null | undefined} rawText Extracted raw text.
 * @returns {void}
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
 * @returns {string | null} Cached raw text if present.
 */
export function readCachedResumeRawText() {
  try {
    return window.sessionStorage.getItem(RESUME_RAW_TEXT_SESSION_KEY);
  } catch {
    return null;
  }
}

/**
 * Fetch the current optional authenticated session.
 *
 * @returns {Promise<Object | null>} Supabase auth session or null.
 */
export async function getOptionalSession() {
  const {
    data: { session },
    error,
  } = await supabase.auth.getSession();

  if (error) {
    throw error;
  }

  return session ?? null;
}

/**
 * Require an authenticated session.
 *
 * @returns {Promise<Object>} Authenticated session.
 * @throws {Error} If the user is not signed in.
 */
export async function requireAuthenticatedSession() {
  const session = await getOptionalSession();

  if (!session?.user) {
    throw new Error("Please sign in before saving your resume.");
  }

  return session;
}

/**
 * Build the canonical storage path for a user's single active resume.
 *
 * @param {string} userId Authenticated user ID.
 * @param {string} fileName Original file name.
 * @returns {string} Stable storage object path.
 */
export function buildResumeStoragePath(userId, fileName) {
  const extension = String(fileName || "resume.pdf").split(".").pop() || "pdf";
  return `${userId}/resume.${extension.toLowerCase()}`;
}

/**
 * Upload a resume file to Supabase Storage, overwriting the prior file if it exists.
 *
 * @param {Object} params Upload parameters.
 * @param {File} params.file Resume PDF file.
 * @returns {Promise<{ storagePath: string, publicUrl: string | null }>} Upload result.
 */
export async function uploadResumeFile({ file }) {
  const session = await requireAuthenticatedSession();
  const userId = session.user.id;
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
 * Upsert the user's single active resume record.
 *
 * @param {Object} params Resume record parameters.
 * @param {string} params.originalFilename Original uploaded file name.
 * @param {number} params.fileSizeBytes File size in bytes.
 * @param {string} [params.fileType="application/pdf"] File MIME type.
 * @param {string} [params.parseStatus="pending"] Parse status.
 * @param {string | null} [params.rawText=null] Extracted raw text.
 * @param {Object | null} [params.parsedJson=null] Parsed resume JSON.
 * @param {string[]} [params.parseWarnings=[]] Parse warnings.
 * @param {string[]} [params.atsTags=[]] ATS tags.
 * @param {string} [params.uploadSource="web"] Upload source label.
 * @param {string | null} [params.storagePath=null] Storage object path.
 * @returns {Promise<Object>} Upserted resume row.
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
  const session = await requireAuthenticatedSession();

  const payload = {
    user_id: session.user.id,
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
  };

  const { data, error } = await supabase
    .from("resumes")
    .upsert(payload, { onConflict: "user_id" })
    .select()
    .single();

  if (error) {
    throw error;
  }

  return data;
}

/**
 * Parse a stored resume record through the backend parser.
 *
 * @param {Object} params Parse parameters.
 * @param {string} params.resumeId Resume row ID.
 * @param {string} params.rawText Extracted raw text.
 * @param {string} [params.fileType="application/pdf"] File MIME type.
 * @param {string} [params.extractionMethod="text"] Extraction method label.
 * @returns {Promise<Object>} Parse response payload.
 */
export async function parseResumeRecord({
  resumeId,
  rawText,
  fileType = "application/pdf",
  extractionMethod = "text",
}) {
  if (!API_BASE_URL) {
    throw new Error("Missing VITE_API_BASE_URL.");
  }

  const session = await requireAuthenticatedSession();
  const accessToken = session.access_token;

  const response = await fetch(`${API_BASE_URL}/resume/${resumeId}/parse`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
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
      message = errorPayload?.detail || message;
    } catch {
      // Keep default message.
    }

    throw new Error(message);
  }

  return await response.json();
}

/**
 * Fetch all stored resumes for the authenticated user.
 *
 * With the single-resume-per-user model, this will usually return zero or one row.
 *
 * @returns {Promise<Object[]>} Resume records ordered by most recent.
 */
export async function fetchMyResumes() {
  await requireAuthenticatedSession();

  const { data, error } = await supabase
    .from("resumes")
    .select("*")
    .order("updated_at", { ascending: false });

  if (error) {
    throw error;
  }

  return data;
}