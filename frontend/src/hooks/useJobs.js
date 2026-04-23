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

const INITIAL_JOBS_RETRY_DELAYS_MS = [450, 1200];

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

function isAbortError(error) {
  return (
    error instanceof DOMException
      ? error.name === "AbortError"
      : error instanceof Error && error.name === "AbortError"
  );
}

function isRetryableJobsError(error) {
  if (!error || typeof error !== "object") {
    return false;
  }

  const status = Number(error.status);
  if ([408, 429, 502, 503, 504].includes(status)) {
    return true;
  }

  const message =
    error instanceof Error && typeof error.message === "string"
      ? error.message.toLowerCase()
      : "";

  return (
    message.includes("unable to reach the server") ||
    message.includes("failed to fetch") ||
    message.includes("networkerror")
  );
}

function waitForRetry(delayMs, signal) {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException("The operation was aborted.", "AbortError"));
      return;
    }

    const timeoutId = window.setTimeout(() => {
      cleanup();
      resolve();
    }, delayMs);

    function handleAbort() {
      cleanup();
      reject(new DOMException("The operation was aborted.", "AbortError"));
    }

    function cleanup() {
      window.clearTimeout(timeoutId);
      signal?.removeEventListener("abort", handleAbort);
    }

    signal?.addEventListener("abort", handleAbort, { once: true });
  });
}

async function fetchJobsWithInitialRetry({
  signal,
  locationQuery,
  force = false,
  shouldRetry = false,
}) {
  const delays = shouldRetry ? INITIAL_JOBS_RETRY_DELAYS_MS : [];

  for (let attempt = 0; attempt <= delays.length; attempt += 1) {
    try {
      return await fetchJobs({
        signal,
        locationQuery,
        force: force || attempt > 0,
      });
    } catch (error) {
      if (isAbortError(error)) {
        throw error;
      }

      const hasNextAttempt = attempt < delays.length;
      if (!hasNextAttempt || !isRetryableJobsError(error)) {
        throw error;
      }

      await waitForRetry(delays[attempt], signal);
    }
  }

  return [];
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
      const isManualRetry = reloadKey > 0;
      const shouldRetryInitialJobsLoad =
        !shouldUseRefreshState || isManualRetry;

      if (shouldUseRefreshState) {
        setIsRefreshing(true);
      } else {
        setIsLoading(true);
      }

      setError("");

      const [jobsResult, profileResult] = await Promise.allSettled([
        fetchJobsWithInitialRetry({
          signal: controller.signal,
          locationQuery,
          force: isManualRetry,
          shouldRetry: shouldRetryInitialJobsLoad,
        }),
        fetchResolvedJobProfile({
          signal: controller.signal,
          force: isManualRetry,
        }),
      ]);

      if (controller.signal.aborted) {
        return;
      }

      let nextError = "";

      if (jobsResult.status === "fulfilled") {
        setJobs(Array.isArray(jobsResult.value) ? jobsResult.value : []);
        setHasLoadedOnce(true);
      } else if (isAbortError(jobsResult.reason)) {
        return;
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
      } else if (isAbortError(profileResult.reason)) {
        return;
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