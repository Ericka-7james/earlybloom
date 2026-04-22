// src/lib/jobs/jobFilters.js
/**
 * @fileoverview Shared frontend job filtering utilities for EarlyBloom.
 *
 * This module powers client-side filtering on the jobs page.
 *
 * Responsibilities:
 * - define filter option groups used by the UI
 * - normalize and toggle selected filter values
 * - infer job metadata when backend fields are incomplete
 * - filter jobs by experience level, workplace, role type, skills, and location
 * - derive active filter tags and summary text for compact UI display
 */

const FILTER_GROUPS = {
  experienceLevel: [
    { label: "Entry-level", value: "entry-level" },
    { label: "Junior", value: "junior" },
    { label: "Mid-level", value: "mid-level" },
    { label: "Senior", value: "senior" },
  ],
  workplace: [
    { label: "Remote", value: "remote" },
    { label: "Onsite", value: "onsite" },
    { label: "Hybrid", value: "hybrid" },
  ],
  roleType: [
    { label: "Frontend", value: "frontend" },
    { label: "Backend", value: "backend" },
    { label: "Full Stack", value: "full-stack" },
    { label: "Software Engineering", value: "software-engineering" },
    { label: "Mobile", value: "mobile" },
    { label: "Data", value: "data" },
    { label: "Data Engineering", value: "data-engineering" },
    { label: "Data Analyst", value: "data-analyst" },
    { label: "Machine Learning", value: "machine-learning" },
    { label: "AI", value: "ai" },
    { label: "DevOps", value: "devops" },
    { label: "SRE", value: "sre" },
    { label: "Cloud", value: "cloud" },
    { label: "Infrastructure", value: "infrastructure" },
    { label: "Cybersecurity", value: "cybersecurity" },
    { label: "QA", value: "qa" },
    { label: "Test Automation", value: "test-automation" },
    { label: "Product", value: "product" },
    { label: "Product Design", value: "product-design" },
    { label: "UX", value: "ux" },
    { label: "Solutions Engineering", value: "solutions-engineering" },
    { label: "Technical Support", value: "technical-support" },
    { label: "IT", value: "it" },
    { label: "Business Analyst", value: "business-analyst" },
    { label: "Platform", value: "platform" },
    { label: "Developer Tools", value: "developer-tools" },
  ],
};

const DEFAULT_SELECTED_EXPERIENCE_LEVELS = ["entry-level", "junior"];
const MAX_VISIBLE_SKILL_OPTIONS = 16;

const STATE_ALIASES = {
  al: "alabama",
  ak: "alaska",
  az: "arizona",
  ar: "arkansas",
  ca: "california",
  co: "colorado",
  ct: "connecticut",
  de: "delaware",
  fl: "florida",
  ga: "georgia",
  hi: "hawaii",
  id: "idaho",
  il: "illinois",
  in: "indiana",
  ia: "iowa",
  ks: "kansas",
  ky: "kentucky",
  la: "louisiana",
  me: "maine",
  md: "maryland",
  ma: "massachusetts",
  mi: "michigan",
  mn: "minnesota",
  ms: "mississippi",
  mo: "missouri",
  mt: "montana",
  ne: "nebraska",
  nv: "nevada",
  nh: "new hampshire",
  nj: "new jersey",
  nm: "new mexico",
  ny: "new york",
  nc: "north carolina",
  nd: "north dakota",
  oh: "ohio",
  ok: "oklahoma",
  or: "oregon",
  pa: "pennsylvania",
  ri: "rhode island",
  sc: "south carolina",
  sd: "south dakota",
  tn: "tennessee",
  tx: "texas",
  ut: "utah",
  vt: "vermont",
  va: "virginia",
  wa: "washington",
  wv: "west virginia",
  wi: "wisconsin",
  wy: "wyoming",
  dc: "district of columbia",
};

/**
 * Normalizes a scalar value into a lowercase comparison-friendly string.
 *
 * @param {unknown} value Raw value.
 * @returns {string} Normalized string value.
 */
function normalizeValue(value) {
  return String(value || "").trim().toLowerCase();
}

