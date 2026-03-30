import { useCallback, useEffect, useState } from "react";
import { fetchJobs, shouldUseMockJobs } from "../lib/jobs/jobsApi";

export function useJobs() {
  const [jobs, setJobs] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  const retry = useCallback(() => {
    setReloadKey((value) => value + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    async function loadJobs() {
      setIsLoading(true);
      setError("");

      try {
        const nextJobs = await fetchJobs({ signal: controller.signal });
        setJobs(Array.isArray(nextJobs) ? nextJobs : []);
      } catch (err) {
        if (err?.name === "AbortError") {
          return;
        }

        setJobs([]);
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

    loadJobs();

    return () => controller.abort();
  }, [reloadKey]);

  return {
    jobs,
    isLoading,
    error,
    isMockMode: shouldUseMockJobs(),
    retry,
  };
}