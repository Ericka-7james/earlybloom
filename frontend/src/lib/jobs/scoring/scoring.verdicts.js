/**
 * @fileoverview Verdict derivation helpers for EarlyBloom job scoring.
 */

import { BLOOM_VERDICTS } from "./scoring.constants";

/**
 * Derives the final Bloom verdict for a job.
 *
 * This version is intentionally less strict than the original. It should let
 * strong junior-friendly roles become Real Junior even when they are not near-perfect
 * matches on every scoring dimension.
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
    warningFlags.includes("Junior title conflicts with senior requirements") ||
    warningFlags.includes("Title suggests junior but requirements are senior-leaning")
  ) {
    return BLOOM_VERDICTS.MISLEADING_JUNIOR;
  }

  if (
    warningFlags.includes("Title suggests a senior role") ||
    warningFlags.includes("Requires 5+ years of experience")
  ) {
    return BLOOM_VERDICTS.TOO_SENIOR;
  }

  const seniorityScore = seniorityResult?.score ?? 0;
  const accessibilityScore = accessibilityResult?.score ?? 0;

  if (
    (score >= 58 && seniorityScore >= 24 && accessibilityScore >= 8) ||
    (score >= 62 && seniorityScore >= 20 && accessibilityScore >= 10)
  ) {
    return BLOOM_VERDICTS.REAL_JUNIOR;
  }

  return BLOOM_VERDICTS.STRETCH_ROLE;
}