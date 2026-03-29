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
 * Returns non-empty tag values for rendering in the footer.
 *
 * @param {Object} params Tag candidates.
 * @param {string | null | undefined} params.workplaceType Workplace type.
 * @param {string | null | undefined} params.roleType Role type.
 * @param {string | null | undefined} params.employmentType Employment type.
 * @param {string | null | undefined} params.compensation Compensation label.
 * @param {string | null | undefined} params.sourceLabel Source label.
 * @returns {string[]} Display-ready tag labels.
 */
function getFooterTags({
  workplaceType,
  roleType,
  employmentType,
  compensation,
  sourceLabel,
}) {
  return [
    workplaceType,
    roleType,
    employmentType,
    compensation,
    sourceLabel ? `Source: ${sourceLabel}` : null,
  ].filter((value) => typeof value === "string" && value.trim().length > 0);
}

/**
 * Renders a single job card.
 *
 * The component accepts a UI-ready job object that has already been transformed
 * from raw job data plus scoring results. This keeps rendering logic focused on
 * presentation rather than data mapping or scoring behavior.
 *
 * @param {{
 *   job: {
 *     id: string,
 *     title?: string,
 *     company?: string,
 *     location?: string,
 *     workplaceType?: string | null,
 *     employmentType?: string | null,
 *     roleType?: string | null,
 *     description?: string,
 *     fitTag?: "Real Junior" | "Stretch Role" | "Too Senior" | "Misleading Junior",
 *     matchScore?: number,
 *     reasons?: string[],
 *     warningFlags?: string[],
 *     compensation?: string | null,
 *     source?: string | null,
 *     sourceUrl?: string | null
 *   }
 * }} props Component props.
 * @returns {JSX.Element} Job card.
 */
function JobCard({ job }) {
  const {
    id,
    title = "Untitled role",
    company = "Unknown company",
    location = "Location not listed",
    workplaceType = null,
    employmentType = null,
    roleType = null,
    description = "",
    fitTag,
    matchScore,
    reasons = [],
    warningFlags = [],
    compensation = null,
    source = null,
    sourceUrl = null,
  } = job;

  const safeFitTag = getSafeFitTag(fitTag);
  const safeMatchScore = getSafeMatchScore(matchScore);
  const sourceLabel = formatSourceLabel(source);

  const footerTags = getFooterTags({
    workplaceType,
    roleType,
    employmentType,
    compensation,
    sourceLabel,
  });

  const hasReasons = Array.isArray(reasons) && reasons.length > 0;
  const hasWarningFlags = Array.isArray(warningFlags) && warningFlags.length > 0;
  const hasDescription = typeof description === "string" && description.trim().length > 0;

  return (
    <article
      className="job-card section-card"
      aria-labelledby={`job-card-title-${id}`}
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

          <p className="job-card__company">
            <span>{company}</span>
            <span className="job-card__separator" aria-hidden="true">
              •
            </span>
            <span>{location}</span>
          </p>
        </div>
      </div>

      {hasDescription ? (
        <p className="job-card__description">{description}</p>
      ) : null}

      {hasReasons ? (
        <section
          className="job-card__insights"
          aria-labelledby={`job-card-insights-${id}`}
        >
          <p id={`job-card-insights-${id}`} className="job-card__insights-label">
            Why EarlyBloom surfaced this
          </p>
          <ul className="job-card__reason-list">
            {reasons.map((reason, index) => (
              <li key={`${id}-reason-${index}`} className="job-card__reason-item">
                {reason}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {hasWarningFlags ? (
        <section
          className="job-card__warnings"
          aria-labelledby={`job-card-warnings-${id}`}
        >
          <p id={`job-card-warnings-${id}`} className="job-card__warnings-label">
            Watchouts
          </p>
          <ul className="job-card__warning-list">
            {warningFlags.map((warning, index) => (
              <li key={`${id}-warning-${index}`} className="job-card__warning-item">
                {warning}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <div className="job-card__footer">
        {footerTags.length > 0 ? (
          <div className="job-card__tags" aria-label="Job details">
            {footerTags.map((tag, index) => (
              <span key={`${id}-tag-${index}`} className="job-card__tag">
                {tag}
              </span>
            ))}
          </div>
        ) : (
          <div className="job-card__tags" aria-hidden="true" />
        )}

        {sourceUrl ? (
          <a
            href={sourceUrl}
            target="_blank"
            rel="noreferrer"
            className="job-card__action"
            aria-label={`View listing for ${title} at ${company}`}
          >
            View listing
          </a>
        ) : (
          <button
            type="button"
            className="job-card__action"
            aria-label={`View details for ${title} at ${company}`}
          >
            View details
          </button>
        )}
      </div>
    </article>
  );
}

export default JobCard;