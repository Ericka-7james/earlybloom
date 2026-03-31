/**
 * @fileoverview Backend-owned auth API helpers.
 *
 * These helpers intentionally talk only to the FastAPI backend so the browser
 * never needs direct Supabase configuration.
 */

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");

/**
 * Sends a JSON request to the backend auth API.
 *
 * @param {string} path Relative backend path beginning with "/".
 * @param {RequestInit} [options] Fetch options.
 * @returns {Promise<any>} Parsed JSON response body.
 * @throws {Error} If the request fails.
 */
async function request(path, options = {}) {
  if (!API_BASE_URL) {
    throw new Error("Missing VITE_API_BASE_URL.");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    let message = "Request failed.";

    try {
      const payload = await response.json();
      message = payload?.detail || payload?.message || message;
    } catch {
      // Keep fallback message.
    }

    throw new Error(message);
  }

  if (response.status === 204) {
    return null;
  }

  return await response.json();
}

/**
 * Creates a new account through the backend.
 *
 * @param {{
 *   email: string,
 *   password: string,
 *   displayName?: string
 * }} payload Sign-up payload.
 * @returns {Promise<any>} Backend response.
 */
export async function signUp(payload) {
  return request("/auth/sign-up", {
    method: "POST",
    body: JSON.stringify({
      email: payload.email,
      password: payload.password,
      display_name: payload.displayName || null,
    }),
  });
}

/**
 * Signs a user in through the backend.
 *
 * @param {{ email: string, password: string }} payload Sign-in payload.
 * @returns {Promise<any>} Backend response.
 */
export async function signIn(payload) {
  return request("/auth/sign-in", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Signs the current user out through the backend.
 *
 * @returns {Promise<any>} Backend response.
 */
export async function signOut() {
  return request("/auth/sign-out", {
    method: "POST",
  });
}

/**
 * Returns the current authenticated session summary from the backend.
 *
 * @returns {Promise<any>} Backend response.
 */
export async function getSession() {
  return request("/auth/session", {
    method: "GET",
  });
}