/**
 * Normalizes free text for tolerant matching.
 *
 * @param {unknown} value Raw text.
 * @returns {string} Normalized text.
 */
function normalizeSearchText(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[|/]+/g, " ")
    .replace(/[()]/g, " ")
    .replace(/\s+/g, " ");
}

/**
 * Compares two arrays as sets.
 *
 * Ordering is ignored. Duplicate values are treated as a single logical item.
 *
 * @param {string[]} left Left list.
 * @param {string[]} right Right list.
 * @returns {boolean} Whether both arrays contain the same values.
 */
function arraysEqualAsSets(left, right) {
  if (left.length !== right.length) {
    return false;
  }

  const leftSet = new Set(left);
  return right.every((value) => leftSet.has(value));
}

/**
 * Toggles a selected value in a list while preserving insertion order.
 *
 * @param {string[]} currentValues Existing selected values.
 * @param {string} value Value to toggle.
 * @returns {string[]} Updated selected values.
 */
function toggleSelectedValue(currentValues, value) {
  if (currentValues.includes(value)) {
    return currentValues.filter((item) => item !== value);
  }

  return [...currentValues, value];
}

/**
 * Returns a normalized experience level for a job.
 *
 * Prefers explicit structured job fields but falls back to text heuristics.
 *
 * @param {object} job Job object.
 * @returns {string} Normalized experience level.
 */
function getJobExperienceLevel(job) {
  const directLevel = normalizeValue(
    job.experienceLevel || job.experience_level || job.level
  );

  if (
    directLevel === "entry-level" ||
    directLevel === "junior" ||
    directLevel === "mid-level" ||
    directLevel === "senior"
  ) {
    return directLevel;
  }

  if (directLevel === "mid") {
    return "mid-level";
  }

  const haystack = normalizeValue(
    `${job.title || ""} ${job.summary || ""} ${job.description || ""}`
  );

  if (
    haystack.includes("entry-level") ||
    haystack.includes("entry level") ||
    haystack.includes("new grad") ||
    haystack.includes("new graduate") ||
    haystack.includes("recent graduate") ||
    haystack.includes("graduate") ||
    haystack.includes("early career") ||
    haystack.includes("apprentice") ||
    haystack.includes("intern")
  ) {
    return "entry-level";
  }

  if (
    haystack.includes("junior") ||
    haystack.includes(" jr ") ||
    haystack.startsWith("jr ") ||
    haystack.includes("junior-level")
  ) {
    return "junior";
  }

  if (
    haystack.includes("mid-level") ||
    haystack.includes("mid level") ||
    haystack.includes("intermediate") ||
    haystack.includes("level ii") ||
    haystack.includes("level 2")
  ) {
    return "mid-level";
  }

  if (
    haystack.includes("senior") ||
    haystack.includes("staff") ||
    haystack.includes("principal") ||
    haystack.includes("lead ") ||
    haystack.startsWith("lead") ||
    haystack.includes("chief") ||
    haystack.includes("director")
  ) {
    return "senior";
  }

  return "unknown";
}

/**
 * Returns a normalized workplace type for a job.
 *
 * @param {object} job Job object.
 * @returns {string} Workplace type.
 */
function getJobWorkplace(job) {
  const directRemoteType = normalizeValue(job.remoteType || job.remote_type);

  if (
    directRemoteType === "remote" ||
    directRemoteType === "onsite" ||
    directRemoteType === "hybrid"
  ) {
    return directRemoteType;
  }

  if (job.remote === true) {
    return "remote";
  }

  const haystack = normalizeValue(
    `${job.location || ""} ${job.location_display || ""} ${job.cardLocation || ""} ${job.summary || ""} ${job.description || ""}`
  );

  if (haystack.includes("hybrid") || haystack.includes("flexible hybrid")) {
    return "hybrid";
  }

  if (
    haystack.includes("remote") ||
    haystack.includes("telework") ||
    haystack.includes("work from home")
  ) {
    return "remote";
  }

  if (
    haystack.includes("onsite") ||
    haystack.includes("on-site") ||
    haystack.includes("in-office") ||
    haystack.includes("in office")
  ) {
    return "onsite";
  }

  return "unknown";
}

