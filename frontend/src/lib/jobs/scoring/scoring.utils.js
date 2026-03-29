/**
 * @fileoverview Shared utility helpers for EarlyBloom job scoring.
 */

/**
 * Normalizes text for keyword matching.
 *
 * @param {string} value Raw text.
 * @returns {string} Normalized text.
 */
export function normalizeText(value = "") {
  return String(value)
    .toLowerCase()
    .replace(/[^\w\s/+.-]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * Returns whether the text contains any phrase from a list.
 *
 * @param {string} text Normalized text.
 * @param {string[]} phrases Phrase list.
 * @returns {boolean} Whether a phrase matched.
 */
export function containsAny(text, phrases = []) {
  return phrases.some((phrase) => text.includes(normalizeText(phrase)));
}

/**
 * Clamps a number to a range.
 *
 * @param {number} value Number to clamp.
 * @param {number} min Minimum bound.
 * @param {number} max Maximum bound.
 * @returns {number} Clamped value.
 */
export function clamp(value, min, max) {
  return Math.max(min, Math.min(max, Math.round(value)));
}

/**
 * Deduplicates strings while preserving order.
 *
 * @param {string[]} items Input items.
 * @returns {string[]} Deduplicated items.
 */
export function dedupeStrings(items = []) {
  return [...new Set(items.filter(Boolean))];
}

/**
 * Creates a fallback ID when the raw object does not provide one.
 *
 * @param {Object} rawJob Raw job listing.
 * @returns {string} Fallback ID.
 */
export function createFallbackId(rawJob = {}) {
  return normalizeText(
    `${rawJob.title ?? "job"}-${rawJob.company ?? "company"}-${rawJob.location ?? "location"}`
  ).replace(/\s+/g, "-");
}

/**
 * Attempts to extract years-of-experience requirements.
 *
 * Examples matched:
 * - 2+ years
 * - 3 years of experience
 * - minimum 1 year
 *
 * @param {string} text Free text.
 * @returns {number} Highest detected minimum years of experience, else 0.
 */
export function extractYearsExperience(text = "") {
  const normalized = normalizeText(text);

  const patterns = [
    /(\d+)\+?\s+years?\s+of\s+experience/g,
    /(\d+)\+?\s+years?\s+experience/g,
    /minimum\s+of\s+(\d+)\s+years?/g,
    /at\s+least\s+(\d+)\s+years?/g,
    /(\d+)\+?\s+yrs/g,
  ];

  let maxYears = 0;

  patterns.forEach((pattern) => {
    const matches = normalized.matchAll(pattern);

    for (const match of matches) {
      const value = Number(match[1]);
      if (Number.isFinite(value)) {
        maxYears = Math.max(maxYears, value);
      }
    }
  });

  return maxYears;
}

/**
 * Infers whether a role appears remote from available fields.
 *
 * @param {Object} rawJob Raw job listing.
 * @param {string} location Location text.
 * @param {string} description Description text.
 * @returns {boolean} Whether the role appears remote.
 */
export function inferRemote(rawJob, location = "", description = "") {
  const combined = normalizeText(
    `${rawJob.remote ?? ""} ${location} ${description} ${rawJob.workplaceType ?? ""}`
  );

  return combined.includes("remote") && !combined.includes("not remote");
}

/**
 * Infers whether a role appears hybrid from available fields.
 *
 * @param {Object} rawJob Raw job listing.
 * @param {string} location Location text.
 * @param {string} description Description text.
 * @returns {boolean} Whether the role appears hybrid.
 */
export function inferHybrid(rawJob, location = "", description = "") {
  const combined = normalizeText(
    `${rawJob.hybrid ?? ""} ${location} ${description} ${rawJob.workplaceType ?? ""}`
  );

  return combined.includes("hybrid");
}

/**
 * Infers whether a role appears onsite from available fields.
 *
 * @param {Object} rawJob Raw job listing.
 * @param {string} location Location text.
 * @param {string} description Description text.
 * @returns {boolean} Whether the role appears onsite.
 */
export function inferOnsite(rawJob, location = "", description = "") {
  const combined = normalizeText(
    `${rawJob.onsite ?? ""} ${location} ${description} ${rawJob.workplaceType ?? ""}`
  );

  return combined.includes("onsite") || combined.includes("on-site");
}