/**
 * @fileoverview Tests for resume-to-job skill overlap helpers.
 */

import { describe, expect, it } from "vitest";
import {
  calculateMatchedSkillBonus,
  getMatchedSkills,
} from "../../../src/lib/jobs/getMatchedSkills";

describe("getMatchedSkills", () => {
  it("returns overlapping skills preserving job skill order", () => {
    const jobSkills = ["React", "JavaScript", "AWS", "SQL"];
    const userSkills = ["SQL", "React", "Docker"];

    expect(getMatchedSkills(jobSkills, userSkills)).toEqual([
      "React",
      "SQL",
    ]);
  });

  it("returns an empty array when there is no overlap", () => {
    expect(
      getMatchedSkills(["React", "AWS"], ["Excel", "Tableau"])
    ).toEqual([]);
  });

  it("returns an empty array when either side is empty", () => {
    expect(getMatchedSkills([], ["React"])).toEqual([]);
    expect(getMatchedSkills(["React"], [])).toEqual([]);
    expect(getMatchedSkills()).toEqual([]);
  });

  it("preserves canonical casing from job skills", () => {
    const jobSkills = ["JavaScript", "PostgreSQL", "Power BI"];
    const userSkills = ["JavaScript", "Power BI"];

    expect(getMatchedSkills(jobSkills, userSkills)).toEqual([
      "JavaScript",
      "Power BI",
    ]);
  });

  it("ignores duplicate user skills", () => {
    const jobSkills = ["React", "SQL", "AWS"];
    const userSkills = ["React", "React", "SQL"];

    expect(getMatchedSkills(jobSkills, userSkills)).toEqual([
      "React",
      "SQL",
    ]);
  });

  it("ignores non-array inputs safely", () => {
    expect(getMatchedSkills(null, ["React"])).toEqual([]);
    expect(getMatchedSkills(["React"], null)).toEqual([]);
    expect(getMatchedSkills("React", ["React"])).toEqual([]);
  });
});

describe("calculateMatchedSkillBonus", () => {
  it("returns zero when there are no matched skills", () => {
    expect(calculateMatchedSkillBonus([])).toBe(0);
    expect(calculateMatchedSkillBonus()).toBe(0);
  });

  it("applies weighted bonuses by overlap count", () => {
    expect(calculateMatchedSkillBonus(["React"])).toBe(2);
    expect(calculateMatchedSkillBonus(["React", "AWS"])).toBe(3.5);
    expect(calculateMatchedSkillBonus(["React", "AWS", "SQL"])).toBe(4.5);
    expect(
      calculateMatchedSkillBonus(["React", "AWS", "SQL", "Docker", "Python"])
    ).toBe(6.5);
  });

  it("caps the total bonus at the configured maximum", () => {
    const manyMatches = [
      "React",
      "JavaScript",
      "AWS",
      "SQL",
      "Docker",
      "Python",
      "Git",
      "Linux",
      "FastAPI",
      "Tableau",
      "Power BI",
      "ServiceNow",
    ];

    expect(calculateMatchedSkillBonus(manyMatches)).toBe(8);
  });

  it("supports a custom maximum bonus", () => {
    const matches = ["React", "JavaScript", "AWS", "SQL", "Docker"];

    expect(calculateMatchedSkillBonus(matches, 5)).toBe(5);
  });
});