/**
 * Infers a normalized role type for a job.
 *
 * @param {object} job Job object.
 * @returns {string} Role type.
 */
function inferRoleType(job) {
  const directRoleType = normalizeValue(job.roleType || job.role_type);

  if (directRoleType && directRoleType !== "unknown") {
    return directRoleType;
  }

  const haystack = ` ${normalizeValue(
    `${job.title || ""} ${job.summary || ""} ${job.description || ""}`
  )} `;

  if (
    haystack.includes(" frontend ") ||
    haystack.includes(" front-end ") ||
    haystack.includes(" react ") ||
    haystack.includes(" ui engineer ")
  ) {
    return "frontend";
  }

  if (
    haystack.includes(" backend ") ||
    haystack.includes(" back-end ") ||
    haystack.includes(" api ") ||
    haystack.includes(" server-side ")
  ) {
    return "backend";
  }

  if (
    haystack.includes(" full stack ") ||
    haystack.includes(" full-stack ") ||
    haystack.includes(" fullstack ")
  ) {
    return "full-stack";
  }

  if (
    haystack.includes(" ios ") ||
    haystack.includes(" android ") ||
    haystack.includes(" mobile ")
  ) {
    return "mobile";
  }

  if (
    haystack.includes(" data engineer ") ||
    haystack.includes(" etl ") ||
    haystack.includes(" pipeline ")
  ) {
    return "data-engineering";
  }

  if (
    haystack.includes(" data analyst ") ||
    haystack.includes(" business intelligence ") ||
    haystack.includes(" reporting analyst ")
  ) {
    return "data-analyst";
  }

  if (
    haystack.includes(" machine learning ") ||
    haystack.includes(" ml engineer ")
  ) {
    return "machine-learning";
  }

  if (
    haystack.includes(" artificial intelligence ") ||
    haystack.includes(" ai ") ||
    haystack.includes(" genai ") ||
    haystack.includes(" llm ")
  ) {
    return "ai";
  }

  if (
    haystack.includes(" devops ") ||
    haystack.includes(" devsecops ") ||
    haystack.includes(" ci/cd ")
  ) {
    return "devops";
  }

  if (
    haystack.includes(" site reliability ") ||
    haystack.includes(" sre ")
  ) {
    return "sre";
  }

  if (haystack.includes(" cloud ")) {
    return "cloud";
  }

  if (
    haystack.includes(" infrastructure ") ||
    haystack.includes(" sysadmin ") ||
    haystack.includes(" systems administration ")
  ) {
    return "infrastructure";
  }

  if (
    haystack.includes(" cyber ") ||
    haystack.includes(" security ") ||
    haystack.includes(" infosec ")
  ) {
    return "cybersecurity";
  }

  if (
    haystack.includes(" test automation ") ||
    haystack.includes(" sdet ")
  ) {
    return "test-automation";
  }

  if (
    haystack.includes(" qa ") ||
    haystack.includes(" quality assurance ")
  ) {
    return "qa";
  }

  if (
    haystack.includes(" product manager ") ||
    haystack.includes(" product owner ")
  ) {
    return "product";
  }

  if (
    haystack.includes(" product design ") ||
    haystack.includes(" product designer ")
  ) {
    return "product-design";
  }

  if (
    haystack.includes(" ux ") ||
    haystack.includes(" user experience ") ||
    haystack.includes(" ui/ux ")
  ) {
    return "ux";
  }

  if (
    haystack.includes(" solutions engineer ") ||
    haystack.includes(" sales engineer ") ||
    haystack.includes(" implementation engineer ")
  ) {
    return "solutions-engineering";
  }

  if (
    haystack.includes(" technical support ") ||
    haystack.includes(" support engineer ") ||
    haystack.includes(" help desk ")
  ) {
    return "technical-support";
  }

  if (
    haystack.includes(" business analyst ") ||
    haystack.includes(" systems analyst ")
  ) {
    return "business-analyst";
  }

  if (
    haystack.includes(" it specialist ") ||
    haystack.includes(" it support ") ||
    haystack.includes(" information technology ")
  ) {
    return "it";
  }

  if (haystack.includes(" platform ")) {
    return "platform";
  }

  if (
    haystack.includes(" developer tools ") ||
    haystack.includes(" devtools ")
  ) {
    return "developer-tools";
  }

  if (
    haystack.includes(" software engineer ") ||
    haystack.includes(" software developer ") ||
    haystack.includes(" application developer ") ||
    haystack.includes(" programmer ")
  ) {
    return "software-engineering";
  }

  if (
    haystack.includes(" data ") ||
    haystack.includes(" analytics ") ||
    haystack.includes(" analyst ")
  ) {
    return "data";
  }

  return "unknown";
}

