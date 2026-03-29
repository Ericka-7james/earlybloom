/**
 * @fileoverview Verdict derivation helpers for EarlyBloom job scoring.
 */

import { BLOOM_VERDICTS } from "./scoring.constants";

/**
 * Derives the final Bloom verdict for a job.
 *
 * @param {Object} params Verdict inputs.
 * @param {number} params.score Total Bloom fit score.
 * @param {string[]} params.warningFlags Warning flags generated during scoring.
 * @param {Object} params.seniorityResult Seniority scoring result.
 * @param {Object} params.accessibilityResult Accessibility scoring result.
 * @returns {string} Bloom verdict label.
 */
export function deriveBloomVerdict({
  score,
  warningFlags,
  seniorityResult,
  accessibilityResult,
}) {
  if (
    seniorityResult.misleading ||
    warningFlags.includes("Junior title conflicts with senior requirements")
  ) {
    return BLOOM_VERDICTS.MISLEADING_JUNIOR;
  }

  if (
    warningFlags.includes("Title suggests a senior role") ||
    warningFlags.includes("Requires 5+ years of experience")
  ) {
    return BLOOM_VERDICTS.TOO_SENIOR;
  }

  if (score >= 70 && accessibilityResult.score >= 12) {
    return BLOOM_VERDICTS.REAL_JUNIOR;
  }

  return BLOOM_VERDICTS.STRETCH_ROLE;
}