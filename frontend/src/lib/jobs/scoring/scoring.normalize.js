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

  const canonicalSkills = extractCanonicalJobSkills(rawJob);
  const normalizedSkills = canonicalSkills.map(normalizeText);

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
    canonicalSkills,
    skills: new Set(normalizedSkills),
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

  const canonicalSkills = dedupeCanonicalSkills(skills);

  return {
    raw: userProfile,
    experienceYears: Number.isFinite(userProfile.experienceYears)
      ? userProfile.experienceYears
      : Number.isFinite(userProfile.yearsOfExperience)
        ? userProfile.yearsOfExperience
        : 0,
    canonicalSkills,
    skills: canonicalSkills.map(normalizeText).filter(Boolean),
    targetTitles: targetTitles.map(normalizeText).filter(Boolean),
    preferredLocations: preferredLocations.map(normalizeText).filter(Boolean),
    remotePreference:
      normalizeText(userProfile.remotePreference || userProfile.workPreference) ||
      "flexible",
  };
}

/**
 * Extracts canonical job skills from available raw fields.
 *
 * This prefers backend-provided normalized `skills` arrays when present,
 * then falls back to requirement lists and lightweight known-skill scanning.
 *
 * @param {Object} rawJob Raw job listing.
 * @returns {string[]} Canonical job skills.
 */
function extractCanonicalJobSkills(rawJob = {}) {
  const requirements = rawJob.requirements ?? {};

  const explicitSkills = [
    ...(Array.isArray(rawJob.skills) ? rawJob.skills : []),
    ...(Array.isArray(rawJob.required_skills) ? rawJob.required_skills : []),
    ...(Array.isArray(rawJob.preferred_skills) ? rawJob.preferred_skills : []),
    ...(Array.isArray(requirements.requiredSkills)
      ? requirements.requiredSkills
      : []),
    ...(Array.isArray(requirements.preferredSkills)
      ? requirements.preferredSkills
      : []),
  ];

  const canonicalExplicitSkills = dedupeCanonicalSkills(explicitSkills);

  if (canonicalExplicitSkills.length > 0) {
    return canonicalExplicitSkills;
  }

  const description = [
    rawJob.title,
    rawJob.summary,
    rawJob.description,
  ]
    .filter(Boolean)
    .join(" ");

  const normalizedDescription = normalizeText(description);

  return KNOWN_SKILLS.filter((skill) =>
    normalizedDescription.includes(normalizeText(skill))
  );
}

/**
 * Deduplicates a skill list while preserving canonical casing from input.
 *
 * @param {string[] | undefined} skills Raw skills.
 * @returns {string[]} Deduplicated canonical skills.
 */
function dedupeCanonicalSkills(skills = []) {
  if (!Array.isArray(skills)) {
    return [];
  }

  const result = [];
  const seen = new Set();

  skills.forEach((skill) => {
    const text = String(skill || "").trim();
    if (!text) {
      return;
    }

    const key = normalizeText(text);
    if (!key || seen.has(key)) {
      return;
    }

    seen.add(key);
    result.push(text);
  });

  return result;
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