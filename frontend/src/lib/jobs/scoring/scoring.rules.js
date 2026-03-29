/**
 * @fileoverview Core scoring rules for EarlyBloom V1.
 */

import {
  EARLY_CAREER_TITLE_HINTS,
  SENIORITY_SIGNALS,
  SIGNALS,
  WEIGHTS,
} from "./scoring.constants";
import { containsAny, clamp, dedupeStrings } from "./scoring.utils";

/**
 * Senior signals that are safe to match directly as substrings.
 *
 * We intentionally exclude raw roman numerals like "ii", "iii", and "iv" from
 * generic substring checks because they can create noisy false positives.
 */
const SAFE_SENIOR_NEGATIVE_SIGNALS = SENIORITY_SIGNALS.seniorNegative.filter(
  (signal) => !["ii", "iii", "iv"].includes(signal)
);

/**
 * Description phrases that often signal a role is operating above a true junior scope.
 */
const SENIOR_SCOPE_DESCRIPTION_SIGNALS = [
  "lead architecture decisions",
  "define architecture",
  "own architecture",
  "architecture decisions",
  "architectural decisions",
  "drive large scale",
  "drive large-scale",
  "independently drive",
  "independently lead",
  "mentor junior engineers",
  "mentor engineers",
  "lead initiatives",
  "own technical direction",
  "set technical direction",
  "cross functional engineering teams",
  "cross-functional engineering teams",
  "large scale platform initiatives",
  "large-scale platform initiatives",
  "ownership of strategy",
  "track record leading",
  "player coach",
];

/**
 * Returns whether the title clearly signals a more senior role.
 *
 * @param {string} titleLower Normalized title text.
 * @returns {boolean} Whether the title looks senior.
 */
function hasSeniorTitleSignal(titleLower = "") {
  if (containsAny(titleLower, SAFE_SENIOR_NEGATIVE_SIGNALS)) {
    return true;
  }

  if (
    /\b(engineer|developer|analyst|designer|specialist|manager|architect)\s+(ii|iii|iv)\b/.test(
      titleLower
    )
  ) {
    return true;
  }

  if (/\blevel\s+[2-9]\b/.test(titleLower)) {
    return true;
  }

  return false;
}

/**
 * Scores how appropriate a role is for an early-career user.
 *
 * @param {Object} job Normalized job.
 * @param {Object} user Normalized user.
 * @returns {{score:number, reasons:string[], misleading:boolean}}
 */
export function scoreSeniorityFit(job, user) {
  let score = 0;
  const reasons = [];

  const titleHasJuniorSignal =
    job.signals.titleSuggestsJunior ||
    containsAny(job.titleLower, [
      ...SENIORITY_SIGNALS.juniorPositive,
      ...SENIORITY_SIGNALS.juniorNeutral,
    ]);

  const descriptionHasJuniorSignal =
    job.signals.descriptionSuggestsJunior ||
    containsAny(job.descriptionLower, SENIORITY_SIGNALS.juniorPositive);

  const titleHasSeniorSignal = hasSeniorTitleSignal(job.titleLower);

  const descriptionHasSeniorSignal =
    containsAny(job.descriptionLower, SAFE_SENIOR_NEGATIVE_SIGNALS) ||
    job.signals.mentionsLeadership ||
    job.signals.mentionsArchitecture ||
    containsAny(job.descriptionLower, SENIOR_SCOPE_DESCRIPTION_SIGNALS);

  const titleMatchesEarlyCareerTrack =
    containsAny(job.titleLower, EARLY_CAREER_TITLE_HINTS) ||
    user.targetTitles.some((targetTitle) => job.titleLower.includes(targetTitle));

  if (titleHasJuniorSignal || descriptionHasJuniorSignal) {
    score += 18;
    reasons.push("Role is explicitly framed as early-career friendly.");
  }

  if (!titleHasSeniorSignal && job.maxYearsRequired <= 2) {
    score += 10;
    reasons.push("Experience range is realistic for junior applicants.");
  } else if (job.maxYearsRequired <= 3) {
    score += 6;
    reasons.push("Experience requirement is slightly above entry level, but still plausible.");
  } else if (job.maxYearsRequired <= 4) {
    score += 2;
    reasons.push("Experience requirement leans above true entry level.");
  }

  if (titleMatchesEarlyCareerTrack) {
    score += 7;
    reasons.push("Job title is in a common early-career lane.");
  }

  let misleading = false;

  if (titleHasSeniorSignal) {
    score -= 18;
    reasons.push("Title suggests a more senior role.");
  }

  if (descriptionHasSeniorSignal && job.maxYearsRequired >= 4) {
    score -= 12;
    reasons.push("Description responsibilities lean more senior than junior.");
  }

  if (
    job.signals.titleDescriptionMismatch ||
    (titleHasJuniorSignal &&
      (job.maxYearsRequired >= 4 ||
        job.signals.mentionsLeadership ||
        job.signals.mentionsArchitecture ||
        job.signals.mentionsOwnership))
  ) {
    misleading = true;
    score -= 14;
    reasons.push("Title says junior, but the actual expectations are more senior.");
  } else if (job.maxYearsRequired >= 5) {
    score -= 14;
    reasons.push("Experience requirement is likely beyond true entry-level range.");
  }

  return {
    score: clamp(score, 0, WEIGHTS.seniority),
    reasons: dedupeStrings(reasons),
    misleading,
  };
}

