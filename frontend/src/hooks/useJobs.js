// frontend/src/hooks/useJobs.js
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
 * - keep previous jobs visible during refresh
 * - distinguish first-load blocking from background refreshes
 * - degrade gracefully when one request succeeds and the other fails
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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

function getReadableErrorMessage(error, fallbackMessage) {
  if (error instanceof Error && error.message?.trim()) {
    return error.message;
  }

  return fallbackMessage;
}

export function useJobs(options = {}) {
  const {
    viewerKey = "guest",
    locationQuery = "",
  } = options;

  const [jobs, setJobs] = useState([]);
  const [resolvedUserProfile, setResolvedUserProfile] = useState(
    getDefaultResolvedUserProfile()
  );
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  const jobsRef = useRef(jobs);
  const hasLoadedOnceRef = useRef(hasLoadedOnce);

  useEffect(() => {
    jobsRef.current = jobs;
  }, [jobs]);

  useEffect(() => {
    hasLoadedOnceRef.current = hasLoadedOnce;
  }, [hasLoadedOnce]);

  const retry = useCallback(() => {
    setReloadKey((currentValue) => currentValue + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    async function loadJobsData() {
      const existingJobs = jobsRef.current;
      const existingHasLoadedOnce = hasLoadedOnceRef.current;
      const hasExistingJobs =
        Array.isArray(existingJobs) && existingJobs.length > 0;
      const shouldUseRefreshState = existingHasLoadedOnce || hasExistingJobs;

      if (shouldUseRefreshState) {
        setIsRefreshing(true);
      } else {
        setIsLoading(true);
      }

      setError("");

      const [jobsResult, profileResult] = await Promise.allSettled([
        fetchJobs({
          signal: controller.signal,
          locationQuery,
        }),
        fetchResolvedJobProfile({ signal: controller.signal }),
      ]);

      if (controller.signal.aborted) {
        return;
      }

      let nextError = "";

      if (jobsResult.status === "fulfilled") {
        setJobs(Array.isArray(jobsResult.value) ? jobsResult.value : []);
        setHasLoadedOnce(true);
      } else if (!hasExistingJobs && !existingHasLoadedOnce) {
        setJobs([]);
        nextError = getReadableErrorMessage(
          jobsResult.reason,
          "Something went wrong while loading jobs."
        );
      } else {
        nextError = getReadableErrorMessage(
          jobsResult.reason,
          "Refreshing jobs failed. Showing the last loaded results."
        );
      }

      if (profileResult.status === "fulfilled") {
        setResolvedUserProfile(
          normalizeResolvedUserProfile(profileResult.value)
        );
      } else if (!existingHasLoadedOnce && !hasExistingJobs) {
        setResolvedUserProfile(getDefaultResolvedUserProfile());

        if (!nextError) {
          nextError = getReadableErrorMessage(
            profileResult.reason,
            "Something went wrong while loading your job profile."
          );
        }
      }

      setError(nextError);
      setIsLoading(false);
      setIsRefreshing(false);
    }

    void loadJobsData();

    return () => {
      controller.abort();
    };
  }, [reloadKey, viewerKey, locationQuery]);

  const isMockMode = useMemo(() => shouldUseMockJobs(), []);

  return {
    jobs,
    resolvedUserProfile,
    isLoading,
    isRefreshing,
    hasLoadedOnce,
    error,
    isMockMode,
    retry,
  };
}

export default useJobs;