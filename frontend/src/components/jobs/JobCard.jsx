import React from "react";

/**
 * Returns a semantic class name for the fit tag badge.
 *
 * @param {"Real Junior" | "Stretch Role" | "Too Senior" | "Misleading Junior"} fitTag
 *   Job fit label.
 * @returns {string} CSS modifier class.
 */
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

/**
 * Returns a label for the source system.
 *
 * @param {string | null | undefined} source Source identifier.
 * @returns {string | null} Human-readable source label.
 */
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
    default:
      return source || null;
  }
}

/**
 * Returns a safe fit tag for display.
 *
 * @param {string | null | undefined} fitTag Raw fit tag.
 * @returns {"Real Junior" | "Stretch Role" | "Too Senior" | "Misleading Junior"}
 *   Safe fit tag.
 */
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

/**
 * Returns a safe percentage match score.
 *
 * @param {number | null | undefined} matchScore Raw match score.
 * @returns {number} Safe match score clamped between 0 and 100.
 */
function getSafeMatchScore(matchScore) {
  if (!Number.isFinite(matchScore)) {
    return 0;
  }

  return Math.max(0, Math.min(100, Math.round(matchScore)));
}

/**
 * Returns a short safe text preview.
 *
 * @param {string | null | undefined} value Raw text.
 * @param {number} maxLength Max allowed length.
 * @returns {string} Safe preview string.
 */
function getPreviewText(value, maxLength = 140) {
  if (typeof value !== "string") {
    return "";
  }

  const trimmed = value.replace(/\s+/g, " ").trim();
  if (!trimmed) {
    return "";
  }

  if (trimmed.length <= maxLength) {
    return trimmed;
  }

  return `${trimmed.slice(0, maxLength).trimEnd()}...`;
}

/**
 * Builds compact metadata pills for the card.
 *
 * @param {Object} params Metadata candidates.
 * @param {string | null | undefined} params.location
 * @param {string | null | undefined} params.experienceLevel
 * @param {string | null | undefined} params.sourceLabel
 * @returns {string[]} Display-ready compact metadata.
 */
function getCompactMeta({ location, experienceLevel, sourceLabel }) {
  return [location, experienceLevel, sourceLabel ? `Source: ${sourceLabel}` : null]
    .filter((value) => typeof value === "string" && value.trim().length > 0)
    .slice(0, 3);
}

/**
 * Renders a single compact job card.
 *
 * @param {{
 *   job: {
 *     id: string,
 *     title?: string,
 *     company?: string,
 *     location?: string,
 *     experienceLevel?: string | null,
 *     summary?: string | null,
 *     fitTag?: "Real Junior" | "Stretch Role" | "Too Senior" | "Misleading Junior",
 *     matchScore?: number,
 *     reasons?: string[],
 *     warningFlags?: string[],
 *     source?: string | null,
 *     sourceUrl?: string | null
 *   },
 *   onOpenReasonsModal?: (job: Object) => void
 * }} props
 * @returns {JSX.Element} Job card.
 */
function JobCard({ job, onOpenReasonsModal }) {
  const {
    id,
    title = "Untitled role",
    company = "Unknown company",
    location = "Location not listed",
    experienceLevel = "unknown",
    summary = "",
    fitTag,
    matchScore,
    reasons = [],
    warningFlags = [],
    source = null,
  } = job;

  const safeFitTag = getSafeFitTag(fitTag);
  const safeMatchScore = getSafeMatchScore(matchScore);
  const sourceLabel = formatSourceLabel(source);

  const compactMeta = getCompactMeta({
    location,
    experienceLevel,
    sourceLabel,
  });

  const reasonPreview =
    Array.isArray(reasons) && reasons.length > 0 ? getPreviewText(reasons[0], 120) : "";

  const summaryPreview = getPreviewText(summary, 150);
  const hasWarningFlags = Array.isArray(warningFlags) && warningFlags.length > 0;

  const canOpenModal = typeof onOpenReasonsModal === "function";

  const handleOpen = () => {
    if (canOpenModal) {
      onOpenReasonsModal(job);
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
                className={`job-card__fit-tag ${getFitTagClassName(safeFitTag)}`}
              >
                {safeFitTag}
              </span>

              <span
                className="job-card__match-badge"
                aria-label={`${safeMatchScore} percent match`}
              >
                {safeMatchScore}% match
              </span>
            </div>

            <h3 id={`job-card-title-${id}`} className="job-card__title">
              {title}
            </h3>

            <p className="job-card__company">{company}</p>
          </div>

          <span className="job-card__chevron" aria-hidden="true">
            →
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

        {reasonPreview ? (
          <div className="job-card__preview-block">
            <p className="job-card__preview-label">Why</p>
            <p className="job-card__preview-text">{reasonPreview}</p>
          </div>
        ) : null}

        {summaryPreview ? (
          <p className="job-card__summary">{summaryPreview}</p>
        ) : null}

        {hasWarningFlags ? (
          <p className="job-card__watchout">Includes watchouts</p>
        ) : null}
      </button>
    </article>
  );
}

export default JobCard;