/**
 * Returns a deduplicated canonical job skill list from available frontend fields.
 *
 * This prefers already-normalized backend-provided `skills` arrays, then
 * falls back to required and preferred skill lists.
 *
 * @param {object} job Job object.
 * @returns {string[]} Ordered canonical skills.
 */
function getJobSkills(job) {
  const sources = [
    ...(Array.isArray(job.skills) ? job.skills : []),
    ...(Array.isArray(job.required_skills) ? job.required_skills : []),
    ...(Array.isArray(job.preferred_skills) ? job.preferred_skills : []),
    ...(Array.isArray(job.requiredSkills) ? job.requiredSkills : []),
    ...(Array.isArray(job.preferredSkills) ? job.preferredSkills : []),
  ];

  const deduped = [];
  const seen = new Set();

  sources.forEach((skill) => {
    const text = String(skill || "").trim();
    if (!text) {
      return;
    }

    const key = normalizeValue(text);
    if (!key || seen.has(key)) {
      return;
    }

    seen.add(key);
    deduped.push(text);
  });

  return deduped;
}

/**
 * Returns whether a job matches the selected skills filter.
 *
 * V1 behavior is "match any selected skill."
 *
 * @param {object} job Job object.
 * @param {string[]} selectedSkills Selected canonical skills.
 * @returns {boolean} Whether the job should pass the skill filter.
 */
function matchesSelectedSkills(job, selectedSkills = []) {
  if (!Array.isArray(selectedSkills) || selectedSkills.length === 0) {
    return true;
  }

  const selectedSkillSet = new Set(selectedSkills.map(normalizeValue));
  const jobSkills = getJobSkills(job);

  return jobSkills.some((skill) => selectedSkillSet.has(normalizeValue(skill)));
}

/**
 * Expands a location query into a few tolerant equivalents.
 *
 * @param {string} locationQuery User-entered location query.
 * @returns {string[]} Normalized comparison tokens.
 */
function expandLocationQuery(locationQuery = "") {
  const normalized = normalizeSearchText(locationQuery);
  if (!normalized) {
    return [];
  }

  const values = new Set([normalized]);

  if (normalized === "remote") {
    values.add("telework");
    values.add("work from home");
    values.add("wfh");
  }

  if (normalized === "hybrid") {
    values.add("flexible hybrid");
  }

  if (normalized === "onsite" || normalized === "on-site" || normalized === "on site") {
    values.add("onsite");
    values.add("on-site");
    values.add("on site");
    values.add("in office");
    values.add("in-office");
  }

  if (STATE_ALIASES[normalized]) {
    values.add(STATE_ALIASES[normalized]);
  }

  Object.entries(STATE_ALIASES).forEach(([abbr, fullName]) => {
    if (normalized === fullName) {
      values.add(abbr);
    }
  });

  return Array.from(values);
}

/**
 * Returns whether a job matches a flexible location query.
 *
 * Matching rules:
 * - empty query matches everything
 * - workplace-like values such as remote/hybrid are supported
 * - city/state text uses substring matching against normalized location text
 * - multi-token queries like "new york ny" require all tokens to appear
 *
 * @param {object} job Job object.
 * @param {string} locationQuery User-entered location query.
 * @returns {boolean} Whether the job passes location filtering.
 */
