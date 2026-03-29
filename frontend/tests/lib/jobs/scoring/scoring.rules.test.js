import {
  collectWarningFlags,
  scoreAccessibility,
  scorePreferenceFit,
  scoreSeniorityFit,
  scoreSkillsFit,
  scoreTrust,
} from "../../../../src/lib/jobs/scoring/scoring.rules";

describe("scoring.rules", () => {
  describe("scoreSeniorityFit", () => {
    it("rewards clearly junior-friendly roles", () => {
      const job = {
        titleLower: "junior frontend engineer",
        descriptionLower: "entry level role with mentorship and onboarding support",
        maxYearsRequired: 2,
        signals: {
          titleSuggestsJunior: true,
          descriptionSuggestsJunior: true,
          mentionsLeadership: false,
          mentionsArchitecture: false,
          mentionsOwnership: false,
          titleDescriptionMismatch: false,
        },
      };

      const user = {
        targetTitles: ["frontend engineer"],
      };

      const result = scoreSeniorityFit(job, user);

      expect(result.score).toBeGreaterThan(0);
      expect(result.misleading).toBe(false);
      expect(result.reasons).toContain(
        "Role is explicitly framed as early-career friendly."
      );
      expect(result.reasons).toContain(
        "Experience range is realistic for junior applicants."
      );
    });

    it("flags misleading junior titles with senior expectations", () => {
      const job = {
        titleLower: "junior software engineer",
        descriptionLower:
          "own architecture and mentor engineers across teams",
        maxYearsRequired: 5,
        signals: {
          titleSuggestsJunior: true,
          descriptionSuggestsJunior: false,
          mentionsLeadership: true,
          mentionsArchitecture: true,
          mentionsOwnership: true,
          titleDescriptionMismatch: true,
        },
      };

      const user = {
        targetTitles: ["software engineer"],
      };

      const result = scoreSeniorityFit(job, user);

      expect(result.misleading).toBe(true);
      expect(result.reasons).toContain(
        "Title says junior, but the actual expectations are more senior."
      );
    });

    it("detects senior title signals like engineer ii", () => {
      const job = {
        titleLower: "software engineer ii",
        descriptionLower: "build product features",
        maxYearsRequired: 2,
        signals: {
          titleSuggestsJunior: false,
          descriptionSuggestsJunior: false,
          mentionsLeadership: false,
          mentionsArchitecture: false,
          mentionsOwnership: false,
          titleDescriptionMismatch: false,
        },
      };

      const user = {
        targetTitles: [],
      };

      const result = scoreSeniorityFit(job, user);

      expect(result.reasons).toContain("Title suggests a more senior role.");
    });
  });

  describe("scoreSkillsFit", () => {
    it("stays neutral when user skills are missing", () => {
      const job = {
        requiredSkills: ["react", "javascript"],
        preferredSkills: ["css"],
        skills: new Set(["react", "javascript", "css"]),
        descriptionLower: "react javascript css",
        titleLower: "frontend engineer",
      };

      const user = {
        skills: [],
      };

      const result = scoreSkillsFit(job, user);

      expect(result.score).toBe(12);
      expect(result.reasons).toEqual([
        "No user skills provided, so skills scoring stays neutral.",
      ]);
    });

    it("rewards strong overlap with required skills", () => {
      const job = {
        requiredSkills: ["react", "javascript", "css"],
        preferredSkills: ["typescript"],
        skills: new Set(["react", "javascript", "css", "typescript"]),
        descriptionLower: "react javascript css typescript",
        titleLower: "frontend engineer",
      };

      const user = {
        skills: ["react", "javascript", "css", "typescript"],
      };

      const result = scoreSkillsFit(job, user);

      expect(result.score).toBeGreaterThan(0);
      expect(result.reasons).toContain(
        "Strong overlap with core required skills."
      );
    });

    it("recognizes limited overlap when only general skills match", () => {
      const job = {
        requiredSkills: ["go", "kubernetes"],
        preferredSkills: ["aws"],
        skills: new Set(["react", "css"]),
        descriptionLower: "react and css helpful",
        titleLower: "frontend engineer",
      };

      const user = {
        skills: ["react", "css"],
      };

      const result = scoreSkillsFit(job, user);

      expect(result.reasons).toContain(
        "There is some relevant skill overlap, but not across core requirements."
      );
    });
  });

  describe("scoreAccessibility", () => {
    it("rewards reachable roles with mentorship and remote access", () => {
      const job = {
        maxYearsRequired: 2,
        descriptionLower: "mentorship onboarding support",
        isRemote: true,
        isHybrid: false,
        signals: {
          mentionsMentorship: true,
          mentionsOwnership: false,
          mentionsLeadership: false,
          mentionsArchitecture: false,
        },
      };

      const user = {
        experienceYears: 1,
      };

      const result = scoreAccessibility(job, user);

      expect(result.score).toBeGreaterThan(0);
      expect(result.reasons).toContain(
        "Experience ask is within a reachable range."
      );
      expect(result.reasons).toContain(
        "Posting suggests mentorship, guidance, or onboarding support."
      );
      expect(result.reasons).toContain(
        "Remote or hybrid setup may widen access."
      );
    });

    it("penalizes roles with senior scope and high experience asks", () => {
      const job = {
        maxYearsRequired: 5,
        descriptionLower: "ownership leadership architecture",
        isRemote: false,
        isHybrid: false,
        signals: {
          mentionsMentorship: false,
          mentionsOwnership: true,
          mentionsLeadership: true,
          mentionsArchitecture: true,
        },
      };

      const user = {
        experienceYears: 1,
      };

      const result = scoreAccessibility(job, user);

      expect(result.reasons).toContain(
        "Role expectations may exceed a typical junior scope."
      );
      expect(result.score).toBeGreaterThanOrEqual(0);
    });
  });

  describe("scoreTrust", () => {
    it("rewards transparent postings with compensation and clear details", () => {
      const job = {
        compensation: {
          salaryVisible: true,
        },
        descriptionLower:
          "this role includes requirements responsibilities qualifications and preferred skills in clear detail for candidates to review carefully",
        signals: {
          hasClearRequirements: true,
          hasSeparatePreferredSkills: true,
        },
      };

      const result = scoreTrust(job);

      expect(result.reasons).toContain("Compensation details are present.");
      expect(result.reasons).toContain(
        "Posting includes concrete job details and clearer requirements."
      );
      expect(result.reasons).toContain(
        "Listing separates required versus preferred skills."
      );
    });

    it("penalizes vague and overly thin postings", () => {
      const job = {
        compensation: {
          salaryVisible: false,
        },
        descriptionLower: "rockstar ninja fast paced",
        signals: {
          hasClearRequirements: false,
          hasSeparatePreferredSkills: false,
        },
      };

      const result = scoreTrust(job);

      expect(result.reasons).toContain(
        "Posting contains vague or hype-heavy language."
      );
      expect(result.reasons).toContain(
        "Description may be too thin to trust fully."
      );
    });
  });

  describe("scorePreferenceFit", () => {
    it("rewards matching remote preference, location, and target title", () => {
      const job = {
        isRemote: true,
        isHybrid: false,
        isOnsite: false,
        locationLower: "atlanta, ga",
        titleLower: "frontend engineer",
      };

      const user = {
        remotePreference: "remote",
        preferredLocations: ["atlanta"],
        targetTitles: ["frontend engineer"],
      };

      const result = scorePreferenceFit(job, user);

      expect(result.reasons).toContain("Matches your remote work preference.");
      expect(result.reasons).toContain("Location aligns with your preferences.");
      expect(result.reasons).toContain(
        "Title is close to the kind of role you are targeting."
      );
    });

    it("gives a smaller bump for flexible remote preference", () => {
      const job = {
        isRemote: false,
        isHybrid: false,
        isOnsite: true,
        locationLower: "new york, ny",
        titleLower: "software engineer",
      };

      const user = {
        remotePreference: "flexible",
        preferredLocations: [],
        targetTitles: [],
      };

      const result = scorePreferenceFit(job, user);

      expect(result.score).toBeGreaterThanOrEqual(3);
    });
  });

  describe("collectWarningFlags", () => {
    it("collects transparent warning flags and dedupes them", () => {
      const result = collectWarningFlags({
        job: {
          titleLower: "senior frontend engineer",
          maxYearsRequired: 5,
          descriptionLower: "rockstar ninja architecture ownership",
          warnings: ["Compensation not listed"],
          compensation: {
            salaryVisible: false,
          },
          signals: {
            mentionsOwnership: true,
            mentionsLeadership: false,
            mentionsArchitecture: true,
          },
        },
        seniorityResult: {
          misleading: true,
        },
        accessibilityResult: {
          score: 8,
        },
        trustResult: {
          score: 3,
        },
        preferenceResult: {
          score: 4,
        },
      });

      expect(result).toContain("Junior title conflicts with senior requirements");
      expect(result).toContain("Requires 5+ years of experience");
      expect(result).toContain("Title suggests a senior role");
      expect(result).toContain("Leadership or architecture ownership expected");
      expect(result).toContain("Compensation not listed");
      expect(result).toContain("Vague or hype-heavy language");
      expect(result).toContain("Low-confidence fit");

      const compensationFlags = result.filter(
        (flag) => flag === "Compensation not listed"
      );
      expect(compensationFlags).toHaveLength(1);
    });
  });
});