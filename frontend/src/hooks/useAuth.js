/**
 * @fileoverview Auth session hook for EarlyBloom.
 *
 * Fetches current session from backend and exposes:
 * - user
 * - loading state
 * - refresh + signOut helpers
 *
 * Also listens for app-wide auth changes so Navbar and pages stay in sync.
 */

import { useEffect, useState, useCallback } from "react";
import { getSession, signOut } from "../lib/auth/authApi";

const AUTH_CHANGED_EVENT = "earlybloom:auth-changed";

/**
 * Broadcasts that auth state changed somewhere in the app.
 */
export function notifyAuthChanged() {
  window.dispatchEvent(new Event(AUTH_CHANGED_EVENT));
}

/**
 * Auth hook.
 *
 * @returns {{
 *   user: object | null,
 *   loading: boolean,
 *   refresh: () => Promise<object | null>,
 *   handleSignOut: () => Promise<void>
 * }}
 */
export function useAuth() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchSession = useCallback(async () => {
    try {
      const session = await getSession();
      const nextUser = session?.user || null;
      setUser(nextUser);
      return nextUser;
    } catch {
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSession();

    function handleAuthChanged() {
      setLoading(true);
      fetchSession();
    }

    window.addEventListener(AUTH_CHANGED_EVENT, handleAuthChanged);

    return () => {
      window.removeEventListener(AUTH_CHANGED_EVENT, handleAuthChanged);
    };
  }, [fetchSession]);

  async function handleSignOut() {
    try {
      await signOut();
    } finally {
      setUser(null);
      notifyAuthChanged();
    }
  }

  return {
    user,
    loading,
    refresh: fetchSession,
    handleSignOut,
  };
}