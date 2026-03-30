import { supabase } from "./supabaseClient";
import { ensureUserSession } from "./auth";

export const RESUME_STORAGE_KEY = "earlybloom_resume_upload";
export const RESUME_MODAL_DISMISSED_KEY = "earlybloom_resume_modal_dismissed";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

export function buildResumeUiCache(file, resumeRecord = null) {
  return {
    id: resumeRecord?.id ?? null,
    name: file.name,
    size: file.size,
    type: file.type || "application/pdf",
    uploadedAt: new Date().toISOString(),
    parseStatus: resumeRecord?.parse_status ?? "pending",
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
}

export async function saveResumeRecord({
  originalFilename,
  fileSizeBytes,
  fileType = "application/pdf",
  parseStatus = "pending",
  rawText = null,
  parsedJson = null,
  parseWarnings = [],
}) {
  const user = await ensureUserSession();

  const { data, error } = await supabase
    .from("resumes")
    .insert({
      user_id: user.id,
      original_filename: originalFilename,
      file_size_bytes: fileSizeBytes,
      file_type: fileType,
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

  const {
    data: { session },
    error: sessionError,
  } = await supabase.auth.getSession();

  if (sessionError) {
    throw sessionError;
  }

  const accessToken = session?.access_token;
  if (!accessToken) {
    throw new Error("Missing authenticated session token.");
  }

  const response = await fetch(
    `${API_BASE_URL}/resume/${resumeId}/parse`,
    {
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
    }
  );

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
  const { data, error } = await supabase
    .from("resumes")
    .select("*")
    .order("created_at", { ascending: false });

  if (error) {
    throw error;
  }

  return data;
}