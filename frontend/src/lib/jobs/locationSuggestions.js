// src/lib/jobs/locationSuggestions.js
/**
 * @fileoverview Lightweight location suggestions for the jobs filters UI.
 *
 * Design goals:
 * - fast in-memory suggestions
 * - no network dependency
 * - curated major-city and state coverage
 * - includes common workplace shortcuts like remote and hybrid
 * - keeps selected values compact and job-board friendly
 */

const LOCATION_SUGGESTIONS = [
  { label: "Remote", value: "Remote", type: "workplace" },
  { label: "Hybrid", value: "Hybrid", type: "workplace" },
  { label: "Onsite", value: "Onsite", type: "workplace" },

  { label: "Atlanta, GA", value: "Atlanta, GA", type: "city" },
  { label: "Austin, TX", value: "Austin, TX", type: "city" },
  { label: "Boston, MA", value: "Boston, MA", type: "city" },
  { label: "Charlotte, NC", value: "Charlotte, NC", type: "city" },
  { label: "Chicago, IL", value: "Chicago, IL", type: "city" },
  { label: "Dallas, TX", value: "Dallas, TX", type: "city" },
  { label: "Denver, CO", value: "Denver, CO", type: "city" },
  { label: "Houston, TX", value: "Houston, TX", type: "city" },
  { label: "Los Angeles, CA", value: "Los Angeles, CA", type: "city" },
  { label: "Miami, FL", value: "Miami, FL", type: "city" },
  { label: "Nashville, TN", value: "Nashville, TN", type: "city" },
  { label: "New York, NY", value: "New York, NY", type: "city" },
  { label: "Philadelphia, PA", value: "Philadelphia, PA", type: "city" },
  { label: "Phoenix, AZ", value: "Phoenix, AZ", type: "city" },
  { label: "Raleigh, NC", value: "Raleigh, NC", type: "city" },
  { label: "San Diego, CA", value: "San Diego, CA", type: "city" },
  { label: "San Francisco, CA", value: "San Francisco, CA", type: "city" },
  { label: "San Jose, CA", value: "San Jose, CA", type: "city" },
  { label: "Seattle, WA", value: "Seattle, WA", type: "city" },
  { label: "Washington, DC", value: "Washington, DC", type: "city" },

  { label: "California", value: "California", type: "state" },
  { label: "Colorado", value: "Colorado", type: "state" },
  { label: "Florida", value: "Florida", type: "state" },
  { label: "Georgia", value: "Georgia", type: "state" },
  { label: "Illinois", value: "Illinois", type: "state" },
  { label: "Massachusetts", value: "Massachusetts", type: "state" },
  { label: "New York", value: "New York", type: "state" },
  { label: "North Carolina", value: "North Carolina", type: "state" },
  { label: "Texas", value: "Texas", type: "state" },
  { label: "Washington", value: "Washington", type: "state" },
];

function normalizeSuggestionText(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[|/]+/g, " ")
    .replace(/[()]/g, " ")
    .replace(/\s+/g, " ");
}

/**
 * Returns a ranked list of location suggestions for a query.
 *
 * Ranking:
 * - exact value startsWith
 * - label startsWith
 * - token inclusion fallback
 *
 * @param {string} query User-entered query.
 * @param {number} [limit=6] Max suggestions.
 * @returns {Array<{label:string,value:string,type:string}>} Suggestions.
 */
export function getLocationSuggestions(query, limit = 6) {
  const normalizedQuery = normalizeSuggestionText(query);

  if (!normalizedQuery) {
    return LOCATION_SUGGESTIONS.slice(0, limit);
  }

  const ranked = LOCATION_SUGGESTIONS.map((item) => {
    const normalizedValue = normalizeSuggestionText(item.value);
    const normalizedLabel = normalizeSuggestionText(item.label);

    let score = 0;

    if (normalizedValue.startsWith(normalizedQuery)) {
      score += 5;
    }

    if (normalizedLabel.startsWith(normalizedQuery)) {
      score += 4;
    }

    if (normalizedValue.includes(normalizedQuery)) {
      score += 3;
    }

    if (normalizedLabel.includes(normalizedQuery)) {
      score += 2;
    }

    const queryTokens = normalizedQuery.split(/[,\s]+/).filter(Boolean);
    if (
      queryTokens.length > 1 &&
      queryTokens.every(
        (token) =>
          normalizedValue.includes(token) || normalizedLabel.includes(token)
      )
    ) {
      score += 2;
    }

    return {
      ...item,
      score,
    };
  })
    .filter((item) => item.score > 0)
    .sort((left, right) => {
      const scoreDelta = right.score - left.score;
      if (scoreDelta !== 0) {
        return scoreDelta;
      }

      const workplacePriority = {
        workplace: 0,
        city: 1,
        state: 2,
      };

      const typeDelta =
        (workplacePriority[left.type] ?? 99) - (workplacePriority[right.type] ?? 99);

      if (typeDelta !== 0) {
        return typeDelta;
      }

      return left.label.localeCompare(right.label);
    });

  const deduped = [];
  const seen = new Set();

  ranked.forEach((item) => {
    const key = `${item.type}:${item.label.toLowerCase()}`;
    if (seen.has(key)) {
      return;
    }

    seen.add(key);
    deduped.push({
      label: item.label,
      value: item.value,
      type: item.type,
    });
  });

  return deduped.slice(0, limit);
}

export { LOCATION_SUGGESTIONS };