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
  const requirements = rawJob.requirements ?? {};
  const signals = rawJob.signals ?? {};

  const location =
    rawJob.location?.display ??
    rawJob.location ??
    rawJob.jobLocation ??
    rawJob.locationText ??
    rawJob.city ??
    "";

  const descriptionParts = [
    rawJob.description,
    rawJob.summary,
    rawJob.qualifications,
    rawJob.responsibilities,
    requirements.educationRequirement,
    ...(Array.isArray(requirements.requiredSkills)
      ? requirements.requiredSkills
      : []),
    ...(Array.isArray(requirements.preferredSkills)
      ? requirements.preferredSkills
      : []),
  ];

  const description = descriptionParts.filter(Boolean).join(" ");

  const structuredMinYears = Number.isFinite(requirements.minYearsRequired)
    ? requirements.minYearsRequired
    : null;

  const structuredMaxYears = Number.isFinite(requirements.maxYearsRequired)
    ? requirements.maxYearsRequired
    : null;

  const extractedYears = extractYearsExperience(`${title} ${description}`);

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
    workplaceType: rawJob.workplaceType ?? "",
    employmentType: rawJob.employmentType ?? "",
    roleType: rawJob.roleType ?? "",
    compensation:
      rawJob.compensation ??
      rawJob.salary ??
      rawJob.salaryRange ??
      rawJob.pay ??
      "",
    isRemote: inferRemote(rawJob, location, description),
    isHybrid: inferHybrid(rawJob, location, description),
    isOnsite: inferOnsite(rawJob, location, description),
    minYearsRequired: structuredMinYears ?? 0,
    maxYearsRequired: structuredMaxYears ?? extractedYears,
    yearsExperienceRequired: structuredMaxYears ?? extractedYears,
    skills: extractJobSkills(rawJob, description),
    requiredSkills: normalizeSkillList(requirements.requiredSkills),
    preferredSkills: normalizeSkillList(requirements.preferredSkills),
    signals: {
      mentionsMentorship: Boolean(signals.mentionsMentorship),
      mentionsOwnership: Boolean(signals.mentionsOwnership),
      mentionsLeadership: Boolean(signals.mentionsLeadership),
      mentionsArchitecture: Boolean(signals.mentionsArchitecture),
      titleSuggestsJunior: Boolean(signals.titleSuggestsJunior),
      descriptionSuggestsJunior: Boolean(signals.descriptionSuggestsJunior),
      titleDescriptionMismatch: Boolean(signals.titleDescriptionMismatch),
      hasClearRequirements: Boolean(signals.hasClearRequirements),
      hasSeparatePreferredSkills: Boolean(signals.hasSeparatePreferredSkills),
    },
    warnings: Array.isArray(rawJob.warnings) ? rawJob.warnings : [],
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
 * @param {Object} rawJob Raw job listing.
 * @param {string} description Description text.
 * @returns {Set<string>} Normalized skill set.
 */
function extractJobSkills(rawJob, description = "") {
  const requirements = rawJob.requirements ?? {};

  const rawSkills = [
    ...(Array.isArray(requirements.requiredSkills)
      ? requirements.requiredSkills
      : []),
    ...(Array.isArray(requirements.preferredSkills)
      ? requirements.preferredSkills
      : []),
    ...(Array.isArray(rawJob.skills) ? rawJob.skills : []),
  ];

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

/**
 * Normalizes a skill list into lowercase scoring-friendly strings.
 *
 * @param {string[] | undefined} skills Raw skills.
 * @returns {string[]} Normalized skills.
 */
function normalizeSkillList(skills = []) {
  return Array.isArray(skills)
    ? skills.map(normalizeText).filter(Boolean)
    : [];
}