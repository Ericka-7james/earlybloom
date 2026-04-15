/**
 * @fileoverview Tests for resume-to-job skill overlap scoring behavior.
 */

import { describe, expect, it } from "vitest";
import { scoreJobsForUser } from "../../../src/lib/jobs/scoreJobsForUser";

function makeJob(overrides = {}) {
  return {
    id: "job-1",
    title: "Junior Software Engineer",
    company: "EarlyBloom",
    location: "Remote",
    description:
      "Entry level role with mentorship, onboarding, and clear responsibilities.",
    summary: "Junior-friendly engineering role.",
    skills: ["React", "JavaScript", "AWS"],
    required_skills: [],
    preferred_skills: [],
    remote: true,
    remote_type: "remote",
    experience_level: "junior",
    role_type: "software-engineering",
    warnings: [],
    ...overrides,
  };
}

function makeUser(overrides = {}) {
  return {
    skills: ["React", "SQL"],
    experienceYears: 1,
    remotePreference: "remote",
    preferredLocations: [],
    targetTitles: [],
    ...overrides,
  };
}

describe("scoreJobsForUser", () => {
  it("returns an empty array for non-array raw jobs input", () => {
    expect(scoreJobsForUser(null, {})).toEqual([]);
    expect(scoreJobsForUser(undefined, {})).toEqual([]);
    expect(scoreJobsForUser({}, {})).toEqual([]);
  });

  it("stores matched skills for UI use", () => {
    const rawJobs = [
      makeJob({
        skills: ["React", "JavaScript", "AWS", "SQL"],
      }),
    ];

    const userProfile = makeUser({
      skills: ["React", "SQL", "Docker"],
    });

    const [result] = scoreJobsForUser(rawJobs, userProfile);

    expect(result.matchedSkills).toEqual(["React", "SQL"]);
  });

  it("increases bloomFitScore when job and user skills overlap", () => {
    const rawJobs = [
      makeJob({
        skills: ["React", "JavaScript", "AWS"],
      }),
    ];

    const noMatchUser = makeUser({
      skills: ["Excel"],
    });

    const overlapUser = makeUser({
      skills: ["React", "AWS"],
    });

    const [withoutOverlap] = scoreJobsForUser(rawJobs, noMatchUser);
    const [withOverlap] = scoreJobsForUser(rawJobs, overlapUser);

    expect(withOverlap.bloomFitScore).toBeGreaterThan(
      withoutOverlap.bloomFitScore
    );
    expect(withOverlap.matchedSkills).toEqual(["React", "AWS"]);
    expect(withOverlap.scoreBreakdown.skillOverlapBonus).toBeGreaterThan(0);
  });

  it("keeps the overlap bonus additive and bounded", () => {
    const rawJobs = [
      makeJob({
        skills: [
          "Python",
          "SQL",
          "Docker",
          "AWS",
          "FastAPI",
          "Git",
          "Linux",
          "React",
          "Tableau",
          "Power BI",
        ],
      }),
    ];

    const userProfile = makeUser({
      skills: [
        "Python",
        "SQL",
        "Docker",
        "AWS",
        "FastAPI",
        "Git",
        "Linux",
        "React",
        "Tableau",
        "Power BI",
      ],
      remotePreference: "flexible",
    });

    const [result] = scoreJobsForUser(rawJobs, userProfile);

    expect(result.matchedSkills).toEqual([
      "Python",
      "SQL",
      "Docker",
      "AWS",
      "FastAPI",
      "Git",
      "Linux",
      "React",
      "Tableau",
      "Power BI",
    ]);
    expect(result.scoreBreakdown.skillOverlapBonus).toBeLessThanOrEqual(8);
    expect(result.bloomFitScore).toBeLessThanOrEqual(100);
  });

  it("returns an empty matchedSkills list when the user has no skills", () => {
    const rawJobs = [
      makeJob({
        skills: ["Excel", "SQL", "Tableau", "Power BI"],
      }),
    ];

    const userProfile = makeUser({
      skills: [],
    });

    const [result] = scoreJobsForUser(rawJobs, userProfile);

    expect(result.matchedSkills).toEqual([]);
    expect(result.scoreBreakdown.skillOverlapBonus).toBe(0);
  });

  it("uses canonical casing from job skills in matchedSkills", () => {
    const rawJobs = [
      makeJob({
        title: "Business Systems Analyst",
        skills: ["Power BI", "ServiceNow", "Jira"],
        remote: false,
        remote_type: "hybrid",
        experience_level: "junior",
      }),
    ];

    const userProfile = makeUser({
      skills: ["Power BI", "Jira"],
      remotePreference: "hybrid",
    });

    const [result] = scoreJobsForUser(rawJobs, userProfile);

    expect(result.matchedSkills).toEqual(["Power BI", "Jira"]);
  });

  it("captures matched skills and overlap bonus when overlap exists", () => {
    const rawJobs = [
      makeJob({
        skills: ["React", "SQL", "AWS"],
      }),
    ];

    const userProfile = makeUser({
      skills: ["React", "AWS"],
    });

    const [result] = scoreJobsForUser(rawJobs, userProfile);

    expect(result.matchedSkills).toEqual(["React", "AWS"]);
    expect(result.scoreBreakdown.skillOverlapBonus).toBeGreaterThan(0);
  });

  it("does not add overlap bonus when no shared skills exist", () => {
    const rawJobs = [
      makeJob({
        skills: ["React", "SQL", "AWS"],
      }),
    ];

    const userProfile = makeUser({
      skills: ["Excel", "Tableau"],
    });

    const [result] = scoreJobsForUser(rawJobs, userProfile);

    expect(result.matchedSkills).toEqual([]);
    expect(result.scoreBreakdown.skillOverlapBonus).toBe(0);
  });

  it("preserves legacy compatibility fields", () => {
    const rawJobs = [makeJob()];
    const userProfile = makeUser();

    const [result] = scoreJobsForUser(rawJobs, userProfile);

    expect(result.matchScore).toBe(result.bloomFitScore);
    expect(result.fitTag).toBe(result.bloomVerdict);
    expect(result.reasons).toEqual(result.bloomReasons);
  });
});