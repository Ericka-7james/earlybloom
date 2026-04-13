/**
 * @fileoverview Backend-owned auth API helpers.
 *
 * These helpers intentionally talk only to the FastAPI backend so the browser
 * never needs direct Supabase configuration.
 */

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");

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

    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  if (response.status === 204) {
    return null;
  }

  return await response.json();
}

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

export async function signIn(payload) {
  return request("/auth/sign-in", {
    method: "POST",
    body: JSON.stringify({
      email: payload.email,
      password: payload.password,
    }),
  });
}

export async function signOut() {
  return request("/auth/sign-out", {
    method: "POST",
  });
}

export async function getSession() {
  try {
    return await request("/auth/session", {
      method: "GET",
    });
  } catch (error) {
    if (error?.status === 401) {
      return null;
    }

    throw error;
  }
}