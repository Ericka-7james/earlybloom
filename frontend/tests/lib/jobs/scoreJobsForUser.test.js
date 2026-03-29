import { describe, it, expect } from "vitest";
import scoreJobsForUser from "../../../src/lib/jobs/scoreJobsForUser";

describe("scoreJobsForUser", () => {
  it("returns an empty array when rawJobs is not an array", () => {
    expect(scoreJobsForUser(null, {})).toEqual([]);
    expect(scoreJobsForUser(undefined, {})).toEqual([]);
    expect(scoreJobsForUser({}, {})).toEqual([]);
  });

  it("returns one scored object per raw job", () => {
    const rawJobs = [
      {
        id: "job-1",
        title: "Junior Frontend Engineer",
        company: "Bloom Labs",
        description:
          "Entry level frontend role using React, JavaScript, and CSS.",
        location: "Atlanta, GA",
        workplaceType: "Remote",
        employmentType: "Full-time",
        roleType: "Frontend",
        source: "greenhouse",
        sourceUrl: "https://example.com/job-1",
      },
      {
        id: "job-2",
        title: "Software Engineer",
        company: "Garden Systems",
        description: "General software engineering role.",
        location: "Remote",
      },
    ];

    const userProfile = {
      desiredRoles: ["Frontend Engineer", "Software Engineer"],
      skills: ["React", "JavaScript", "CSS"],
      preferredWorkplaceTypes: ["Remote"],
      preferredLocations: ["Atlanta, GA"],
    };

    const result = scoreJobsForUser(rawJobs, userProfile);

    expect(result).toHaveLength(2);
    expect(result[0].id).toBe("job-1");
    expect(result[1].id).toBe("job-2");
  });

  it("returns UI compatibility fields for each scored job", () => {
    const rawJobs = [
      {
        id: "job-3",
        title: "Junior Frontend Engineer",
        company: "Bloom Labs",
        description:
          "Entry level frontend role using React, JavaScript, and CSS.",
        location: "Atlanta, GA",
      },
    ];

    const userProfile = {
      desiredRoles: ["Frontend Engineer"],
      skills: ["React", "JavaScript", "CSS"],
      preferredLocations: ["Atlanta, GA"],
    };

    const [result] = scoreJobsForUser(rawJobs, userProfile);

    expect(result).toEqual(
      expect.objectContaining({
        id: "job-3",
        bloomFitScore: expect.any(Number),
        bloomVerdict: expect.any(String),
        bloomReasons: expect.any(Array),
        scoreBreakdown: expect.objectContaining({
          seniorityFit: expect.any(Number),
          skillsFit: expect.any(Number),
          accessibility: expect.any(Number),
          trust: expect.any(Number),
          preferenceFit: expect.any(Number),
        }),
        warningFlags: expect.any(Array),
        matchScore: expect.any(Number),
        fitTag: expect.any(String),
        reasons: expect.any(Array),
      })
    );
  });

  it("keeps legacy alias fields aligned with bloom fields", () => {
    const rawJobs = [
      {
        id: "job-4",
        title: "Junior Frontend Engineer",
        description: "React JavaScript CSS entry level frontend role.",
        location: "Remote",
      },
    ];

    const userProfile = {
      desiredRoles: ["Frontend Engineer"],
      skills: ["React", "JavaScript", "CSS"],
    };

    const [result] = scoreJobsForUser(rawJobs, userProfile);

    expect(result.matchScore).toBe(result.bloomFitScore);
    expect(result.fitTag).toBe(result.bloomVerdict);
    expect(result.reasons).toEqual(result.bloomReasons);
  });

  it("limits bloomReasons to at most 4 items", () => {
    const rawJobs = [
      {
        id: "job-5",
        title: "Junior Frontend Engineer",
        description:
          "Entry level frontend role using React JavaScript CSS HTML remote hybrid collaboration product UI.",
        location: "Atlanta, GA",
      },
    ];

    const userProfile = {
      desiredRoles: ["Frontend Engineer"],
      skills: ["React", "JavaScript", "CSS", "HTML", "UI Design"],
      preferredLocations: ["Atlanta, GA"],
      preferredWorkplaceTypes: ["Remote", "Hybrid"],
    };

    const [result] = scoreJobsForUser(rawJobs, userProfile);

    expect(result.bloomReasons.length).toBeLessThanOrEqual(4);
    expect(result.reasons.length).toBeLessThanOrEqual(4);
  });

  it("uses fallback identifiers when id is missing but jobId exists", () => {
    const rawJobs = [
      {
        jobId: "legacy-job-id",
        title: "Frontend Engineer I",
        description: "React role",
      },
    ];

    const [result] = scoreJobsForUser(rawJobs, {});

    expect(result.id).toBe("legacy-job-id");
  });

  it("uses fallback identifiers when id and jobId are missing but slug exists", () => {
    const rawJobs = [
      {
        slug: "frontend-engineer-i",
        title: "Frontend Engineer I",
        description: "React role",
      },
    ];

    const [result] = scoreJobsForUser(rawJobs, {});

    expect(result.id).toBe("frontend-engineer-i");
  });

  it("returns numeric scores clamped into a safe range", () => {
    const rawJobs = [
      {
        id: "job-6",
        title: "Frontend Engineer I",
        description: "React JavaScript CSS role",
      },
    ];

    const [result] = scoreJobsForUser(rawJobs, {
      skills: ["React", "JavaScript", "CSS"],
      desiredRoles: ["Frontend Engineer"],
    });

    expect(result.bloomFitScore).toBeGreaterThanOrEqual(0);
    expect(result.bloomFitScore).toBeLessThanOrEqual(100);
    expect(result.matchScore).toBeGreaterThanOrEqual(0);
    expect(result.matchScore).toBeLessThanOrEqual(100);
  });
});