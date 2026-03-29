/**
 * @fileoverview Derived scored mock jobs for EarlyBloom.
 *
 * This module replaces hand-authored scored mock data with generated scores from
 * the current raw jobs dataset and user profile. It preserves the legacy export
 * shape expected by the current UI while sourcing scoring from the real
 * scoreJobsForUser utility.
 */

import scoreJobsForUser from "../lib/jobs/scoreJobsForUser";
import { MOCK_RAW_JOBS } from "./jobs.raw";
import { MOCK_USER_PROFILE } from "./jobs.user-profile";

/**
 * Maps a numeric Bloom score to a simple confidence label for the current mock UI.
 *
 * This keeps confidence available while the rest of the app transitions from
 * static mock data to fully derived scoring output.
 *
 * @param {number} bloomFitScore Total Bloom fit score.
 * @returns {"high" | "medium" | "low"} Confidence label.
 */
function deriveConfidenceLabel(bloomFitScore = 0) {
  if (bloomFitScore >= 80) {
    return "high";
  }

  if (bloomFitScore >= 55) {
    return "medium";
  }

  return "low";
}

/**
 * Adapts scored jobs from the scoring utility into the exact mock export shape
 * currently expected by the UI layer.
 *
 * Important:
 * - Keeps existing property names like accessibilityFit and trustFit.
 * - Preserves Bloom-native fields for future migration.
 *
 * @param {Array<Object>} scoredJobs Raw scored jobs from scoreJobsForUser.
 * @returns {Array<Object>} UI-compatible scored jobs.
 */
function mapScoredJobsForMockExport(scoredJobs = []) {
  return scoredJobs.map((job) => ({
    id: job.id,
    bloomFitScore: job.bloomFitScore,
    bloomVerdict: job.bloomVerdict,
    bloomReasons: job.bloomReasons,
    scoreBreakdown: {
      seniorityFit: job.scoreBreakdown?.seniorityFit ?? 0,
      skillsFit: job.scoreBreakdown?.skillsFit ?? 0,
      accessibilityFit: job.scoreBreakdown?.accessibility ?? 0,
      trustFit: job.scoreBreakdown?.trust ?? 0,
      preferenceFit: job.scoreBreakdown?.preferenceFit ?? 0,
    },
    warningFlags: Array.isArray(job.warningFlags) ? job.warningFlags : [],
    confidence: deriveConfidenceLabel(job.bloomFitScore),

    // Optional bridge fields in case parts of the UI still read these directly.
    matchScore: job.matchScore ?? job.bloomFitScore,
    fitTag: job.fitTag ?? job.bloomVerdict,
    reasons: job.reasons ?? job.bloomReasons,
  }));
}

/**
 * Scored mock jobs derived from the current raw mock dataset and mock user profile.
 */
export const MOCK_SCORED_JOBS = mapScoredJobsForMockExport(
  scoreJobsForUser(MOCK_RAW_JOBS, MOCK_USER_PROFILE)
);

export default MOCK_SCORED_JOBS;