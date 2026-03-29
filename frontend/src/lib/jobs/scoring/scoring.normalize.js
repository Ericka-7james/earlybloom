/**
 * @fileoverview Input normalization helpers for EarlyBloom job scoring.
 */

import { KNOWN_SKILLS } from "./scoring.constants";
import {
  extractYearsExperience,
  inferHybrid,
  inferOnsite,
  inferRemote,
  normalizeText,
} from "./scoring.utils";

/**
 * Normalizes a raw job into a consistent internal shape.
 *
 * @param {Object} rawJob Raw job listing.
 * @returns {Object} Normalized job.
 */
export function normalizeJob(rawJob = {}) {
  const title = rawJob.title ?? "";
  const description = [
    rawJob.description,
    rawJob.summary,
    rawJob.requirements,
    rawJob.qualifications,
    rawJob.responsibilities,
  ]
    .filter(Boolean)
    .join(" ");

  const location =
    rawJob.location ??
    rawJob.jobLocation ??
    rawJob.locationText ??
    rawJob.city ??
    "";

  const compensation =
    rawJob.compensation ??
    rawJob.salary ??
    rawJob.salaryRange ??
    rawJob.pay ??
    "";

  return {
    raw: rawJob,
    title,
    titleLower: normalizeText(title),
    description,
    descriptionLower: normalizeText(description),
    company: rawJob.company ?? rawJob.companyName ?? "",
    source: rawJob.source ?? rawJob.platform ?? "",
    location,
    locationLower: normalizeText(location),
    compensation,
    isRemote: inferRemote(rawJob, location, description),
    isHybrid: inferHybrid(rawJob, location, description),
    isOnsite: inferOnsite(rawJob, location, description),
    yearsExperienceRequired: extractYearsExperience(`${title} ${description}`),
    skills: extractJobSkills(rawJob, description),
  };
}

/**
 * Normalizes a user profile into scoring-friendly data.
 *
 * @param {Object} userProfile User profile.
 * @returns {Object} Normalized user profile.
 */
export function normalizeUserProfile(userProfile = {}) {
  const skills = Array.isArray(userProfile.skills)
    ? userProfile.skills
    : Array.isArray(userProfile.topSkills)
    ? userProfile.topSkills
    : [];

  const targetTitles = Array.isArray(userProfile.targetTitles)
    ? userProfile.targetTitles
    : Array.isArray(userProfile.roles)
    ? userProfile.roles
    : [];

  const preferredLocations = Array.isArray(userProfile.preferredLocations)
    ? userProfile.preferredLocations
    : userProfile.location
    ? [userProfile.location]
    : [];

  return {
    raw: userProfile,
    experienceYears: Number.isFinite(userProfile.experienceYears)
      ? userProfile.experienceYears
      : Number.isFinite(userProfile.yearsOfExperience)
      ? userProfile.yearsOfExperience
      : 0,
    skills: skills.map(normalizeText).filter(Boolean),
    targetTitles: targetTitles.map(normalizeText).filter(Boolean),
    preferredLocations: preferredLocations.map(normalizeText).filter(Boolean),
    remotePreference:
      normalizeText(userProfile.remotePreference || userProfile.workPreference) ||
      "flexible",
  };
}

/**
 * Extracts a normalized set of job skills.
 *
 * V1 keeps this intentionally simple and readable. Later, this can be swapped
 * for a richer taxonomy or embeddings-based matcher.
 *
 * @param {Object} rawJob Raw job listing.
 * @param {string} description Description text.
 * @returns {Set<string>} Normalized skill set.
 */
function extractJobSkills(rawJob, description = "") {
  const rawSkills = Array.isArray(rawJob.skills) ? rawJob.skills : [];
  const combinedText = normalizeText(`${description} ${rawSkills.join(" ")}`);

  const found = new Set();

  KNOWN_SKILLS.forEach((skill) => {
    const normalizedSkill = normalizeText(skill);
    if (combinedText.includes(normalizedSkill)) {
      found.add(normalizedSkill);
    }
  });

  rawSkills.forEach((skill) => {
    const normalizedSkill = normalizeText(skill);
    if (normalizedSkill) {
      found.add(normalizedSkill);
    }
  });

  return found;
}