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
import { deriveBloomVerdict as deriveBloomVerdictInternal } from "./scoring.verdicts";

/**
 * Scores how appropriate a role is for an early-career user.
 *
 * Biggest purpose:
 * - reward true junior roles
 * - penalize title/description mismatch
 * - penalize high years-of-experience asks hiding behind junior labels
 *
 * @param {Object} job Normalized job.
 * @param {Object} user Normalized user.
 * @returns {{score:number, reasons:string[], misleading:boolean}}
 */
export function scoreSeniorityFit(job, user) {
  let score = 0;
  const reasons = [];

  const titleHasJuniorSignal = containsAny(job.titleLower, [
    ...SENIORITY_SIGNALS.juniorPositive,
    ...SENIORITY_SIGNALS.juniorNeutral,
  ]);
  const titleHasSeniorSignal = containsAny(
    job.titleLower,
    SENIORITY_SIGNALS.seniorNegative
  );
  const descriptionHasJuniorSignal = containsAny(
    job.descriptionLower,
    SENIORITY_SIGNALS.juniorPositive
  );
  const descriptionHasSeniorSignal = containsAny(
    job.descriptionLower,
    SENIORITY_SIGNALS.seniorNegative
  );

  if (titleHasJuniorSignal || descriptionHasJuniorSignal) {
    score += 18;
    reasons.push("Signals an early-career or junior-friendly role.");
  }

  if (!titleHasSeniorSignal && job.yearsExperienceRequired <= 2) {
    score += 10;
    reasons.push("Years-of-experience ask looks realistic for entry-level applicants.");
  } else if (job.yearsExperienceRequired <= 4) {
    score += 5;
    reasons.push("Experience requirement may be a stretch, but still possible.");
  }

  const titleMatchesEarlyCareerTrack =
    containsAny(job.titleLower, EARLY_CAREER_TITLE_HINTS) ||
    user.targetTitles.some((targetTitle) => job.titleLower.includes(targetTitle));

  if (titleMatchesEarlyCareerTrack) {
    score += 7;
    reasons.push("Job title lines up with common early-career tracks.");
  }

  let misleading = false;

  if (titleHasSeniorSignal) {
    score -= 18;
    reasons.push("Title signals a more senior role.");
  }

  if (descriptionHasSeniorSignal && job.yearsExperienceRequired >= 5) {
    score -= 12;
    reasons.push("Description leans more senior than the title suggests.");
  }

  if (job.yearsExperienceRequired >= 5) {
    score -= 14;

    if (titleHasJuniorSignal) {
      misleading = true;
      reasons.push("Marked junior, but asks for too many years of experience.");
    } else {
      reasons.push("Experience requirement is likely beyond true entry-level range.");
    }
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
 * This is intentionally forgiving. V1 should reward partial overlap instead of
 * demanding near-perfect matching for junior candidates.
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

  const matchedSkills = user.skills.filter((skill) => {
    return (
      job.skills.has(skill) ||
      job.descriptionLower.includes(skill) ||
      job.titleLower.includes(skill)
    );
  });

  const ratio = matchedSkills.length / user.skills.length;
  const score = Math.round(ratio * WEIGHTS.skills);

  if (matchedSkills.length >= 4) {
    reasons.push("Strong skill overlap with the posting.");
  } else if (matchedSkills.length >= 2) {
    reasons.push("Some of your current skills align with this role.");
  } else if (matchedSkills.length >= 1) {
    reasons.push("At least one of your current skills matches the posting.");
  } else {
    reasons.push("Low direct skill overlap with the posting.");
  }

  return {
    score: clamp(score, 0, WEIGHTS.skills),
    reasons,
  };
}

/**
 * Scores how accessible the role feels for a junior candidate.
 *
 * Accessibility tries to answer:
 * "Could a real early-career applicant reasonably have a shot here?"
 *
 * @param {Object} job Normalized job.
 * @param {Object} user Normalized user.
 * @returns {{score:number, reasons:string[]}}
 */
export function scoreAccessibility(job, user) {
  let score = 0;
  const reasons = [];

  if (job.yearsExperienceRequired <= Math.max(1, user.experienceYears + 1)) {
    score += 10;
    reasons.push("Experience ask is within a reachable range.");
  } else if (job.yearsExperienceRequired <= user.experienceYears + 3) {
    score += 5;
    reasons.push("Experience ask is slightly above your background.");
  }

  if (containsAny(job.descriptionLower, SIGNALS.accessibilityPositive)) {
    score += 6;
    reasons.push("Posting includes onboarding, mentorship, or training signals.");
  }

  if (job.isRemote || job.isHybrid) {
    score += 2;
    reasons.push("Remote or hybrid setup may widen access.");
  }

  if (containsAny(job.descriptionLower, SIGNALS.accessibilityNegative)) {
    score -= 4;
    reasons.push("Posting uses language that may screen out junior applicants.");
  }

  if (job.yearsExperienceRequired >= 5) {
    score -= 8;
  }

  return {
    score: clamp(score, 0, WEIGHTS.accessibility),
    reasons,
  };
}

/**
 * Scores posting trustworthiness.
 *
 * Trust does not try to prove fraud. It simply detects quality and clarity
 * signals versus vague or hype-heavy wording.
 *
 * @param {Object} job Normalized job.
 * @returns {{score:number, reasons:string[]}}
 */
export function scoreTrust(job) {
  let score = 5;
  const reasons = [];

  if (job.compensation) {
    score += 2;
    reasons.push("Compensation details are present.");
  }

  if (containsAny(job.descriptionLower, SIGNALS.trustPositive)) {
    score += 2;
    reasons.push("Posting includes concrete job details or benefits language.");
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
    reasons,
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
    reasons,
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

  if (job.yearsExperienceRequired >= 5) {
    flags.push("Requires 5+ years of experience");
  }

  if (containsAny(job.titleLower, SENIORITY_SIGNALS.seniorNegative)) {
    flags.push("Title suggests a senior role");
  }

  if (!job.compensation) {
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

  return dedupeStrings(flags);
}

/**
 * Re-export verdict derivation for convenience.
 *
 * @param {Object} params Verdict parameters.
 * @returns {string} Bloom verdict label.
 */
export function deriveBloomVerdict(params) {
  return deriveBloomVerdictInternal(params);
}