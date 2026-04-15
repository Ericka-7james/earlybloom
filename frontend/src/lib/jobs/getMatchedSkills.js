/**
 * @fileoverview Skill-overlap helpers for EarlyBloom job scoring.
 *
 * This module provides small, deterministic utilities for comparing
 * resume-derived user skills against normalized job skills.
 *
 * Design goals:
 * - preserve canonical skill casing from the job payload
 * - remain resilient to empty or malformed inputs
 * - keep matching logic deterministic and easy to test
 */

/**
 * Returns the overlapping skills between a job and a user profile.
 *
 * Matching preserves the order and canonical casing from `jobSkills`.
 * This is important because backend-normalized job skills are the preferred
 * display source for UI chips such as "Matched skills: React, SQL, AWS".
 *
 * Example:
 * getMatchedSkills(
 *   ["React", "JavaScript", "AWS", "SQL"],
 *   ["SQL", "React", "Docker"]
 * )
 * => ["React", "SQL"]
 *
 * @param {string[]} [jobSkills=[]] Canonical normalized job skills.
 * @param {string[]} [userSkills=[]] Canonical normalized user skills.
 * @returns {string[]} Ordered list of shared skills.
 */
export function getMatchedSkills(jobSkills = [], userSkills = []) {
  if (!Array.isArray(jobSkills) || !Array.isArray(userSkills)) {
    return [];
  }

  const userSet = new Set(
    userSkills
      .filter((skill) => typeof skill === "string")
      .map((skill) => skill.trim())
      .filter(Boolean)
  );

  if (userSet.size === 0) {
    return [];
  }

  return jobSkills.filter(
    (skill) => typeof skill === "string" && userSet.has(skill.trim())
  );
}

/**
 * Calculates a small additive score bonus from shared skills.
 *
 * Weighting:
 * - first shared skill: +2
 * - second shared skill: +1.5
 * - third through fifth shared skills: +1 each
 * - sixth and beyond: +0.5 each
 *
 * The bonus is capped so it helps but does not overpower the broader
 * early-career fit model.
 *
 * @param {string[]} [matchedSkills=[]] Ordered matched skills.
 * @param {number} [maxBonus=8] Maximum allowed overlap bonus.
 * @returns {number} Rounded additive overlap bonus.
 */
export function calculateMatchedSkillBonus(
  matchedSkills = [],
  maxBonus = 8
) {
  if (!Array.isArray(matchedSkills) || matchedSkills.length === 0) {
    return 0;
  }

  let bonus = 0;

  matchedSkills.forEach((_, index) => {
    if (index === 0) {
      bonus += 2;
      return;
    }

    if (index === 1) {
      bonus += 1.5;
      return;
    }

    if (index <= 4) {
      bonus += 1;
      return;
    }

    bonus += 0.5;
  });

  return Math.min(maxBonus, bonus);
}

export default getMatchedSkills;