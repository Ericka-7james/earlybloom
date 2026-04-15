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
 *
 * Phase 9 hardening:
 * - safe fallbacks for missing resume/profile skills
 * - safe fallbacks for jobs with no normalized skills
 * - predictable empty arrays for UI consumers
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
  if (!Array.isArray(rawJobs) || rawJobs.length === 0) {
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
function scoreSingleJob(rawJob = {}, userProfile = {}) {
  const normalizedJob = normalizeJob(rawJob);
  const normalizedUser = normalizeUserProfile(userProfile);

  const seniorityResult = scoreSeniorityFit(normalizedJob, normalizedUser);
  const skillsResult = scoreSkillsFit(normalizedJob, normalizedUser);
  const accessibilityResult = scoreAccessibility(normalizedJob, normalizedUser);
  const trustResult = scoreTrust(normalizedJob);
  const preferenceResult = scorePreferenceFit(normalizedJob, normalizedUser);

  const jobSkills = Array.isArray(normalizedJob?.canonicalSkills)
    ? normalizedJob.canonicalSkills
    : [];
  const userSkills = Array.isArray(normalizedUser?.canonicalSkills)
    ? normalizedUser.canonicalSkills
    : [];

  const matchedSkills = getMatchedSkills(jobSkills, userSkills);
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
        seniority: Array.isArray(seniorityResult?.reasons)
          ? seniorityResult.reasons
          : [],
        skills: addMatchedSkillReason(skillsResult?.reasons, matchedSkills),
        accessibility: Array.isArray(accessibilityResult?.reasons)
          ? accessibilityResult.reasons
          : [],
        trust: Array.isArray(trustResult?.reasons) ? trustResult.reasons : [],
        preference: Array.isArray(preferenceResult?.reasons)
          ? preferenceResult.reasons
          : [],
      },
      bloomVerdict
    )
  ).slice(0, 4);

  return {
    id: rawJob.id ?? rawJob.jobId ?? rawJob.slug ?? createFallbackId(rawJob),
    bloomFitScore,
    bloomVerdict,
    bloomReasons,
    matchedSkills: Array.isArray(matchedSkills) ? matchedSkills : [],
    scoreBreakdown: {
      seniorityFit: Number(seniorityResult?.score || 0),
      skillsFit: Number(skillsResult?.score || 0),
      skillOverlapBonus: Number(matchedSkillBonus || 0),
      accessibility: Number(accessibilityResult?.score || 0),
      trust: Number(trustResult?.score || 0),
      preferenceFit: Number(preferenceResult?.score || 0),
    },
    warningFlags: Array.isArray(warningFlags) ? warningFlags : [],

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
 * @param {string[] | undefined} reasons Existing skills-related reasons.
 * @param {string[] | undefined} matchedSkills Canonical matched skills.
 * @returns {string[]} Updated reasons list.
 */
function addMatchedSkillReason(reasons, matchedSkills) {
  const safeReasons = Array.isArray(reasons) ? reasons : [];
  const safeMatchedSkills = Array.isArray(matchedSkills) ? matchedSkills : [];

  if (safeMatchedSkills.length === 0) {
    return safeReasons;
  }

  const preview = safeMatchedSkills.slice(0, 3).join(", ");
  const suffix =
    safeMatchedSkills.length > 3
      ? `, and ${safeMatchedSkills.length - 3} more`
      : "";

  return [...safeReasons, `Matched skills include ${preview}${suffix}.`];
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
    ...(Array.isArray(groupedReasons?.seniority) ? groupedReasons.seniority : []),
    ...(Array.isArray(groupedReasons?.skills) ? groupedReasons.skills : []),
    ...(Array.isArray(groupedReasons?.accessibility)
      ? groupedReasons.accessibility
      : []),
    ...(Array.isArray(groupedReasons?.preference) ? groupedReasons.preference : []),
    ...(Array.isArray(groupedReasons?.trust) ? groupedReasons.trust : []),
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