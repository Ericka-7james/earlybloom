/**
 * @fileoverview Jobs data hook for EarlyBloom.
 *
 * This hook loads:
 * - the shared jobs feed
 * - the resolved profile inputs used for scoring and filtering
 *
 * Design goals:
 * - keep loading, retry, and abort handling centralized
 * - return stable default shapes when backend data is missing
 * - avoid stale state updates after request cancellation
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  fetchJobs,
  fetchResolvedJobProfile,
  shouldUseMockJobs,
} from "../lib/jobs/jobsApi";

const DEFAULT_RESOLVED_USER_PROFILE = {
  desiredLevels: ["entry-level", "junior"],
  preferredRoleTypes: [],
  preferredWorkplaceTypes: [],
  preferredLocations: [],
  skills: [],
  isLgbtFriendlyOnly: false,
};

/**
 * Returns a fresh copy of the default resolved-profile shape.
 *
 * @returns {{
 *   desiredLevels: string[],
 *   preferredRoleTypes: string[],
 *   preferredWorkplaceTypes: string[],
 *   preferredLocations: string[],
 *   skills: string[],
 *   isLgbtFriendlyOnly: boolean
 * }} Default resolved-profile object.
 */
function getDefaultResolvedUserProfile() {
  return {
    desiredLevels: [...DEFAULT_RESOLVED_USER_PROFILE.desiredLevels],
    preferredRoleTypes: [...DEFAULT_RESOLVED_USER_PROFILE.preferredRoleTypes],
    preferredWorkplaceTypes: [...DEFAULT_RESOLVED_USER_PROFILE.preferredWorkplaceTypes],
    preferredLocations: [...DEFAULT_RESOLVED_USER_PROFILE.preferredLocations],
    skills: [...DEFAULT_RESOLVED_USER_PROFILE.skills],
    isLgbtFriendlyOnly: DEFAULT_RESOLVED_USER_PROFILE.isLgbtFriendlyOnly,
  };
}

/**
 * Normalizes a resolved-profile payload into the app's stable frontend shape.
 *
 * @param {object | null | undefined} profile Raw resolved-profile payload.
 * @returns {{
 *   desiredLevels: string[],
 *   preferredRoleTypes: string[],
 *   preferredWorkplaceTypes: string[],
 *   preferredLocations: string[],
 *   skills: string[],
 *   isLgbtFriendlyOnly: boolean
 * }} Normalized resolved-profile object.
 */
function normalizeResolvedUserProfile(profile) {
  if (!profile || typeof profile !== "object") {
    return getDefaultResolvedUserProfile();
  }

  return {
    desiredLevels: Array.isArray(profile.desiredLevels)
      ? profile.desiredLevels
      : [...DEFAULT_RESOLVED_USER_PROFILE.desiredLevels],
    preferredRoleTypes: Array.isArray(profile.preferredRoleTypes)
      ? profile.preferredRoleTypes
      : [...DEFAULT_RESOLVED_USER_PROFILE.preferredRoleTypes],
    preferredWorkplaceTypes: Array.isArray(profile.preferredWorkplaceTypes)
      ? profile.preferredWorkplaceTypes
      : [...DEFAULT_RESOLVED_USER_PROFILE.preferredWorkplaceTypes],
    preferredLocations: Array.isArray(profile.preferredLocations)
      ? profile.preferredLocations
      : [...DEFAULT_RESOLVED_USER_PROFILE.preferredLocations],
    skills: Array.isArray(profile.skills)
      ? profile.skills
      : [...DEFAULT_RESOLVED_USER_PROFILE.skills],
    isLgbtFriendlyOnly:
      typeof profile.isLgbtFriendlyOnly === "boolean"
        ? profile.isLgbtFriendlyOnly
        : DEFAULT_RESOLVED_USER_PROFILE.isLgbtFriendlyOnly,
  };
}

/**
 * Loads jobs and resolved-profile data for the current viewer.
 *
 * @param {{
 *   viewerKey?: string
 * }} [options] Hook options.
 * @returns {{
 *   jobs: Array,
 *   resolvedUserProfile: {
 *     desiredLevels: string[],
 *     preferredRoleTypes: string[],
 *     preferredWorkplaceTypes: string[],
 *     preferredLocations: string[],
 *     skills: string[],
 *     isLgbtFriendlyOnly: boolean
 *   },
 *   isLoading: boolean,
 *   error: string,
 *   isMockMode: boolean,
 *   retry: () => void
 * }} Jobs state and helpers.
 */
export function useJobs(options = {}) {
  const { viewerKey = "guest" } = options;

  const [jobs, setJobs] = useState([]);
  const [resolvedUserProfile, setResolvedUserProfile] = useState(
    getDefaultResolvedUserProfile()
  );
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  /**
   * Triggers a jobs reload.
   *
   * @returns {void}
   */
  const retry = useCallback(() => {
    setReloadKey((currentValue) => currentValue + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    /**
     * Loads jobs and resolved-profile data in parallel.
     *
     * @returns {Promise<void>}
     */
    async function loadJobsData() {
      setIsLoading(true);
      setError("");

      try {
        const [nextJobs, nextResolvedUserProfile] = await Promise.all([
          fetchJobs({ signal: controller.signal }),
          fetchResolvedJobProfile({ signal: controller.signal }),
        ]);

        if (controller.signal.aborted) {
          return;
        }

        setJobs(Array.isArray(nextJobs) ? nextJobs : []);
        setResolvedUserProfile(
          normalizeResolvedUserProfile(nextResolvedUserProfile)
        );
      } catch (error) {
        if (controller.signal.aborted || error?.name === "AbortError") {
          return;
        }

        setJobs([]);
        setResolvedUserProfile(getDefaultResolvedUserProfile());
        setError(
          error instanceof Error
            ? error.message
            : "Something went wrong while loading jobs."
        );
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    }

    void loadJobsData();

    return () => {
      controller.abort();
    };
  }, [reloadKey, viewerKey]);

  const isMockMode = useMemo(() => shouldUseMockJobs(), []);

  return {
    jobs,
    resolvedUserProfile,
    isLoading,
    error,
    isMockMode,
    retry,
  };
}

export default useJobs;