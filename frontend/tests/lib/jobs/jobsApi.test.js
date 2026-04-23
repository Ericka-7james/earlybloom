import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";

const ORIGINAL_ENV = { ...import.meta.env };

function createJsonResponse(payload, init = {}) {
  const status = init.status ?? 200;
  const ok = status >= 200 && status < 300;

  return {
    ok,
    status,
    async json() {
      return payload;
    },
    async text() {
      return typeof payload === "string" ? payload : JSON.stringify(payload);
    },
  };
}

describe("jobsApi", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();

    import.meta.env.VITE_API_BASE_URL = "http://localhost:8000";
    import.meta.env.VITE_USE_MOCK_JOBS = "false";
  });

  afterEach(() => {
    Object.keys(import.meta.env).forEach((key) => {
      if (!(key in ORIGINAL_ENV)) {
        delete import.meta.env[key];
      }
    });

    Object.assign(import.meta.env, ORIGINAL_ENV);
  });

  it("reuses in-flight GET requests when no AbortSignal is provided", async () => {
    const fetchSpy = vi.fn(
      () =>
        new Promise((resolve) => {
          setTimeout(() => {
            resolve(
              createJsonResponse({
                jobs: [
                  {
                    id: "job-1",
                    title: "Junior Software Engineer",
                    company: "EarlyBloom",
                    location: "Atlanta, GA",
                  },
                ],
              })
            );
          }, 10);
        })
    );

    vi.stubGlobal("fetch", fetchSpy);

    const { fetchJobs } = await import("../../../src/lib/jobs/jobsApi.js");

    const [firstResult, secondResult] = await Promise.all([
      fetchJobs(),
      fetchJobs(),
    ]);

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(firstResult).toHaveLength(1);
    expect(secondResult).toHaveLength(1);
    expect(firstResult[0].id).toBe("job-1");
    expect(secondResult[0].id).toBe("job-1");
  });

  it("does not reuse an in-flight GET request across callers with different AbortSignals", async () => {
    const fetchSpy = vi.fn((url, options = {}) => {
      const signal = options.signal;

      return new Promise((resolve, reject) => {
        const timeoutId = setTimeout(() => {
          resolve(
            createJsonResponse({
              jobs: [
                {
                  id: url.includes("location=atlanta") ? "job-atl" : "job-generic",
                  title: "Junior Developer",
                  company: "EarlyBloom",
                  location: "Atlanta, GA",
                },
              ],
            })
          );
        }, 20);

        signal?.addEventListener(
          "abort",
          () => {
            clearTimeout(timeoutId);
            reject(new DOMException("The operation was aborted.", "AbortError"));
          },
          { once: true }
        );
      });
    });

    vi.stubGlobal("fetch", fetchSpy);

    const { fetchJobs } = await import("../../../src/lib/jobs/jobsApi.js");

    const controllerA = new AbortController();
    const controllerB = new AbortController();

    const firstPromise = fetchJobs({
      signal: controllerA.signal,
      locationQuery: "atlanta",
    });

    const secondPromise = fetchJobs({
      signal: controllerB.signal,
      locationQuery: "atlanta",
    });

    controllerA.abort();

    await expect(firstPromise).rejects.toMatchObject({
      name: "AbortError",
    });

    await expect(secondPromise).resolves.toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: "job-atl",
        }),
      ])
    );

    expect(fetchSpy).toHaveBeenCalledTimes(2);
  });

  it("preserves AbortError instead of masking it as a generic network failure", async () => {
    const fetchSpy = vi.fn((_, options = {}) => {
      const signal = options.signal;

      return new Promise((resolve, reject) => {
        const timeoutId = setTimeout(() => {
          resolve(
            createJsonResponse({
              jobs: [],
            })
          );
        }, 50);

        signal?.addEventListener(
          "abort",
          () => {
            clearTimeout(timeoutId);
            reject(new DOMException("The operation was aborted.", "AbortError"));
          },
          { once: true }
        );
      });
    });

    vi.stubGlobal("fetch", fetchSpy);

    const { fetchJobs } = await import("../../../src/lib/jobs/jobsApi.js");

    const controller = new AbortController();
    const promise = fetchJobs({ signal: controller.signal });

    controller.abort();

    await expect(promise).rejects.toMatchObject({
      name: "AbortError",
    });

    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  it("surfaces backend error detail for non-ok responses", async () => {
    const fetchSpy = vi.fn(async () =>
      createJsonResponse(
        { detail: "Unable to load jobs at this time." },
        { status: 503 }
      )
    );

    vi.stubGlobal("fetch", fetchSpy);

    const { fetchJobs } = await import("../../../src/lib/jobs/jobsApi.js");

    await expect(fetchJobs()).rejects.toMatchObject({
      message: "Unable to load jobs at this time.",
      status: 503,
    });
  });

  it("normalizes jobs from a standard backend payload", async () => {
    const fetchSpy = vi.fn(async () =>
      createJsonResponse({
        jobs: [
          {
            id: "job-123",
            title: "Software Engineer I",
            company: "EarlyBloom",
            location: "Remote, United States",
            remote_type: "remote",
            viewer_state: {
              is_saved: true,
              is_hidden: false,
            },
          },
        ],
      })
    );

    vi.stubGlobal("fetch", fetchSpy);

    const { fetchJobs } = await import("../../../src/lib/jobs/jobsApi.js");

    const result = await fetchJobs();

    expect(result).toEqual([
      expect.objectContaining({
        id: "job-123",
        title: "Software Engineer I",
        company: "EarlyBloom",
        location: "Remote, United States",
        remote_type: "remote",
        is_saved: true,
        is_hidden: false,
      }),
    ]);
  });
});