/**
 * Maps raw + scored jobs into UI-ready job cards and modal details.
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

function buildCompensation(job) {
  if (job.compensation) {
    return job.compensation;
  }

  const salaryMinUsd = job.salaryMinUsd ?? job.salary_min ?? null;
  const salaryMaxUsd = job.salaryMaxUsd ?? job.salary_max ?? null;
  const currency =
    job.salaryCurrency ?? job.salary_currency ?? job.currency ?? "USD";

  if (!salaryMinUsd && !salaryMaxUsd) {
    return null;
  }

  return {
    salaryMinUsd,
    salaryMaxUsd,
    currency,
    salaryVisible: true,
  };
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

function cleanText(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function resolveLocation(job) {
  if (job.location?.display) return cleanText(job.location.display);
  if (typeof job.location === "string") return cleanText(job.location);
  if (job.jobLocation) return cleanText(job.jobLocation);
  return "";
}

function looksMultiLocation(location) {
  const normalized = cleanText(location).toLowerCase();

  if (!normalized) {
    return false;
  }

  return (
    normalized.includes("location negotiable after selection") ||
    normalized.includes("many vacancies") ||
    normalized.includes("multiple locations") ||
    normalized.includes("few vacancies") ||
    normalized.includes("locations") ||
    normalized.split(";").length >= 3 ||
    normalized.split("|").length >= 3 ||
    normalized.split(", ").length >= 6
  );
}

function formatCardLocation(location, source) {
  const safeLocation = cleanText(location);
  const safeSource = cleanText(source).toLowerCase();

  if (!safeLocation) {
    return "Location not listed";
  }

  if (safeSource === "usajobs" && looksMultiLocation(safeLocation)) {
    return "Multiple U.S. locations";
  }

  if (looksMultiLocation(safeLocation)) {
    return "Multiple locations";
  }

  if (safeLocation.length > 72) {
    return "Location details in modal";
  }

  return safeLocation;
}

function formatModalLocation(location, source) {
  const safeLocation = cleanText(location);
  const safeSource = cleanText(source).toLowerCase();

  if (!safeLocation) {
    return null;
  }

  if (safeSource === "usajobs" && looksMultiLocation(safeLocation)) {
    return "Multiple U.S. locations";
  }

  if (looksMultiLocation(safeLocation)) {
    return "Multiple locations";
  }

  return safeLocation;
}

function resolveWorkplaceType(job) {
  return (
    job.workplaceType ??
    job.workplace_type ??
    job.remoteType ??
    job.remote_type ??
    job.workplace ??
    job.location?.workplaceType ??
    null
  );
}

function resolveEmploymentType(job) {
  return job.employmentType ?? job.employment_type ?? null;
}

function resolveRoleType(job) {
  return job.roleType ?? job.role_type ?? null;
}

function resolveExperienceLevel(job) {
  return job.experienceLevel ?? job.experience_level ?? job.level ?? null;
}

function normalizeExperienceLevel(level) {
  const normalized = cleanText(level).toLowerCase();

  if (!normalized || normalized === "unknown") {
    return null;
  }

  switch (normalized) {
    case "entry":
    case "entry-level":
      return "Entry-level";
    case "junior":
      return "Junior";
    case "mid":
    case "mid-level":
      return "Mid-level";
    case "senior":
      return "Senior";
    default:
      return level || null;
  }
}

function resolveFitTag(scored) {
  return scored?.bloomVerdict ?? scored?.fitTag ?? "Too Senior";
}

function resolveMatchScore(scored) {
  return scored?.bloomFitScore ?? scored?.matchScore ?? 0;
}

function resolveReasons(scored) {
  return scored?.bloomReasons ?? scored?.reasons ?? [];
}

function resolveWarnings(raw, scored) {
  return scored?.warningFlags ?? raw?.warnings ?? [];
}

function resolveCompany(job) {
  return job.company ?? job.company_name ?? "Unknown company";
}

function resolvePostedAt(job) {
  return job.postedAt ?? job.posted_at ?? null;
}

function resolveSourceUrl(job) {
  return job.sourceUrl ?? job.source_url ?? job.url ?? job.apply_url ?? null;
}

function resolveSummary(job) {
  return job.summary ?? job.short_summary ?? "";
}

function resolveRemote(job) {
  if (typeof job.remote === "boolean") {
    return job.remote;
  }

  const remoteType = resolveWorkplaceType(job);
  return remoteType === "remote";
}

function formatSourceLabel(source) {
  switch (source) {
    case "greenhouse":
      return "Greenhouse";
    case "lever":
      return "Lever";
    case "adzuna":
      return "Adzuna";
    case "usajobs":
      return "USAJobs";
    case "remoteok":
      return "RemoteOK";
    case "jobicy":
      return "Jobicy";
    case "arbeitnow":
      return "ArbeitNow";
    default:
      return source || null;
  }
}

export function mapJobsForDisplay(rawJobs = [], scoredJobs = []) {
  const scoredMap = new Map(scoredJobs.map((job) => [job.id, job]));

  return rawJobs.map((job) => {
    const scored = scoredMap.get(job.id);
    const compensation = buildCompensation(job);
    const sourceUrl = resolveSourceUrl(job);
    const source = job.source ?? job.source_name ?? null;
    const fullLocation = resolveLocation(job);
    const modalLocation = formatModalLocation(fullLocation, source);

    return {
      id: job.id,
      title: job.title ?? "Untitled role",
      company: resolveCompany(job),
      location: fullLocation || "Location not listed",
      cardLocation: formatCardLocation(fullLocation, source),
      modalLocation,
      fullLocation,
      workplaceType: resolveWorkplaceType(job),
      remoteType: resolveWorkplaceType(job),
      remote: resolveRemote(job),
      employmentType: resolveEmploymentType(job),
      roleType: resolveRoleType(job),
      experienceLevel: normalizeExperienceLevel(resolveExperienceLevel(job)),
      description: job.description ?? "",
      summary: resolveSummary(job),
      fitTag: resolveFitTag(scored),
      matchScore: resolveMatchScore(scored),
      reasons: resolveReasons(scored),
      warningFlags: resolveWarnings(job, scored),
      scoreBreakdown: normalizeScoreBreakdown(scored?.scoreBreakdown),
      confidence: scored?.confidence ?? null,
      compensation: formatCompensation(compensation),
      postedAt: resolvePostedAt(job),
      source,
      sourceLabel: formatSourceLabel(source),
      sourceUrl,
      url: sourceUrl,
    };
  });
}

export default mapJobsForDisplay;