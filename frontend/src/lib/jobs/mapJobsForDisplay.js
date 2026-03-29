/**
 * @fileoverview Maps raw job data and scoring output into a stable UI shape.
 *
 * This utility keeps the Jobs page and JobCard presentational by translating
 * raw ingestion fields and scoring-layer output into one display-ready object
 * per job. It is intentionally UI-facing and should not contain scoring logic.
 */

/**
 * Maps a scored verdict into the UI tag currently used by JobCard.
 *
 * This keeps the UI vocabulary stable even if scoring terminology evolves.
 *
 * @param {string | undefined | null} bloomVerdict Verdict returned by scoring.
 * @returns {"Real Junior" | "Stretch Role" | "Too Senior" | "Misleading Junior"}
 *   Display-ready fit tag.
 */
function mapVerdictToFitTag(bloomVerdict) {
  switch (bloomVerdict) {
    case "Real Junior":
      return "Real Junior";
    case "Stretch Role":
      return "Stretch Role";
    case "Misleading Junior":
      return "Misleading Junior";
    case "Too Senior":
    default:
      return "Too Senior";
  }
}

/**
 * Converts structured compensation data into a compact display string.
 *
 * @param {{
 *   salaryMinUsd?: number | null,
 *   salaryMaxUsd?: number | null,
 *   salaryVisible?: boolean
 * } | undefined | null} compensation Raw compensation object.
 * @returns {string | null} Human-readable compensation label.
 */
function formatCompensation(compensation) {
  if (!compensation || !compensation.salaryVisible) {
    return null;
  }

  const { salaryMinUsd, salaryMaxUsd } = compensation;

  if (typeof salaryMinUsd === "number" && typeof salaryMaxUsd === "number") {
    return `$${salaryMinUsd.toLocaleString()} - $${salaryMaxUsd.toLocaleString()}`;
  }

  if (typeof salaryMinUsd === "number") {
    return `$${salaryMinUsd.toLocaleString()}+`;
  }

  return null;
}

/**
 * Returns a display-safe location string.
 *
 * @param {Object} rawJob Raw job object.
 * @returns {string} Display-ready location label.
 */
function getDisplayLocation(rawJob) {
  if (typeof rawJob?.location?.display === "string" && rawJob.location.display.trim()) {
    return rawJob.location.display;
  }

  if (typeof rawJob?.location === "string" && rawJob.location.trim()) {
    return rawJob.location;
  }

  if (typeof rawJob?.jobLocation === "string" && rawJob.jobLocation.trim()) {
    return rawJob.jobLocation;
  }

  return "Location not listed";
}

/**
 * Returns a display-safe workplace type.
 *
 * @param {Object} rawJob Raw job object.
 * @returns {string | null} Workplace type label.
 */
function getDisplayWorkplaceType(rawJob) {
  if (typeof rawJob?.workplaceType === "string" && rawJob.workplaceType.trim()) {
    return rawJob.workplaceType;
  }

  if (typeof rawJob?.location?.workplaceType === "string" && rawJob.location.workplaceType.trim()) {
    return rawJob.location.workplaceType;
  }

  return null;
}

/**
 * Normalizes score breakdown keys for the UI layer.
 *
 * This bridges older mock naming and newer scoring utility naming so display
 * components do not need to care about scoring schema transitions.
 *
 * @param {Object | null | undefined} scoreBreakdown Raw score breakdown.
 * @returns {{
 *   seniorityFit: number,
 *   skillsFit: number,
 *   accessibilityFit: number,
 *   trustFit: number,
 *   preferenceFit: number
 * } | null} UI-normalized breakdown.
 */
function normalizeScoreBreakdown(scoreBreakdown) {
  if (!scoreBreakdown || typeof scoreBreakdown !== "object") {
    return null;
  }

  return {
    seniorityFit: scoreBreakdown.seniorityFit ?? 0,
    skillsFit: scoreBreakdown.skillsFit ?? 0,
    accessibilityFit:
      scoreBreakdown.accessibilityFit ?? scoreBreakdown.accessibility ?? 0,
    trustFit: scoreBreakdown.trustFit ?? scoreBreakdown.trust ?? 0,
    preferenceFit: scoreBreakdown.preferenceFit ?? 0,
  };
}

