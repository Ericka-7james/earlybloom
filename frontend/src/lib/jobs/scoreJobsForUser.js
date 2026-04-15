/**
 * @fileoverview Public job scoring entry point for EarlyBloom.
 *
 * This module scores raw job listings for an early-career user using the
 * EarlyBloom V1 scoring model. It is intentionally pure and UI-agnostic.
 *
 * Phase 6 additions:
 * - resume-to-job skill overlap matching
 * - small additive overlap bonus
 * - matched skill metadata returned for UI use
 */

import {
  collectWarningFlags,
  scoreAccessibility,
  scorePreferenceFit,
  scoreSeniorityFit,
  scoreSkillsFit,
  scoreTrust,
} from "./scoring/scoring.rules";
import { deriveBloomVerdict } from "./scoring/scoring.verdicts";
import { normalizeJob, normalizeUserProfile } from "./scoring/scoring.normalize";
import { clamp, createFallbackId, dedupeStrings } from "./scoring/scoring.utils";
import {
  calculateMatchedSkillBonus,
  getMatchedSkills,
} from "./getMatchedSkills";

/**
 * Returns scored job objects for a given user.
 *
 * Output includes both Bloom-native fields and legacy aliases so the current UI
 * can migrate off mock scored data with minimal churn.
 *
 * @param {Array<Object>} [rawJobs=[]] Raw job listings.
 * @param {Object} [userProfile={}] User preferences and profile data.
 * @returns {Array<Object>} Scored job objects.
 */
export function scoreJobsForUser(rawJobs = [], userProfile = {}) {
  if (!Array.isArray(rawJobs)) {
    return [];
  }

  return rawJobs.map((job) => scoreSingleJob(job, userProfile));
}

/**
 * Scores a single raw job listing for a single user.
 *
 * This function combines:
 * - seniority fit
 * - skills fit
 * - accessibility
 * - trust
 * - preferences
 * - a small additive resume-to-job skill overlap boost
 *
 * The overlap boost is intentionally capped and secondary to junior-fit logic.
 *
 * @param {Object} rawJob Raw job listing.
 * @param {Object} userProfile User profile.
 * @returns {Object} Scored job object.
 */
function scoreSingleJob(rawJob, userProfile) {
  const normalizedJob = normalizeJob(rawJob);
  const normalizedUser = normalizeUserProfile(userProfile);

  const seniorityResult = scoreSeniorityFit(normalizedJob, normalizedUser);
  const skillsResult = scoreSkillsFit(normalizedJob, normalizedUser);
  const accessibilityResult = scoreAccessibility(normalizedJob, normalizedUser);
  const trustResult = scoreTrust(normalizedJob);
  const preferenceResult = scorePreferenceFit(normalizedJob, normalizedUser);

  const matchedSkills = getMatchedSkills(
    normalizedJob.canonicalSkills,
    normalizedUser.canonicalSkills
  );

  const matchedSkillBonus = calculateMatchedSkillBonus(matchedSkills);

  const bloomFitScore = clamp(
    seniorityResult.score +
      skillsResult.score +
      accessibilityResult.score +
      trustResult.score +
      preferenceResult.score +
      matchedSkillBonus,
    0,
    100
  );

  const warningFlags = collectWarningFlags({
    job: normalizedJob,
    seniorityResult,
    accessibilityResult,
    trustResult,
    preferenceResult,
  });

  const bloomVerdict = deriveBloomVerdict({
    score: bloomFitScore,
    warningFlags,
    seniorityResult,
    accessibilityResult,
  });

  const bloomReasons = dedupeStrings(
    prioritizeReasonsForVerdict(
      {
        seniority: seniorityResult.reasons,
        skills: addMatchedSkillReason(skillsResult.reasons, matchedSkills),
        accessibility: accessibilityResult.reasons,
        trust: trustResult.reasons,
        preference: preferenceResult.reasons,
      },
      bloomVerdict
    )
  ).slice(0, 4);

  return {
    id: rawJob.id ?? rawJob.jobId ?? rawJob.slug ?? createFallbackId(rawJob),
    bloomFitScore,
    bloomVerdict,
    bloomReasons,
    matchedSkills,
    scoreBreakdown: {
      seniorityFit: seniorityResult.score,
      skillsFit: skillsResult.score,
      skillOverlapBonus: matchedSkillBonus,
      accessibility: accessibilityResult.score,
      trust: trustResult.score,
      preferenceFit: preferenceResult.score,
    },
    warningFlags,

    // Legacy aliases for current UI compatibility.
    matchScore: bloomFitScore,
    fitTag: bloomVerdict,
    reasons: bloomReasons,
  };
}

/**
 * Adds an optional matched-skills explanation to the skills reason list.
 *
 * This keeps the existing skills scoring language intact while allowing
 * the UI and reason prioritization flow to surface concrete overlap.
 *
 * @param {string[]} reasons Existing skills-related reasons.
 * @param {string[]} matchedSkills Canonical matched skills.
 * @returns {string[]} Updated reasons list.
 */
function addMatchedSkillReason(reasons, matchedSkills) {
  const safeReasons = Array.isArray(reasons) ? reasons : [];

  if (!Array.isArray(matchedSkills) || matchedSkills.length === 0) {
    return safeReasons;
  }

  const preview = matchedSkills.slice(0, 3).join(", ");
  const suffix =
    matchedSkills.length > 3
      ? `, and ${matchedSkills.length - 3} more`
      : "";

  return [
    ...safeReasons,
    `Matched skills include ${preview}${suffix}.`,
  ];
}

/**
 * Prioritizes reasons based on the final verdict so the explanation feels more honest.
 *
 * @param {{
 *   seniority: string[],
 *   skills: string[],
 *   accessibility: string[],
 *   trust: string[],
 *   preference: string[]
 * }} groupedReasons Grouped reasons by scoring bucket.
 * @param {string} verdict Final verdict.
 * @returns {string[]} Prioritized reasons.
 */
function prioritizeReasonsForVerdict(groupedReasons, verdict) {
  const allReasons = [
    ...groupedReasons.seniority,
    ...groupedReasons.skills,
    ...groupedReasons.accessibility,
    ...groupedReasons.preference,
    ...groupedReasons.trust,
  ];

  const negativeLikeReasons = allReasons.filter((reason) =>
    /stretch|senior|beyond|ownership|leadership|architecture|limited|weak|mismatch|too many|not listed|more senior|exceed/i.test(
      reason
    )
  );

  const positiveLikeReasons = allReasons.filter(
    (reason) => !negativeLikeReasons.includes(reason)
  );

  if (verdict === "Misleading Junior" || verdict === "Too Senior") {
    return [...negativeLikeReasons, ...positiveLikeReasons];
  }

  if (verdict === "Stretch Role") {
    return [
      ...negativeLikeReasons.slice(0, 2),
      ...positiveLikeReasons,
      ...negativeLikeReasons.slice(2),
    ];
  }

  return [...positiveLikeReasons, ...negativeLikeReasons];
}

export default scoreJobsForUser;