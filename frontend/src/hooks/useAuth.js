/**
 * @fileoverview Auth session hook for EarlyBloom.
 *
 * Uses backend cookie session as the app-shell source of truth.
 *
 * Principles:
 * - Public pages must remain usable while auth is being checked.
 * - Auth lookup should happen in the background.
 * - Restricted pages can still gate on resolved auth state.
 */

import { useEffect, useState, useCallback } from "react";
import { getSession, signOut } from "../lib/auth/authApi";

const AUTH_CHANGED_EVENT = "earlybloom:auth-changed";

/**
 * Broadcast that auth state changed somewhere in the app.
 *
 * @returns {void}
 */
export function notifyAuthChanged() {
  window.dispatchEvent(new Event(AUTH_CHANGED_EVENT));
}

/**
 * Auth hook.
 *
 * Returns:
 *   user: Current authenticated user or null.
 *   loading: Whether auth state is refreshing.
 *   refresh: Refresh auth state and return the current user.
 *   handleSignOut: Sign the user out.
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
  const [loading, setLoading] = useState(false);

  const fetchSession = useCallback(async () => {
    setLoading(true);

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
    let isMounted = true;

    async function bootstrapAuth() {
      setLoading(true);

      try {
        const session = await getSession();
        if (!isMounted) {
          return;
        }

        setUser(session?.user || null);
      } catch {
        if (!isMounted) {
          return;
        }

        setUser(null);
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    bootstrapAuth();

    function handleAuthChanged() {
      fetchSession();
    }

    window.addEventListener(AUTH_CHANGED_EVENT, handleAuthChanged);

    return () => {
      isMounted = false;
      window.removeEventListener(AUTH_CHANGED_EVENT, handleAuthChanged);
    };
  }, [fetchSession]);

  async function handleSignOut() {
    try {
      await signOut();
    } finally {
      setUser(null);
      setLoading(false);
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