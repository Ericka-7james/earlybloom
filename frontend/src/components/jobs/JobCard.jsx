import React from "react";

/**
 * Returns a semantic class name for the fit tag badge.
 *
 * @param {"Real Junior" | "Stretch Role" | "Too Senior" | "Misleading Junior"} fitTag
 *   - Job fit label.
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
 * @param {string | null} source - Source identifier.
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
 * Renders a single job card.
 *
 * The component accepts a UI-ready job object that has already been transformed
 * from raw job data plus scoring results. This keeps rendering logic focused on
 * presentation rather than data mapping or scoring behavior.
 *
 * @param {{
 *   job: {
 *     id: string,
 *     title: string,
 *     company: string,
 *     location: string,
 *     workplaceType: string,
 *     employmentType?: string,
 *     roleType: string,
 *     description: string,
 *     fitTag: "Real Junior" | "Stretch Role" | "Too Senior" | "Misleading Junior",
 *     matchScore: number,
 *     reasons?: string[],
 *     warningFlags?: string[],
 *     compensation?: string | null,
 *     source?: string | null,
 *     sourceUrl?: string | null
 *   }
 * }} props - Component props.
 * @returns {JSX.Element} Job card.
 */
function JobCard({ job }) {
  const {
    title,
    company,
    location,
    workplaceType,
    employmentType,
    roleType,
    description,
    fitTag,
    matchScore,
    reasons = [],
    warningFlags = [],
    compensation = null,
    source = null,
    sourceUrl = null,
  } = job;

  const sourceLabel = formatSourceLabel(source);

  return (
    <article className="job-card section-card">
      <div className="job-card__top">
        <div className="job-card__heading">
          <div className="job-card__meta-row">
            <span className={`job-card__fit-tag ${getFitTagClassName(fitTag)}`}>
              {fitTag}
            </span>
            <span className="job-card__match-badge">{matchScore}% match</span>
          </div>

          <h3 className="job-card__title">{title}</h3>

          <p className="job-card__company">
            {company}
            <span className="job-card__separator">•</span>
            {location}
          </p>
        </div>
      </div>

      <p className="job-card__description">{description}</p>

      {reasons.length > 0 && (
        <div className="job-card__insights">
          <p className="job-card__insights-label">Why EarlyBloom surfaced this</p>
          <ul className="job-card__reason-list">
            {reasons.map((reason, index) => (
              <li
                key={`${job.id}-reason-${index}`}
                className="job-card__reason-item"
              >
                {reason}
              </li>
            ))}
          </ul>
        </div>
      )}

      {warningFlags.length > 0 && (
        <div className="job-card__warnings" aria-label="Job warning flags">
          <p className="job-card__warnings-label">Watchouts</p>
          <ul className="job-card__warning-list">
            {warningFlags.map((warning, index) => (
              <li
                key={`${job.id}-warning-${index}`}
                className="job-card__warning-item"
              >
                {warning}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="job-card__footer">
        <div className="job-card__tags">
          <span className="job-card__tag">{workplaceType}</span>
          <span className="job-card__tag">{roleType}</span>
          {employmentType ? (
            <span className="job-card__tag">{employmentType}</span>
          ) : null}
          {compensation ? (
            <span className="job-card__tag">{compensation}</span>
          ) : null}
          {sourceLabel ? (
            <span className="job-card__tag">Source: {sourceLabel}</span>
          ) : null}
        </div>

        {sourceUrl ? (
          <a
            href={sourceUrl}
            target="_blank"
            rel="noreferrer"
            className="job-card__action"
          >
            View listing
          </a>
        ) : (
          <button type="button" className="job-card__action">
            View details
          </button>
        )}
      </div>
    </article>
  );
}

export default JobCard;