/**
 * @fileoverview Authentication session hook for EarlyBloom.
 *
 * This hook treats the backend cookie session as the single source of truth
 * for application authentication state.
 *
 * Design goals:
 * - keep public pages usable while session lookup happens in the background
 * - normalize auth refresh behavior across the app
 * - avoid stale state updates after unmount
 * - provide a small, production-safe API to components
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { getSession, signOut } from "../lib/auth/authApi";

const AUTH_CHANGED_EVENT = "earlybloom:auth-changed";

/**
 * Broadcasts an auth-state change event to the current browser window.
 *
 * Components using this hook listen for the event and refresh local session
 * state when it occurs.
 *
 * @returns {void}
 */
export function notifyAuthChanged() {
  if (typeof window === "undefined") {
    return;
  }

  window.dispatchEvent(new Event(AUTH_CHANGED_EVENT));
}

/**
 * Reads and manages the current authenticated backend session.
 *
 * @returns {{
 *   user: object | null,
 *   loading: boolean,
 *   refresh: () => Promise<object | null>,
 *   handleSignOut: () => Promise<void>
 * }} Auth state and actions.
 */
export function useAuth() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false);

  const isMountedRef = useRef(true);
  const hasBootstrappedRef = useRef(false);

  /**
   * Applies a user value only while the hook is mounted.
   *
   * @param {object | null} nextUser The next authenticated user value.
   * @returns {void}
   */
  const applyUserSafely = useCallback((nextUser) => {
    if (!isMountedRef.current) {
      return;
    }

    setUser(nextUser);
  }, []);

  /**
   * Applies a loading value only while the hook is mounted.
   *
   * @param {boolean} nextLoading Whether auth loading is active.
   * @returns {void}
   */
  const applyLoadingSafely = useCallback((nextLoading) => {
    if (!isMountedRef.current) {
      return;
    }

    setLoading(nextLoading);
  }, []);

  /**
   * Refreshes the current backend session and updates local auth state.
   *
   * @returns {Promise<object | null>} The authenticated user when available.
   */
  const refresh = useCallback(async () => {
    applyLoadingSafely(true);

    try {
      const session = await getSession();
      const nextUser = session?.user || null;
      applyUserSafely(nextUser);
      return nextUser;
    } catch {
      applyUserSafely(null);
      return null;
    } finally {
      applyLoadingSafely(false);
    }
  }, [applyLoadingSafely, applyUserSafely]);

  useEffect(() => {
    isMountedRef.current = true;

    /**
     * Performs the initial auth bootstrap once for the hook instance.
     *
     * @returns {Promise<void>}
     */
    async function bootstrapAuth() {
      if (hasBootstrappedRef.current) {
        return;
      }

      hasBootstrappedRef.current = true;
      await refresh();
    }

    /**
     * Handles broadcast auth changes from elsewhere in the app.
     *
     * @returns {void}
     */
    function handleAuthChanged() {
      void refresh();
    }

    void bootstrapAuth();

    if (typeof window !== "undefined") {
      window.addEventListener(AUTH_CHANGED_EVENT, handleAuthChanged);
    }

    return () => {
      isMountedRef.current = false;

      if (typeof window !== "undefined") {
        window.removeEventListener(AUTH_CHANGED_EVENT, handleAuthChanged);
      }
    };
  }, [refresh]);

  /**
   * Signs the current user out through the backend and clears local state.
   *
   * @returns {Promise<void>}
   */
  async function handleSignOut() {
    applyLoadingSafely(true);

    try {
      await signOut();
    } finally {
      applyUserSafely(null);
      applyLoadingSafely(false);
      notifyAuthChanged();
    }
  }

  return {
    user,
    loading,
    refresh,
    handleSignOut,
  };
}

export default useAuth;