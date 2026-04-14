import { requireAuthenticatedSession } from "../resumes";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

async function buildAuthHeaders() {
  if (!API_BASE_URL) {
    throw new Error("Missing VITE_API_BASE_URL.");
  }

  const session = await requireAuthenticatedSession();

  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${session.access_token}`,
  };
}

export async function fetchTracker() {
  const headers = await buildAuthHeaders();

  const response = await fetch(`${API_BASE_URL}/tracker`, {
    method: "GET",
    headers,
  });

  if (!response.ok) {
    let message = "Failed to load tracker.";

    try {
      const errorPayload = await response.json();
      message = errorPayload?.detail || message;
    } catch {
      // keep default
    }

    throw new Error(message);
  }

  return await response.json();
}

export async function updateTrackerPreferences(payload) {
  const headers = await buildAuthHeaders();

  const response = await fetch(`${API_BASE_URL}/tracker/preferences`, {
    method: "PATCH",
    headers,
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let message = "Failed to save tracker preferences.";

    try {
      const errorPayload = await response.json();
      message = errorPayload?.detail || message;
    } catch {
      // keep default
    }

    throw new Error(message);
  }

  return await response.json();
}