/**
 * Scores overlap between user skills and job signals.
 *
 * @param {Object} job Normalized job.
 * @param {Object} user Normalized user.
 * @returns {{score:number, reasons:string[]}}
 */
export function scoreSkillsFit(job, user) {
  const reasons = [];

  if (!user.skills.length) {
    return {
      score: 12,
      reasons: ["No user skills provided, so skills scoring stays neutral."],
    };
  }

  const matchedRequiredSkills = user.skills.filter((skill) =>
    job.requiredSkills.includes(skill)
  );

  const matchedPreferredSkills = user.skills.filter((skill) =>
    job.preferredSkills.includes(skill)
  );

  const matchedGeneralSkills = user.skills.filter(
    (skill) =>
      job.skills.has(skill) ||
      job.descriptionLower.includes(skill) ||
      job.titleLower.includes(skill)
  );

  const requiredScore = matchedRequiredSkills.length * 4;
  const preferredScore = matchedPreferredSkills.length * 2;
  const generalScore = Math.min(matchedGeneralSkills.length * 2, 8);

  const score = Math.min(
    WEIGHTS.skills,
    requiredScore + preferredScore + generalScore
  );

  if (matchedRequiredSkills.length >= 3) {
    reasons.push("Strong overlap with core required skills.");
  } else if (matchedRequiredSkills.length >= 1) {
    reasons.push("Some required skills overlap with your current profile.");
  } else if (
    matchedPreferredSkills.length >= 1 ||
    matchedGeneralSkills.length >= 2
  ) {
    reasons.push("There is some relevant skill overlap, but not across core requirements.");
  } else {
    reasons.push("Skill overlap looks limited based on the listed requirements.");
  }

  return {
    score: clamp(score, 0, WEIGHTS.skills),
    reasons: dedupeStrings(reasons),
  };
}

/**
 * Scores how accessible the role feels for a junior candidate.
 *
 * @param {Object} job Normalized job.
 * @param {Object} user Normalized user.
 * @returns {{score:number, reasons:string[]}}
 */
export function scoreAccessibility(job, user) {
  let score = 0;
  const reasons = [];

  if (job.maxYearsRequired <= Math.max(1, user.experienceYears + 1)) {
    score += 10;
    reasons.push("Experience ask is within a reachable range.");
  } else if (job.maxYearsRequired <= user.experienceYears + 2) {
    score += 6;
    reasons.push("Experience ask is slightly above your background.");
  } else if (job.maxYearsRequired <= user.experienceYears + 3) {
    score += 3;
    reasons.push("This role may be reachable, but it is clearly a stretch.");
  }

  if (
    job.signals.mentionsMentorship ||
    containsAny(job.descriptionLower, SIGNALS.accessibilityPositive)
  ) {
    score += 6;
    reasons.push("Posting suggests mentorship, guidance, or onboarding support.");
  }

  if (job.isRemote || job.isHybrid) {
    score += 2;
    reasons.push("Remote or hybrid setup may widen access.");
  }

  if (
    job.signals.mentionsOwnership ||
    job.signals.mentionsLeadership ||
    job.signals.mentionsArchitecture ||
    containsAny(job.descriptionLower, SIGNALS.accessibilityNegative)
  ) {
    score -= 4;
    reasons.push("Role expectations may exceed a typical junior scope.");
  }

  if (job.maxYearsRequired >= 5) {
    score -= 8;
  }

  return {
    score: clamp(score, 0, WEIGHTS.accessibility),
    reasons: dedupeStrings(reasons),
  };
}

