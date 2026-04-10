import React from "react";

function getFitTagClassName(fitTag) {
  switch (fitTag) {
    case "Real Junior":
      return "job-card__fit-tag--junior";
    case "Stretch Role":
      return "job-card__fit-tag--stretch";
    case "Misleading Junior":
      return "job-card__fit-tag--misleading";
    case "Too Senior":
    default:
      return "job-card__fit-tag--senior";
  }
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

function getSafeFitTag(fitTag) {
  switch (fitTag) {
    case "Real Junior":
    case "Stretch Role":
    case "Too Senior":
    case "Misleading Junior":
      return fitTag;
    default:
      return "Too Senior";
  }
}

function getSafeMatchScore(matchScore) {
  if (!Number.isFinite(matchScore)) {
    return 0;
  }

  return Math.max(0, Math.min(100, Math.round(matchScore)));
}

function formatExperienceLevel(experienceLevel) {
  const normalized = String(experienceLevel || "")
    .trim()
    .toLowerCase();

  switch (normalized) {
    case "entry-level":
      return "Entry-level";
    case "junior":
      return "Junior";
    case "mid":
    case "mid-level":
      return "Mid-level";
    case "senior":
      return "Senior";
    case "unknown":
    case "":
      return null;
    default:
      return experienceLevel || null;
  }
}

function getCompactMeta({ location, experienceLevel, compensation, sourceLabel }) {
  return [location, formatExperienceLevel(experienceLevel), compensation, sourceLabel]
    .filter((value) => typeof value === "string" && value.trim().length > 0)
    .slice(0, 4);
}

function JobCard({ job, onOpenDetails }) {
  const id = job.id;
  const title = job.title || "Untitled role";
  const company = job.company || "Unknown company";
  const fitTag = getSafeFitTag(job.fitTag);
  const matchScore = getSafeMatchScore(job.matchScore);
  const sourceLabel = formatSourceLabel(job.source)
    ? `Source: ${formatSourceLabel(job.source)}`
    : null;

  const compactMeta = getCompactMeta({
    location: job.cardLocation || job.location || "Location not listed",
    experienceLevel: job.experienceLevel,
    compensation: job.compensation,
    sourceLabel,
  });

  const hasWarningFlags =
    Array.isArray(job.warningFlags) && job.warningFlags.length > 0;

  const handleOpen = () => {
    if (typeof onOpenDetails === "function") {
      onOpenDetails(job);
    }
  };

  return (
    <article
      className="job-card section-card job-card--compact"
      aria-labelledby={`job-card-title-${id}`}
    >
      <button
        type="button"
        className="job-card__surface"
        onClick={handleOpen}
        aria-label={`Open details for ${title} at ${company}`}
      >
        <div className="job-card__top">
          <div className="job-card__heading">
            <div className="job-card__meta-row">
              <span
                className={`job-card__fit-tag ${getFitTagClassName(fitTag)}`}
              >
                {fitTag}
              </span>

              <span
                className="job-card__match-badge"
                aria-label={`${matchScore} percent match`}
              >
                {matchScore}% match
              </span>

              {hasWarningFlags ? (
                <span className="job-card__watchout-chip">Watchouts</span>
              ) : null}
            </div>

            <h3 id={`job-card-title-${id}`} className="job-card__title">
              {title}
            </h3>

            <p className="job-card__company">{company}</p>
          </div>

          <span className="job-card__details-link" aria-hidden="true">
            View details
          </span>
        </div>

        {compactMeta.length > 0 ? (
          <div className="job-card__compact-meta" aria-label="Job metadata">
            {compactMeta.map((item, index) => (
              <span key={`${id}-meta-${index}`} className="job-card__tag">
                {item}
              </span>
            ))}
          </div>
        ) : null}
      </button>
    </article>
  );
}

export default JobCard;