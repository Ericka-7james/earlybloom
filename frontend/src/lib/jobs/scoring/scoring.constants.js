/**
 * @fileoverview Shared constants for EarlyBloom job scoring.
 */

/**
 * Bloom verdict labels used by the UI.
 * @enum {string}
 */
export const BLOOM_VERDICTS = {
  REAL_JUNIOR: "Real Junior",
  STRETCH_ROLE: "Stretch Role",
  TOO_SENIOR: "Too Senior",
  MISLEADING_JUNIOR: "Misleading Junior",
};

/**
 * Weight constants for the EarlyBloom V1 scoring model.
 */
export const WEIGHTS = {
  seniority: 35,
  skills: 25,
  accessibility: 20,
  trust: 10,
  preference: 10,
};

/**
 * Seniority keywords.
 */
export const SENIORITY_SIGNALS = {
  juniorPositive: [
    "entry level",
    "entry-level",
    "junior",
    "jr",
    "new grad",
    "new graduate",
    "graduate",
    "early career",
    "associate",
    "apprentice",
    "trainee",
    "intern to hire",
    "career starter",
  ],
  juniorNeutral: [
    "software engineer i",
    "engineer i",
    "analyst i",
    "developer i",
    "level 1",
    "l1",
  ],
  seniorNegative: [
    "senior",
    "staff",
    "principal",
    "lead",
    "manager",
    "director",
    "architect",
    "specialist iv",
    "engineer iii",
    "engineer iv",
    "sr.",
    "sde ii",
    "sde iii",
    "ii",
    "iii",
    "iv",
  ],
};

/**
 * Accessibility and trust signals.
 */
export const SIGNALS = {
  accessibilityPositive: [
    "training provided",
    "will train",
    "mentorship",
    "mentor",
    "supportive team",
    "entry level welcome",
    "recent graduates",
    "new grads",
    "career development",
    "onboarding",
  ],
  accessibilityNegative: [
    "must have",
    "required years",
    "5+ years",
    "6+ years",
    "7+ years",
    "8+ years",
    "10+ years",
    "expert",
    "deep expertise",
    "extensive experience",
    "track record leading",
    "ownership of strategy",
    "player coach",
  ],
  trustNegative: [
    "rockstar",
    "ninja",
    "guru",
    "wear many hats",
    "fast-paced environment",
    "self-starter",
    "hit the ground running",
    "unpaid",
    "commission only",
    "1099",
    "contract to hire",
    "competitive salary",
    "salary commensurate",
  ],
  trustPositive: [
    "salary",
    "compensation",
    "benefits",
    "health insurance",
    "pto",
    "paid time off",
    "clear responsibilities",
    "equal opportunity",
  ],
};

/**
 * Common early-career-friendly title tokens.
 */
export const EARLY_CAREER_TITLE_HINTS = [
  "software engineer",
  "frontend engineer",
  "frontend developer",
  "backend engineer",
  "full stack engineer",
  "fullstack engineer",
  "web developer",
  "qa engineer",
  "quality assurance",
  "support engineer",
  "implementation specialist",
  "technical support",
  "analyst",
  "associate engineer",
  "developer",
];

/**
 * Known skills for simple V1 mock-based matching.
 *
 * This can later move to a richer taxonomy or config-driven skills registry.
 */
export const KNOWN_SKILLS = [
  "javascript",
  "typescript",
  "react",
  "node",
  "node.js",
  "html",
  "css",
  "python",
  "java",
  "sql",
  "aws",
  "git",
  "rest",
  "fastapi",
  "docker",
  "kubernetes",
  "figma",
  "excel",
  "tableau",
  "power bi",
  "qa",
  "testing",
  "automation",
  "api",
  "apis",
];