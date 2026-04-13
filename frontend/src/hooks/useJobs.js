import { useCallback, useEffect, useState } from "react";
import {
  fetchJobs,
  fetchResolvedJobProfile,
  shouldUseMockJobs,
} from "../lib/jobs/jobsApi";

const DEFAULT_RESOLVED_USER_PROFILE = {
  desiredLevels: ["entry-level", "junior"],
  preferredRoleTypes: [],
  preferredWorkplaceTypes: [],
  skills: [],
  isLgbtFriendlyOnly: false,
};

export function useJobs(options = {}) {
  const { viewerKey = "guest" } = options;

  const [jobs, setJobs] = useState([]);
  const [resolvedUserProfile, setResolvedUserProfile] = useState(
    DEFAULT_RESOLVED_USER_PROFILE
  );
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  const retry = useCallback(() => {
    setReloadKey((value) => value + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();

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
          nextResolvedUserProfile && typeof nextResolvedUserProfile === "object"
            ? {
                ...DEFAULT_RESOLVED_USER_PROFILE,
                ...nextResolvedUserProfile,
              }
            : DEFAULT_RESOLVED_USER_PROFILE
        );
      } catch (err) {
        if (err?.name === "AbortError") {
          return;
        }

        setJobs([]);
        setResolvedUserProfile(DEFAULT_RESOLVED_USER_PROFILE);
        setError(
          err instanceof Error
            ? err.message
            : "Something went wrong while loading jobs."
        );
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    }

    loadJobsData();

    return () => controller.abort();
  }, [reloadKey, viewerKey]);

  return {
    jobs,
    resolvedUserProfile,
    isLoading,
    error,
    isMockMode: shouldUseMockJobs(),
    retry,
  };
}

export default useJobs;