function matchesLocationQuery(job, locationQuery = "") {
  const normalizedQuery = normalizeSearchText(locationQuery);

  if (!normalizedQuery) {
    return true;
  }

  const haystack = normalizeSearchText(
    [
      job.location,
      job.location_display,
      job.cardLocation,
      job.modalLocation,
      job.fullLocation,
      job.workplaceType,
      job.remoteType,
      job.summary,
    ]
      .filter(Boolean)
      .join(" ")
  );

  if (!haystack) {
    return false;
  }

  const expandedQueries = expandLocationQuery(normalizedQuery);

  if (expandedQueries.some((value) => haystack.includes(value))) {
    return true;
  }

  const queryTokens = normalizedQuery.split(/[,\s]+/).filter(Boolean);
  if (queryTokens.length <= 1) {
    return false;
  }

  const expandedTokenSet = new Set(queryTokens);

  queryTokens.forEach((token) => {
    if (STATE_ALIASES[token]) {
      expandedTokenSet.add(STATE_ALIASES[token]);
    }

    Object.entries(STATE_ALIASES).forEach(([abbr, fullName]) => {
      if (token === fullName) {
        expandedTokenSet.add(abbr);
      }
    });
  });

  return Array.from(expandedTokenSet).every((token) => haystack.includes(token));
}

/**
 * Filters jobs using selected experience, workplace, role type, skills,
 * and optional location query.
 *
 * @param {object[]} jobs Jobs array.
 * @param {{
 *   locationQuery?: string,
 *   selectedExperienceLevels: string[],
 *   selectedWorkplaces: string[],
 *   selectedRoleTypes: string[],
 *   selectedSkills?: string[],
 * }} filters Selected filter state.
 * @returns {object[]} Filtered jobs.
 */
function filterJobs(
  jobs,
  {
    locationQuery = "",
    selectedExperienceLevels,
    selectedWorkplaces,
    selectedRoleTypes,
    selectedSkills = [],
  }
) {
  return jobs.filter((job) => {
    const experienceLevel = getJobExperienceLevel(job);
    const workplace = getJobWorkplace(job);
    const roleType = inferRoleType(job);

    const matchesLocation = matchesLocationQuery(job, locationQuery);

    const matchesExperienceLevel =
      selectedExperienceLevels.length === 0 ||
      selectedExperienceLevels.includes(experienceLevel);

    const matchesWorkplace =
      selectedWorkplaces.length === 0 ||
      selectedWorkplaces.includes(workplace);

    const matchesRoleType =
      selectedRoleTypes.length === 0 ||
      selectedRoleTypes.includes(roleType);

    const matchesSkills = matchesSelectedSkills(job, selectedSkills);

    return (
      matchesLocation &&
      matchesExperienceLevel &&
      matchesWorkplace &&
      matchesRoleType &&
      matchesSkills
    );
  });
}

/**
 * Builds compact summary text for the mobile filters trigger.
 *
 * @param {{
 *   locationQuery?: string,
 *   selectedExperienceLevels: string[],
 *   selectedWorkplaces: string[],
 *   selectedRoleTypes: string[],
 *   selectedSkills?: string[],
 * }} filters Current filter state.
 * @returns {string} Summary text.
 */
function getFilterSummary({
  locationQuery = "",
  selectedExperienceLevels,
  selectedWorkplaces,
  selectedRoleTypes,
  selectedSkills = [],
}) {
  const parts = [];

  if (String(locationQuery || "").trim()) {
    parts.push("1 location");
  }

  if (selectedExperienceLevels.length > 0) {
    parts.push(`${selectedExperienceLevels.length} level`);
  }

  if (selectedWorkplaces.length > 0) {
    parts.push(`${selectedWorkplaces.length} workplace`);
  }

  if (selectedRoleTypes.length > 0) {
    parts.push(`${selectedRoleTypes.length} role type`);
  }

  if (selectedSkills.length > 0) {
    parts.push(`${selectedSkills.length} skill`);
  }

  if (parts.length === 0) {
    return "All roles";
  }

  return parts.join(" • ");
}

/**
 * Builds visible active-filter tags for the jobs page.
 *
 * @param {{
 *   locationQuery?: string,
 *   selectedExperienceLevels: string[],
 *   selectedWorkplaces: string[],
 *   selectedRoleTypes: string[],
 *   selectedSkills?: string[],
 * }} filters Current filter state.
 * @returns {Array<{group:string,label:string,value:string,type:string}>} Active tags.
 */
