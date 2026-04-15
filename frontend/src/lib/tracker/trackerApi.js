const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");

function ensureApiBaseUrl() {
  if (!API_BASE_URL) {
    throw new Error("Missing VITE_API_BASE_URL.");
  }
}

async function request(path, options = {}) {
  ensureApiBaseUrl();

  let response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        ...(options.headers || {}),
      },
      ...options,
    });
  } catch {
    throw new Error(
      "Unable to reach the server. Check that the backend is running and try again.",
    );
  }

  if (!response.ok) {
    let message =
      path === "/tracker"
        ? "Failed to load tracker."
        : "Failed to save tracker preferences.";

    try {
      const errorPayload = await response.json();
      message = errorPayload?.detail || message;
    } catch {
      try {
        const text = await response.text();
        if (text?.trim()) {
          message = text;
        }
      } catch {
        // keep fallback
      }
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

export async function fetchTracker() {
  return request("/tracker", {
    method: "GET",
  });
}

export async function updateTrackerPreferences(payload) {
  return request("/tracker/preferences", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}