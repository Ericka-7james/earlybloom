/**
 * @fileoverview Auth session hook for EarlyBloom.
 *
 * Fetches current session from backend and exposes:
 * - user
 * - loading state
 * - refresh + signOut helpers
 */

import { useEffect, useState, useCallback } from "react";
import { getSession, signOut } from "../lib/auth/authApi";

/**
 * Auth hook.
 *
 * @returns {{
 *   user: object | null,
 *   loading: boolean,
 *   refresh: () => Promise<void>,
 *   handleSignOut: () => Promise<void>
 * }}
 */
export function useAuth() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchSession = useCallback(async () => {
    try {
      const session = await getSession();
      setUser(session?.user || null);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSession();
  }, [fetchSession]);

  async function handleSignOut() {
    await signOut();
    setUser(null);
  }

  return {
    user,
    loading,
    refresh: fetchSession,
    handleSignOut,
  };
}