/**
 * Scores posting trustworthiness.
 *
 * @param {Object} job Normalized job.
 * @returns {{score:number, reasons:string[]}}
 */
export function scoreTrust(job) {
  let score = 5;
  const reasons = [];

  if (job.compensation?.salaryVisible) {
    score += 2;
    reasons.push("Compensation details are present.");
  }

  if (
    job.signals.hasClearRequirements ||
    containsAny(job.descriptionLower, SIGNALS.trustPositive)
  ) {
    score += 2;
    reasons.push("Posting includes concrete job details and clearer requirements.");
  }

  if (job.signals.hasSeparatePreferredSkills) {
    score += 1;
    reasons.push("Listing separates required versus preferred skills.");
  }

  if (containsAny(job.descriptionLower, SIGNALS.trustNegative)) {
    score -= 3;
    reasons.push("Posting contains vague or hype-heavy language.");
  }

  if (!job.descriptionLower || job.descriptionLower.length < 120) {
    score -= 2;
    reasons.push("Description may be too thin to trust fully.");
  }

  return {
    score: clamp(score, 0, WEIGHTS.trust),
    reasons: dedupeStrings(reasons),
  };
}

/**
 * Scores how well the role matches stated user preferences.
 *
 * @param {Object} job Normalized job.
 * @param {Object} user Normalized user.
 * @returns {{score:number, reasons:string[]}}
 */
export function scorePreferenceFit(job, user) {
  let score = 3;
  const reasons = [];

  if (user.remotePreference === "remote" && job.isRemote) {
    score += 4;
    reasons.push("Matches your remote work preference.");
  } else if (user.remotePreference === "hybrid" && job.isHybrid) {
    score += 4;
    reasons.push("Matches your hybrid work preference.");
  } else if (user.remotePreference === "onsite" && job.isOnsite) {
    score += 4;
    reasons.push("Matches your onsite work preference.");
  } else if (user.remotePreference === "flexible") {
    score += 2;
  }

  if (
    user.preferredLocations.length &&
    user.preferredLocations.some((loc) => job.locationLower.includes(loc))
  ) {
    score += 3;
    reasons.push("Location aligns with your preferences.");
  }

  if (
    user.targetTitles.length &&
    user.targetTitles.some((title) => job.titleLower.includes(title))
  ) {
    score += 2;
    reasons.push("Title is close to the kind of role you are targeting.");
  }

  return {
    score: clamp(score, 0, WEIGHTS.preference),
    reasons: dedupeStrings(reasons),
  };
}

/**
 * Collects transparent warning flags for the UI.
 *
 * @param {Object} params Scoring context.
 * @param {Object} params.job Normalized job.
 * @param {Object} params.seniorityResult Seniority result.
 * @param {Object} params.accessibilityResult Accessibility result.
 * @param {Object} params.trustResult Trust result.
 * @param {Object} params.preferenceResult Preference result.
 * @returns {string[]} Warning flags.
 */
export function collectWarningFlags({
  job,
  seniorityResult,
  accessibilityResult,
  trustResult,
  preferenceResult,
}) {
  const flags = [];

  if (seniorityResult.misleading) {
    flags.push("Junior title conflicts with senior requirements");
  }

  if (job.maxYearsRequired >= 5) {
    flags.push("Requires 5+ years of experience");
  }

  if (hasSeniorTitleSignal(job.titleLower)) {
    flags.push("Title suggests a senior role");
  }

  if (
    job.signals.mentionsOwnership ||
    job.signals.mentionsLeadership ||
    job.signals.mentionsArchitecture
  ) {
    flags.push("Leadership or architecture ownership expected");
  }

  if (!job.compensation?.salaryVisible) {
    flags.push("Compensation not listed");
  }

  if (containsAny(job.descriptionLower, SIGNALS.trustNegative)) {
    flags.push("Vague or hype-heavy language");
  }

  if (
    trustResult.score <= 3 &&
    accessibilityResult.score <= 8 &&
    preferenceResult.score <= 4
  ) {
    flags.push("Low-confidence fit");
  }

  return dedupeStrings([...job.warnings, ...flags]);
}