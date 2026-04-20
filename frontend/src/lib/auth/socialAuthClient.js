import { createClient } from "@supabase/supabase-js";

const SUPABASE_URL = (import.meta.env.VITE_SUPABASE_URL || "").replace(/\/+$/, "");
const SUPABASE_PUBLISHABLE_KEY =
  import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY || "";

let browserClient = null;

function getBrowserSupabaseClient() {
  if (!SUPABASE_URL || !SUPABASE_PUBLISHABLE_KEY) {
    throw new Error("Missing Supabase browser auth environment variables.");
  }

  if (!browserClient) {
    browserClient = createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, {
      auth: {
        flowType: "pkce",
        detectSessionInUrl: false,
      },
    });
  }

  return browserClient;
}

export async function startOAuthProviderSignIn(provider) {
  const client = getBrowserSupabaseClient();

  const redirectTo = `${window.location.origin}/auth/callback`;

  const { data, error } = await client.auth.signInWithOAuth({
    provider,
    options: {
      redirectTo,
    },
  });

  if (error) {
    throw new Error(error.message || `Unable to start ${provider} sign-in.`);
  }

  return data;
}

export async function exchangeOAuthCodeFromUrl() {
  const client = getBrowserSupabaseClient();
  const url = new URL(window.location.href);
  const code = url.searchParams.get("code");
  const errorDescription = url.searchParams.get("error_description");
  const errorCode = url.searchParams.get("error");

  if (errorCode || errorDescription) {
    throw new Error(errorDescription || errorCode || "Social sign-in failed.");
  }

  if (!code) {
    throw new Error("Missing OAuth authorization code.");
  }

  const { data, error } = await client.auth.exchangeCodeForSession(code);

  if (error) {
    throw new Error(error.message || "Unable to complete social sign-in.");
  }

  const session = data?.session;

  if (!session?.access_token || !session?.refresh_token) {
    throw new Error("OAuth sign-in did not return a usable session.");
  }

  return {
    accessToken: session.access_token,
    refreshToken: session.refresh_token,
  };
}

export async function clearBrowserOAuthSession() {
  const client = getBrowserSupabaseClient();

  try {
    await client.auth.signOut();
  } catch {
    // Ignore browser cleanup failures.
  }
}