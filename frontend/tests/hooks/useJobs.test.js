import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";

vi.mock("../../src/lib/jobs/jobsApi", () => ({
  fetchJobs: vi.fn(),
  fetchResolvedJobProfile: vi.fn(),
  shouldUseMockJobs: vi.fn(() => false),
}));

describe("useJobs", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  it(
    "retries the initial jobs load after a transient failure and then succeeds",
    async () => {
      const jobsApi = await import("../../src/lib/jobs/jobsApi");
      const { useJobs } = await import("../../src/hooks/useJobs");

      jobsApi.fetchJobs
        .mockRejectedValueOnce(
          Object.assign(new Error("Unable to load jobs at this time."), {
            status: 503,
          })
        )
        .mockResolvedValueOnce([
          {
            id: "job-1",
            title: "Junior Software Engineer",
            company: "EarlyBloom",
            location: "Atlanta, GA",
          },
        ]);

      jobsApi.fetchResolvedJobProfile.mockResolvedValue({
        desiredLevels: ["entry-level", "junior"],
        preferredRoleTypes: [],
        preferredWorkplaceTypes: [],
        preferredLocations: [],
        skills: ["react"],
        isLgbtFriendlyOnly: false,
      });

      const { result } = renderHook(() => useJobs());

      await waitFor(
        () => {
          expect(result.current.isLoading).toBe(false);
        },
        { timeout: 3000 }
      );

      expect(jobsApi.fetchJobs).toHaveBeenCalledTimes(2);
      expect(result.current.jobs).toHaveLength(1);
      expect(result.current.error).toBe("");
    }
  );

  it(
    "surfaces an error when all initial retry attempts fail",
    async () => {
      const jobsApi = await import("../../src/lib/jobs/jobsApi");
      const { useJobs } = await import("../../src/hooks/useJobs");

      jobsApi.fetchJobs.mockRejectedValue(
        Object.assign(new Error("Unable to load jobs at this time."), {
          status: 503,
        })
      );

      jobsApi.fetchResolvedJobProfile.mockResolvedValue({
        desiredLevels: ["entry-level", "junior"],
        preferredRoleTypes: [],
        preferredWorkplaceTypes: [],
        preferredLocations: [],
        skills: [],
        isLgbtFriendlyOnly: false,
      });

      const { result } = renderHook(() => useJobs());

      await waitFor(
        () => {
          expect(result.current.isLoading).toBe(false);
        },
        { timeout: 4000 }
      );

      expect(jobsApi.fetchJobs).toHaveBeenCalledTimes(3);
      expect(result.current.jobs).toEqual([]);
      expect(result.current.error).toBe(
        "Unable to load jobs at this time."
      );
    }
  );

  it("does not set an error after unmount when the request is aborted", async () => {
    const jobsApi = await import("../../src/lib/jobs/jobsApi");
    const { useJobs } = await import("../../src/hooks/useJobs");

    jobsApi.fetchJobs.mockImplementation(
      ({ signal } = {}) =>
        new Promise((resolve, reject) => {
          signal?.addEventListener(
            "abort",
            () => reject(new DOMException("Aborted", "AbortError")),
            { once: true }
          );

          setTimeout(() => resolve([]), 50);
        })
    );

    jobsApi.fetchResolvedJobProfile.mockResolvedValue({
      desiredLevels: ["entry-level", "junior"],
      preferredRoleTypes: [],
      preferredWorkplaceTypes: [],
      preferredLocations: [],
      skills: [],
      isLgbtFriendlyOnly: false,
    });

    const consoleSpy = vi
      .spyOn(console, "error")
      .mockImplementation(() => {});

    const { unmount } = renderHook(() => useJobs());

    unmount();

    await act(async () => {
      await new Promise((r) => setTimeout(r, 100));
    });

    expect(consoleSpy).not.toHaveBeenCalled();

    consoleSpy.mockRestore();
  });

    it(
    "keeps existing jobs visible when a refresh fails after a successful load",
    async () => {
        const jobsApi = await import("../../src/lib/jobs/jobsApi");
        const { useJobs } = await import("../../src/hooks/useJobs");

        jobsApi.fetchJobs
        .mockResolvedValueOnce([
            {
            id: "job-1",
            title: "Junior Software Engineer",
            company: "EarlyBloom",
            location: "Atlanta, GA",
            },
        ])
        .mockRejectedValue(
            Object.assign(new Error("Refreshing jobs failed."), {
            status: 503,
            })
        );

        jobsApi.fetchResolvedJobProfile.mockResolvedValue({
        desiredLevels: ["entry-level", "junior"],
        preferredRoleTypes: [],
        preferredWorkplaceTypes: [],
        preferredLocations: [],
        skills: [],
        isLgbtFriendlyOnly: false,
        });

        const { result } = renderHook(() => useJobs());

        await waitFor(() => {
        expect(result.current.jobs).toHaveLength(1);
        expect(result.current.isLoading).toBe(false);
        });

        act(() => {
        result.current.retry();
        });

        await waitFor(
        () => {
            expect(result.current.isRefreshing).toBe(false);
        },
        { timeout: 4000 }
        );

        expect(jobsApi.fetchJobs).toHaveBeenCalledTimes(4);
        expect(result.current.jobs).toHaveLength(1);
        expect(result.current.jobs[0].id).toBe("job-1");
        expect(result.current.error).toBe("Refreshing jobs failed.");
    }
    );
});