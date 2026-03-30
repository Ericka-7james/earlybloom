import { supabase } from "./supabaseClient";

export const RESUME_STORAGE_KEY = "earlybloom_resume_upload";
export const RESUME_MODAL_DISMISSED_KEY = "earlybloom_resume_modal_dismissed";
export const RESUME_RAW_TEXT_SESSION_KEY = "earlybloom_resume_raw_text";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

export function buildResumeUiCache(file, resumeRecord = null) {
  return {
    id: resumeRecord?.id ?? null,
    name: file.name,
    size: file.size,
    type: file.type || "application/pdf",
    uploadedAt: new Date().toISOString(),
    parseStatus: resumeRecord?.parse_status ?? "pending",
    isLocalOnly: resumeRecord?.isLocalOnly ?? false,
  };
}

export function cacheResumeUiState(cachedResume) {
  window.localStorage.setItem(
    RESUME_STORAGE_KEY,
    JSON.stringify(cachedResume)
  );

  window.sessionStorage.setItem(RESUME_MODAL_DISMISSED_KEY, "true");
}

export function readCachedResumeUiState() {
  try {
    const cachedResume = window.localStorage.getItem(RESUME_STORAGE_KEY);
    return cachedResume ? JSON.parse(cachedResume) : null;
  } catch {
    return null;
  }
}

export function clearCachedResumeUiState() {
  window.localStorage.removeItem(RESUME_STORAGE_KEY);
  window.sessionStorage.removeItem(RESUME_MODAL_DISMISSED_KEY);
  window.sessionStorage.removeItem(RESUME_RAW_TEXT_SESSION_KEY);
}

export function cacheResumeRawText(rawText) {
  if (!rawText) {
    window.sessionStorage.removeItem(RESUME_RAW_TEXT_SESSION_KEY);
    return;
  }

  window.sessionStorage.setItem(RESUME_RAW_TEXT_SESSION_KEY, rawText);
}

export function readCachedResumeRawText() {
  try {
    return window.sessionStorage.getItem(RESUME_RAW_TEXT_SESSION_KEY);
  } catch {
    return null;
  }
}

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

export async function requireAuthenticatedSession() {
  const session = await getOptionalSession();

  if (!session?.user) {
    throw new Error("Please sign in before saving your resume.");
  }

  return session;
}

export async function saveResumeRecord({
  originalFilename,
  fileSizeBytes,
  fileType = "application/pdf",
  parseStatus = "pending",
  rawText = null,
  parsedJson = null,
  parseWarnings = [],
  uploadSource = "web",
}) {
  const session = await requireAuthenticatedSession();

  const { data, error } = await supabase
    .from("resumes")
    .insert({
      user_id: session.user.id,
      original_filename: originalFilename,
      file_size_bytes: fileSizeBytes,
      file_type: fileType,
      upload_source: uploadSource,
      parse_status: parseStatus,
      raw_text: rawText,
      parsed_json: parsedJson,
      parse_warnings: parseWarnings,
    })
    .select()
    .single();

  if (error) {
    throw error;
  }

  return data;
}

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
      // keep default message
    }

    throw new Error(message);
  }

  return await response.json();
}

export async function fetchMyResumes() {
  await requireAuthenticatedSession();

  const { data, error } = await supabase
    .from("resumes")
    .select("*")
    .order("created_at", { ascending: false });

  if (error) {
    throw error;
  }

  return data;
}