/**
 * Returns display-safe reasons from scored job data.
 *
 * @param {Object | undefined} scoredJob Scored job object.
 * @returns {string[]} Display reasons.
 */
function getDisplayReasons(scoredJob) {
  if (Array.isArray(scoredJob?.bloomReasons)) {
    return scoredJob.bloomReasons;
  }

  if (Array.isArray(scoredJob?.reasons)) {
    return scoredJob.reasons;
  }

  return [];
}

/**
 * Returns a display-safe fit score from scored job data.
 *
 * @param {Object | undefined} scoredJob Scored job object.
 * @returns {number} Display score.
 */
function getDisplayMatchScore(scoredJob) {
  if (typeof scoredJob?.bloomFitScore === "number") {
    return scoredJob.bloomFitScore;
  }

  if (typeof scoredJob?.matchScore === "number") {
    return scoredJob.matchScore;
  }

  return 0;
}

/**
 * Merges raw job data with scoring results into a UI-friendly display shape.
 *
 * The UI should not need to understand backend ingestion details or scoring
 * internals. This utility creates one stable object per job so pages and cards
 * can stay presentational and easy to maintain.
 *
 * @param {Array<Object>} rawJobs Normalized raw jobs from ingestion or mocks.
 * @param {Array<Object>} scoredJobs Scored results returned by the scoring layer.
 * @returns {Array<{
 *   id: string,
 *   title: string,
 *   company: string,
 *   location: string,
 *   workplaceType: string | null,
 *   employmentType: string | null,
 *   roleType: string | null,
 *   description: string,
 *   fitTag: "Real Junior" | "Stretch Role" | "Too Senior" | "Misleading Junior",
 *   matchScore: number,
 *   reasons: string[],
 *   warningFlags: string[],
 *   scoreBreakdown: {
 *     seniorityFit: number,
 *     skillsFit: number,
 *     accessibilityFit: number,
 *     trustFit: number,
 *     preferenceFit: number
 *   } | null,
 *   confidence: string | null,
 *   compensation: string | null,
 *   postedAt: string | null,
 *   source: string | null,
 *   sourceUrl: string | null
 * }>}
 *   Display-ready jobs for the UI layer.
 */
export function mapJobsForDisplay(rawJobs = [], scoredJobs = []) {
  const scoredJobMap = new Map(scoredJobs.map((job) => [job.id, job]));

  return rawJobs.map((rawJob) => {
    const scoredJob = scoredJobMap.get(rawJob.id);

    return {
      id: rawJob.id,
      title: rawJob.title ?? "Untitled role",
      company: rawJob.company ?? "Unknown company",
      location: getDisplayLocation(rawJob),
      workplaceType: getDisplayWorkplaceType(rawJob),
      employmentType: rawJob.employmentType ?? null,
      roleType: rawJob.roleType ?? null,
      description: rawJob.description ?? "",
      fitTag: mapVerdictToFitTag(scoredJob?.bloomVerdict ?? scoredJob?.fitTag),
      matchScore: getDisplayMatchScore(scoredJob),
      reasons: getDisplayReasons(scoredJob),
      warningFlags: Array.isArray(scoredJob?.warningFlags)
        ? scoredJob.warningFlags
        : Array.isArray(rawJob?.warnings)
        ? rawJob.warnings
        : [],
      scoreBreakdown: normalizeScoreBreakdown(scoredJob?.scoreBreakdown),
      confidence: scoredJob?.confidence ?? null,
      compensation: formatCompensation(rawJob.compensation),
      postedAt: rawJob.postedAt ?? null,
      source: rawJob.source ?? null,
      sourceUrl: rawJob.sourceUrl ?? null,
    };
  });
}

export default mapJobsForDisplay;