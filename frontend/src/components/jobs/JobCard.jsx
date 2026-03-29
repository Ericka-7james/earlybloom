import React from "react";

/**
 * Returns a semantic class name for the fit tag badge.
 *
 * @param {"Real Junior" | "Stretch Role" | "Too Senior"} fitTag - Job fit label.
 * @returns {string} CSS modifier class.
 */
function getFitTagClassName(fitTag) {
  switch (fitTag) {
    case "Real Junior":
      return "job-card__fit-tag--junior";
    case "Stretch Role":
      return "job-card__fit-tag--stretch";
    case "Too Senior":
      return "job-card__fit-tag--senior";
    default:
      return "";
  }
}

/**
 * Renders a single job card.
 *
 * The component accepts a normalized job object and stays presentation-focused.
 * This keeps it reusable when jobs eventually come from FastAPI or another data layer.
 *
 * @param {{
 *   job: {
 *     id: string,
 *     title: string,
 *     company: string,
 *     location: string,
 *     workplaceType: string,
 *     roleType: string,
 *     description: string,
 *     fitTag: "Real Junior" | "Stretch Role" | "Too Senior",
 *     matchScore: number
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
    roleType,
    description,
    fitTag,
    matchScore,
  } = job;

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

      <div className="job-card__footer">
        <div className="job-card__tags">
          <span className="job-card__tag">{workplaceType}</span>
          <span className="job-card__tag">{roleType}</span>
        </div>

        <button type="button" className="job-card__action">
          View details
        </button>
      </div>
    </article>
  );
}

export default JobCard;