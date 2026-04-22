// src/lib/jobs/locationSuggestions.js
/**
 * @fileoverview Lightweight location suggestions for the jobs filters UI.
 *
 * Design goals:
 * - fast in-memory suggestions
 * - no network dependency
 * - curated major-city and state coverage
 * - includes common workplace shortcuts like remote and hybrid
 */

const LOCATION_SUGGESTIONS = [
  { label: "Remote", value: "remote", type: "workplace" },
  { label: "Hybrid", value: "hybrid", type: "workplace" },
  { label: "Onsite", value: "onsite", type: "workplace" },

  { label: "Atlanta, GA", value: "atlanta", type: "city" },
  { label: "Austin, TX", value: "austin", type: "city" },
  { label: "Boston, MA", value: "boston", type: "city" },
  { label: "Charlotte, NC", value: "charlotte", type: "city" },
  { label: "Chicago, IL", value: "chicago", type: "city" },
  { label: "Dallas, TX", value: "dallas", type: "city" },
  { label: "Denver, CO", value: "denver", type: "city" },
  { label: "Houston, TX", value: "houston", type: "city" },
  { label: "Los Angeles, CA", value: "los angeles", type: "city" },
  { label: "Miami, FL", value: "miami", type: "city" },
  { label: "Nashville, TN", value: "nashville", type: "city" },
  { label: "New York, NY", value: "new york", type: "city" },
  { label: "Philadelphia, PA", value: "philadelphia", type: "city" },
  { label: "Phoenix, AZ", value: "phoenix", type: "city" },
  { label: "Raleigh, NC", value: "raleigh", type: "city" },
  { label: "San Diego, CA", value: "san diego", type: "city" },
  { label: "San Francisco, CA", value: "san francisco", type: "city" },
  { label: "San Jose, CA", value: "san jose", type: "city" },
  { label: "Seattle, WA", value: "seattle", type: "city" },
  { label: "Washington, DC", value: "washington dc", type: "city" },

  { label: "California", value: "california", type: "state" },
  { label: "Colorado", value: "colorado", type: "state" },
  { label: "Florida", value: "florida", type: "state" },
  { label: "Georgia", value: "georgia", type: "state" },
  { label: "Illinois", value: "illinois", type: "state" },
  { label: "Massachusetts", value: "massachusetts", type: "state" },
  { label: "New York", value: "new york", type: "state" },
  { label: "North Carolina", value: "north carolina", type: "state" },
  { label: "Texas", value: "texas", type: "state" },
  { label: "Washington", value: "washington", type: "state" },
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

    const queryTokens = normalizedQuery.split(" ").filter(Boolean);
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