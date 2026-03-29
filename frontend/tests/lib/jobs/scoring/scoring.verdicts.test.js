import { describe, it, expect } from "vitest";
import { deriveBloomVerdict } from "../../../../src/lib/jobs/scoring/scoring.verdicts";

describe("deriveBloomVerdict", () => {
  it("returns Misleading Junior when seniorityResult is misleading", () => {
    const result = deriveBloomVerdict({
      score: 70,
      warningFlags: [],
      seniorityResult: { misleading: true, score: 25 },
      accessibilityResult: { score: 10 },
    });

    expect(result).toBe("Misleading Junior");
  });

  it("returns Misleading Junior when warning flags show junior title conflict", () => {
    const result = deriveBloomVerdict({
      score: 70,
      warningFlags: ["Junior title conflicts with senior requirements"],
      seniorityResult: { misleading: false, score: 25 },
      accessibilityResult: { score: 10 },
    });

    expect(result).toBe("Misleading Junior");
  });

  it("returns Misleading Junior when warning flags show junior title but senior-leaning requirements", () => {
    const result = deriveBloomVerdict({
      score: 70,
      warningFlags: ["Title suggests junior but requirements are senior-leaning"],
      seniorityResult: { misleading: false, score: 25 },
      accessibilityResult: { score: 10 },
    });

    expect(result).toBe("Misleading Junior");
  });

  it("returns Too Senior when warning flags indicate a senior title", () => {
    const result = deriveBloomVerdict({
      score: 70,
      warningFlags: ["Title suggests a senior role"],
      seniorityResult: { misleading: false, score: 25 },
      accessibilityResult: { score: 10 },
    });

    expect(result).toBe("Too Senior");
  });

  it("returns Too Senior when warning flags indicate 5+ years required", () => {
    const result = deriveBloomVerdict({
      score: 70,
      warningFlags: ["Requires 5+ years of experience"],
      seniorityResult: { misleading: false, score: 25 },
      accessibilityResult: { score: 10 },
    });

    expect(result).toBe("Too Senior");
  });

  it("returns Real Junior for the first qualifying threshold", () => {
    const result = deriveBloomVerdict({
      score: 58,
      warningFlags: [],
      seniorityResult: { misleading: false, score: 24 },
      accessibilityResult: { score: 8 },
    });

    expect(result).toBe("Real Junior");
  });

  it("returns Real Junior for the second qualifying threshold", () => {
    const result = deriveBloomVerdict({
      score: 62,
      warningFlags: [],
      seniorityResult: { misleading: false, score: 20 },
      accessibilityResult: { score: 10 },
    });

    expect(result).toBe("Real Junior");
  });

  it("returns Stretch Role when score is good but thresholds are not met", () => {
    const result = deriveBloomVerdict({
      score: 61,
      warningFlags: [],
      seniorityResult: { misleading: false, score: 19 },
      accessibilityResult: { score: 9 },
    });

    expect(result).toBe("Stretch Role");
  });

  it("defaults missing seniority and accessibility scores to 0", () => {
    const result = deriveBloomVerdict({
      score: 80,
      warningFlags: [],
      seniorityResult: {},
      accessibilityResult: {},
    });

    expect(result).toBe("Stretch Role");
  });

  it("prioritizes Misleading Junior over Too Senior when both conditions exist", () => {
    const result = deriveBloomVerdict({
      score: 80,
      warningFlags: [
        "Junior title conflicts with senior requirements",
        "Title suggests a senior role",
      ],
      seniorityResult: { misleading: false, score: 30 },
      accessibilityResult: { score: 12 },
    });

    expect(result).toBe("Misleading Junior");
  });
});