function getActiveFilterTags({
  locationQuery = "",
  selectedExperienceLevels,
  selectedWorkplaces,
  selectedRoleTypes,
  selectedSkills = [],
}) {
  const tags = [];

  if (String(locationQuery || "").trim()) {
    tags.push({
      group: "Location",
      label: String(locationQuery).trim(),
      value: String(locationQuery).trim(),
      type: "location",
    });
  }

  FILTER_GROUPS.experienceLevel.forEach((option) => {
    if (selectedExperienceLevels.includes(option.value)) {
      tags.push({
        group: "Experience",
        label: option.label,
        value: option.value,
        type: "experience",
      });
    }
  });

  FILTER_GROUPS.workplace.forEach((option) => {
    if (selectedWorkplaces.includes(option.value)) {
      tags.push({
        group: "Workplace",
        label: option.label,
        value: option.value,
        type: "workplace",
      });
    }
  });

  FILTER_GROUPS.roleType.forEach((option) => {
    if (selectedRoleTypes.includes(option.value)) {
      tags.push({
        group: "Role type",
        label: option.label,
        value: option.value,
        type: "role",
      });
    }
  });

  selectedSkills.forEach((skill) => {
    tags.push({
      group: "Skills",
      label: skill,
      value: skill,
      type: "skill",
    });
  });

  return tags;
}

/**
 * Builds visible skill filter options.
 *
 * Source priority:
 * 1. resume/profile skills
 * 2. most common current job-result skills
 *
 * This keeps the UI personalized while still surfacing relevant market skills.
 *
 * @param {object[]} jobs Current mapped jobs.
 * @param {string[]} profileSkills Resume or resolved profile skills.
 * @param {number} [maxVisible=MAX_VISIBLE_SKILL_OPTIONS] Maximum number of visible skills.
 * @returns {Array<{label:string,value:string,count:number,source:"profile"|"jobs"}>} Visible skill options.
 */
function getAvailableSkillOptions(
  jobs = [],
  profileSkills = [],
  maxVisible = MAX_VISIBLE_SKILL_OPTIONS
) {
  const counts = new Map();

  jobs.forEach((job) => {
    getJobSkills(job).forEach((skill) => {
      const key = normalizeValue(skill);
      if (!key) {
        return;
      }

      const existing = counts.get(key);
      if (existing) {
        existing.count += 1;
        return;
      }

      counts.set(key, {
        label: skill,
        value: skill,
        count: 1,
      });
    });
  });

  const normalizedProfileSkills = [];
  const seenProfile = new Set();

  profileSkills.forEach((skill) => {
    const text = String(skill || "").trim();
    const key = normalizeValue(text);
    if (!text || !key || seenProfile.has(key)) {
      return;
    }

    seenProfile.add(key);
    normalizedProfileSkills.push(text);
  });

  const prioritized = [];

  normalizedProfileSkills.forEach((skill) => {
    const key = normalizeValue(skill);
    const existing = counts.get(key);

    prioritized.push({
      label: existing?.label || skill,
      value: existing?.value || skill,
      count: existing?.count || 0,
      source: "profile",
    });
  });

  const remaining = Array.from(counts.entries())
    .filter(([key]) => !seenProfile.has(key))
    .sort((left, right) => {
      const countDelta = right[1].count - left[1].count;
      if (countDelta !== 0) {
        return countDelta;
      }

      return left[1].label.localeCompare(right[1].label);
    })
    .map(([, value]) => ({
      ...value,
      source: "jobs",
    }));

  return [...prioritized, ...remaining].slice(0, maxVisible);
}

export {
  FILTER_GROUPS,
  DEFAULT_SELECTED_EXPERIENCE_LEVELS,
  MAX_VISIBLE_SKILL_OPTIONS,
  arraysEqualAsSets,
  toggleSelectedValue,
  getJobExperienceLevel,
  getJobWorkplace,
  inferRoleType,
  getJobSkills,
  matchesSelectedSkills,
  matchesLocationQuery,
  filterJobs,
  getFilterSummary,
  getActiveFilterTags,
  getAvailableSkillOptions,
};