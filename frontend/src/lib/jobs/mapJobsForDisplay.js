/**
 * Maps a scored verdict into the UI tag currently used by JobCard.
 *
 * This keeps the UI vocabulary stable even if scoring terminology evolves.
 *
 * @param {string} bloomVerdict - Verdict returned by the scoring layer.
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
 *   salaryMinUsd: number | null,
 *   salaryMaxUsd: number | null,
 *   salaryVisible: boolean
 * } | undefined} compensation - Raw compensation object.
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
 * Merges raw job data with scoring results into a UI-friendly display shape.
 *
 * The UI should not need to understand backend ingestion details or scoring
 * internals. This utility creates one stable object per job so pages and cards
 * can stay presentational and easy to maintain.
 *
 * @param {Array<Object>} rawJobs - Normalized raw jobs from ingestion/mocks.
 * @param {Array<Object>} scoredJobs - Scored results returned by the scoring layer.
 * @returns {Array<{
 *   id: string,
 *   title: string,
 *   company: string,
 *   location: string,
 *   workplaceType: string,
 *   employmentType: string,
 *   roleType: string,
 *   description: string,
 *   fitTag: "Real Junior" | "Stretch Role" | "Too Senior" | "Misleading Junior",
 *   matchScore: number,
 *   reasons: string[],
 *   warningFlags: string[],
 *   scoreBreakdown: Record<string, number> | null,
 *   confidence: string | null,
 *   compensation: string | null,
 *   postedAt: string | null,
 *   source: string | null,
 *   sourceUrl: string | null
 * }>}
 *   Display-ready jobs for the UI layer.
 */
export function mapJobsForDisplay(rawJobs = [], scoredJobs = []) {
  const scoredJobMap = new Map(
    scoredJobs.map((job) => [job.id, job])
  );

  return rawJobs.map((rawJob) => {
    const scoredJob = scoredJobMap.get(rawJob.id);

    return {
      id: rawJob.id,
      title: rawJob.title,
      company: rawJob.company,
      location: rawJob.location?.display ?? "Location not listed",
      workplaceType: rawJob.workplaceType,
      employmentType: rawJob.employmentType,
      roleType: rawJob.roleType,
      description: rawJob.description,
      fitTag: mapVerdictToFitTag(scoredJob?.bloomVerdict),
      matchScore: scoredJob?.bloomFitScore ?? 0,
      reasons: scoredJob?.bloomReasons ?? [],
      warningFlags: scoredJob?.warningFlags ?? rawJob.warnings ?? [],
      scoreBreakdown: scoredJob?.scoreBreakdown ?? null,
      confidence: scoredJob?.confidence ?? null,
      compensation: formatCompensation(rawJob.compensation),
      postedAt: rawJob.postedAt ?? null,
      source: rawJob.source ?? null,
      sourceUrl: rawJob.sourceUrl ?? null,
    };
  });
}

export default mapJobsForDisplay;