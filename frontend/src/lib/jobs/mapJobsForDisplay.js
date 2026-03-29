import mapJobsForDisplay from "../../../src/lib/jobs/mapJobsForDisplay";

describe("mapJobsForDisplay", () => {
  it("maps raw and scored jobs into display-ready objects", () => {
    const rawJobs = [
      {
        id: "job-1",
        title: "Frontend Engineer I",
        company: "Bloom Labs",
        location: {
          display: "Atlanta, GA",
          workplaceType: "Hybrid",
        },
        employmentType: "Full-time",
        roleType: "Frontend",
        description: "Build UI features.",
        compensation: {
          salaryMinUsd: 90000,
          salaryMaxUsd: 110000,
          salaryVisible: true,
        },
        postedAt: "2026-03-20",
        source: "greenhouse",
        sourceUrl: "https://example.com/job-1",
      },
    ];

    const scoredJobs = [
      {
        id: "job-1",
        bloomVerdict: "Real Junior",
        bloomFitScore: 86,
        bloomReasons: ["Good title match", "Frontend fit"],
        warningFlags: ["Mentions 2+ years"],
        scoreBreakdown: {
          seniorityFit: 30,
          skillsFit: 25,
          accessibilityFit: 12,
          trustFit: 10,
          preferenceFit: 9,
        },
        confidence: "high",
      },
    ];

    const result = mapJobsForDisplay(rawJobs, scoredJobs);

    expect(result).toEqual([
      {
        id: "job-1",
        title: "Frontend Engineer I",
        company: "Bloom Labs",
        location: "Atlanta, GA",
        workplaceType: "Hybrid",
        employmentType: "Full-time",
        roleType: "Frontend",
        description: "Build UI features.",
        fitTag: "Real Junior",
        matchScore: 86,
        reasons: ["Good title match", "Frontend fit"],
        warningFlags: ["Mentions 2+ years"],
        scoreBreakdown: {
          seniorityFit: 30,
          skillsFit: 25,
          accessibilityFit: 12,
          trustFit: 10,
          preferenceFit: 9,
        },
        confidence: "high",
        compensation: "$90,000 - $110,000",
        postedAt: "2026-03-20",
        source: "greenhouse",
        sourceUrl: "https://example.com/job-1",
      },
    ]);
  });

  it("falls back safely when raw and scored fields are missing", () => {
    const rawJobs = [{ id: "job-2" }];

    const result = mapJobsForDisplay(rawJobs, []);

    expect(result).toEqual([
      {
        id: "job-2",
        title: "Untitled role",
        company: "Unknown company",
        location: "Location not listed",
        workplaceType: null,
        employmentType: null,
        roleType: null,
        description: "",
        fitTag: "Too Senior",
        matchScore: 0,
        reasons: [],
        warningFlags: [],
        scoreBreakdown: null,
        confidence: null,
        compensation: null,
        postedAt: null,
        source: null,
        sourceUrl: null,
      },
    ]);
  });

  it("uses string location when location.display is unavailable", () => {
    const rawJobs = [
      {
        id: "job-3",
        location: "Remote - U.S.",
      },
    ];

    const result = mapJobsForDisplay(rawJobs, []);

    expect(result[0].location).toBe("Remote - U.S.");
  });

  it("uses jobLocation when other location shapes are unavailable", () => {
    const rawJobs = [
      {
        id: "job-4",
        jobLocation: "New York, NY",
      },
    ];

    const result = mapJobsForDisplay(rawJobs, []);

    expect(result[0].location).toBe("New York, NY");
  });

  it("uses top-level workplaceType before nested location.workplaceType", () => {
    const rawJobs = [
      {
        id: "job-5",
        workplaceType: "Remote",
        location: {
          display: "Atlanta, GA",
          workplaceType: "Hybrid",
        },
      },
    ];

    const result = mapJobsForDisplay(rawJobs, []);

    expect(result[0].workplaceType).toBe("Remote");
  });

  it("uses fallback reasons and matchScore from legacy scored fields", () => {
    const rawJobs = [{ id: "job-6" }];

    const scoredJobs = [
      {
        id: "job-6",
        fitTag: "Stretch Role",
        matchScore: 64,
        reasons: ["Legacy reason"],
      },
    ];

    const result = mapJobsForDisplay(rawJobs, scoredJobs);

    expect(result[0].fitTag).toBe("Stretch Role");
    expect(result[0].matchScore).toBe(64);
    expect(result[0].reasons).toEqual(["Legacy reason"]);
  });

  it("normalizes score breakdown from mixed key names", () => {
    const rawJobs = [{ id: "job-7" }];

    const scoredJobs = [
      {
        id: "job-7",
        scoreBreakdown: {
          seniorityFit: 20,
          skillsFit: 18,
          accessibility: 11,
          trust: 7,
        },
      },
    ];

    const result = mapJobsForDisplay(rawJobs, scoredJobs);

    expect(result[0].scoreBreakdown).toEqual({
      seniorityFit: 20,
      skillsFit: 18,
      accessibilityFit: 11,
      trustFit: 7,
      preferenceFit: 0,
    });
  });

  it("uses scored warningFlags before raw warnings", () => {
    const rawJobs = [
      {
        id: "job-8",
        warnings: ["Raw warning"],
      },
    ];

    const scoredJobs = [
      {
        id: "job-8",
        warningFlags: ["Scored warning"],
      },
    ];

    const result = mapJobsForDisplay(rawJobs, scoredJobs);

    expect(result[0].warningFlags).toEqual(["Scored warning"]);
  });

  it("falls back to raw warnings when scored warningFlags are absent", () => {
    const rawJobs = [
      {
        id: "job-9",
        warnings: ["Raw warning"],
      },
    ];

    const result = mapJobsForDisplay(rawJobs, []);

    expect(result[0].warningFlags).toEqual(["Raw warning"]);
  });

  it("formats compensation as minimum plus when only salaryMinUsd is present", () => {
    const rawJobs = [
      {
        id: "job-10",
        compensation: {
          salaryMinUsd: 95000,
          salaryVisible: true,
        },
      },
    ];

    const result = mapJobsForDisplay(rawJobs, []);

    expect(result[0].compensation).toBe("$95,000+");
  });

  it("returns null compensation when salary is hidden", () => {
    const rawJobs = [
      {
        id: "job-11",
        compensation: {
          salaryMinUsd: 95000,
          salaryMaxUsd: 120000,
          salaryVisible: false,
        },
      },
    ];

    const result = mapJobsForDisplay(rawJobs, []);

    expect(result[0].compensation).toBeNull();
  });

  it("defaults unknown verdicts to Too Senior", () => {
    const rawJobs = [{ id: "job-12" }];

    const scoredJobs = [
      {
        id: "job-12",
        bloomVerdict: "Some New Verdict",
      },
    ];

    const result = mapJobsForDisplay(rawJobs, scoredJobs);

    expect(result[0].fitTag).toBe("Too Senior");
  });
});