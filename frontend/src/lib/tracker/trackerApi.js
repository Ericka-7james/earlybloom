/**
 * @fileoverview Tracker API client for EarlyBloom.
 *
 * This module provides a small wrapper around tracker-related backend calls.
 * Requests rely on the backend's cookie-auth session and return normalized
 * error messages suitable for product UI.
 */

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");

/**
 * Ensures the configured backend API base URL exists.
 *
 * @throws {Error} When the API base URL is missing.
 * @returns {void}
 */
function ensureApiBaseUrl() {
  if (!API_BASE_URL) {
    throw new Error("Missing VITE_API_BASE_URL.");
  }
}

/**
 * Reads a backend error payload and converts it into a user-friendly message.
 *
 * @param {Response} response Fetch response object.
 * @param {string} fallbackMessage Message used when no backend detail is present.
 * @returns {Promise<string>} A readable error message.
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
    // Keep fallback.
  }

  return fallbackMessage;
}

/**
 * Performs a tracker API request using backend cookie authentication.
 *
 * @param {string} path Backend API path.
 * @param {RequestInit} [options] Fetch options.
 * @returns {Promise<any>} Parsed JSON response, or null for 204 responses.
 */
async function request(path, options = {}) {
  ensureApiBaseUrl();

  let response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      credentials: "include",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
      ...options,
    });
  } catch {
    throw new Error(
      "Unable to reach the server. Check that the backend is running and try again."
    );
  }

  if (!response.ok) {
    const fallbackMessage =
      path === "/tracker"
        ? "Failed to load tracker."
        : "Failed to save tracker preferences.";

    const message = await readErrorMessage(response, fallbackMessage);
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  if (response.status === 204) {
    return null;
  }

  return await response.json();
}

/**
 * Fetches the current authenticated user's tracker payload.
 *
 * @returns {Promise<object>} Tracker response payload.
 */
export async function fetchTracker() {
  return request("/tracker", {
    method: "GET",
  });
}

/**
 * Updates tracker preference fields for the current authenticated user.
 *
 * @param {object} payload Tracker preference update payload.
 * @returns {Promise<object>} Updated tracker preferences response.
 */
export async function updateTrackerPreferences(payload) {
  return request("/tracker/preferences", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}