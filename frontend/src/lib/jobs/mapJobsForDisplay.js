/**
 * Maps raw + scored jobs into UI-ready job cards.
 */

function formatCompensation(comp) {
  if (!comp || comp.salaryVisible === false) return null;

  const { salaryMinUsd, salaryMaxUsd } = comp;

  if (salaryMinUsd && salaryMaxUsd) {
    return `$${salaryMinUsd.toLocaleString()} - $${salaryMaxUsd.toLocaleString()}`;
  }

  if (salaryMinUsd) {
    return `$${salaryMinUsd.toLocaleString()}+`;
  }

  return null;
}

function normalizeScoreBreakdown(breakdown) {
  if (!breakdown) return null;

  return {
    seniorityFit: breakdown.seniorityFit ?? 0,
    skillsFit: breakdown.skillsFit ?? 0,
    accessibilityFit:
      breakdown.accessibilityFit ?? breakdown.accessibility ?? 0,
    trustFit: breakdown.trustFit ?? breakdown.trust ?? 0,
    preferenceFit: breakdown.preferenceFit ?? 0,
  };
}

function resolveLocation(job) {
  if (job.location?.display) return job.location.display;
  if (typeof job.location === "string") return job.location;
  if (job.jobLocation) return job.jobLocation;
  return "Location not listed";
}

function resolveWorkplaceType(job) {
  return job.workplaceType ?? job.location?.workplaceType ?? null;
}

function resolveFitTag(scored) {
  return (
    scored?.bloomVerdict ??
    scored?.fitTag ??
    "Too Senior"
  );
}

function resolveMatchScore(scored) {
  return (
    scored?.bloomFitScore ??
    scored?.matchScore ??
    0
  );
}

function resolveReasons(scored) {
  return (
    scored?.bloomReasons ??
    scored?.reasons ??
    []
  );
}

function resolveWarnings(raw, scored) {
  return scored?.warningFlags ?? raw?.warnings ?? [];
}

export function mapJobsForDisplay(rawJobs = [], scoredJobs = []) {
  const scoredMap = new Map(
    scoredJobs.map((job) => [job.id, job])
  );

  return rawJobs.map((job) => {
    const scored = scoredMap.get(job.id);

    return {
      id: job.id,
      title: job.title ?? "Untitled role",
      company: job.company ?? "Unknown company",
      location: resolveLocation(job),
      workplaceType: resolveWorkplaceType(job),
      employmentType: job.employmentType ?? null,
      roleType: job.roleType ?? null,
      description: job.description ?? "",
      fitTag: resolveFitTag(scored),
      matchScore: resolveMatchScore(scored),
      reasons: resolveReasons(scored),
      warningFlags: resolveWarnings(job, scored),
      scoreBreakdown: normalizeScoreBreakdown(
        scored?.scoreBreakdown
      ),
      confidence: scored?.confidence ?? null,
      compensation: formatCompensation(job.compensation),
      postedAt: job.postedAt ?? null,
      source: job.source ?? null,
      sourceUrl: job.sourceUrl ?? null,
    };
  });
}

export default mapJobsForDisplay;