import React, { memo, useMemo, useCallback } from "react";

/**
 * Returns the modifier class used for the fit tag badge.
 *
 * @param {string} fitTag Fit verdict label.
 * @returns {string} CSS class name.
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
 * Normalizes incoming fit tags into the supported UI set.
 *
 * @param {string} fitTag Raw fit tag.
 * @returns {string} Safe fit tag.
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
 * Normalizes match score into a safe 0-100 integer.
 *
 * @param {number} matchScore Raw match score.
 * @returns {number} Safe score.
 */
function getSafeMatchScore(matchScore) {
  if (!Number.isFinite(matchScore)) {
    return 0;
  }

  return Math.max(0, Math.min(100, Math.round(matchScore)));
}

/**
 * Stops a nested button click from bubbling through the card surface.
 *
 * @param {React.SyntheticEvent} event React event.
 * @returns {void}
 */
function stopCardEvent(event) {
  event.preventDefault();
  event.stopPropagation();
}

/**
 * Returns the quick-take copy shown near the top of the card.
 *
 * @param {object} job Display job.
 * @returns {string} Short quick-take text.
 */
function getQuickTake(job) {
  if (job?.qualificationSignal?.text) {
    return job.qualificationSignal.text;
  }

  if (job.fitTag === "Real Junior") {
    return "Looks realistically junior-friendly.";
  }

  if (job.fitTag === "Stretch Role") {
    return "Possible fit, but double-check requirements.";
  }

  if (job.fitTag === "Misleading Junior") {
    return "Labeled junior, but parts may lean more experienced.";
  }

  return "This may be more experienced than it first appears.";
}

/**
 * Returns a capped list of matched skills for compact card display.
 *
 * @param {string[] | undefined} matchedSkills Matched skills.
 * @returns {string[]} Up to three matched skills.
 */
function getVisibleMatchedSkills(matchedSkills) {
  return Array.isArray(matchedSkills)
    ? matchedSkills.filter(Boolean).slice(0, 3)
    : [];
}

/**
 * EarlyBloom job result card.
 *
 * @param {{
 *   job: object,
 *   onOpenDetails?: (job: object) => void,
 *   onSaveToggle?: (job: object) => void,
 *   onHide?: (job: object) => void,
 *   isSavePending?: boolean,
 *   isHidePending?: boolean,
 *   hideLabel?: string,
 * }} props Card props.
 * @returns {JSX.Element} Job card.
 */
function JobCardComponent({
  job,
  onOpenDetails,
  onSaveToggle,
  onHide,
  isSavePending = false,
  isHidePending = false,
  hideLabel,
}) {
  const id = job.id;

  const title = job.title || "Untitled role";
  const company = job.company || "Unknown company";

  const fitTag = useMemo(() => getSafeFitTag(job.fitTag), [job.fitTag]);
  const fitTagClassName = useMemo(
    () => getFitTagClassName(fitTag),
    [fitTag]
  );
  const matchScore = useMemo(
    () => getSafeMatchScore(job.matchScore),
    [job.matchScore]
  );
  const metaItems = useMemo(
    () => (Array.isArray(job.cardMeta) ? job.cardMeta : []),
    [job.cardMeta]
  );
  const quickTake = useMemo(() => getQuickTake(job), [job]);
  const applyUrl = job.url || job.sourceUrl || null;
  const resolvedHideLabel =
    hideLabel || (job.isHidden ? "Restore job" : "Hide job");
  const visibleMatchedSkills = useMemo(
    () => getVisibleMatchedSkills(job.matchedSkills),
    [job.matchedSkills]
  );

  const handleOpen = useCallback(() => {
    if (typeof onOpenDetails === "function") {
      onOpenDetails(job);
    }
  }, [job, onOpenDetails]);

  const handleSaveClick = useCallback(
    (event) => {
      stopCardEvent(event);

      if (typeof onSaveToggle === "function" && !isSavePending) {
        onSaveToggle(job);
      }
    },
    [job, onSaveToggle, isSavePending]
  );

  const handleHideClick = useCallback(
    (event) => {
      stopCardEvent(event);

      if (typeof onHide === "function" && !isHidePending) {
        onHide(job);
      }
    },
    [job, onHide, isHidePending]
  );

  const handleApplyClick = useCallback((event) => {
    event.stopPropagation();
  }, []);

  return (
    <article
      className="job-card section-card job-card--tracker-ready"
      aria-labelledby={`job-card-title-${id}`}
    >
      <div className="job-card__top-row">
        <div className="job-card__meta-row">
          <span className={`job-card__fit-tag ${fitTagClassName}`}>
            {fitTag}
          </span>

          <span
            className="job-card__match-badge"
            aria-label={`${matchScore} percent match`}
          >
            {matchScore}% match
          </span>

          {job.isSaved ? (
            <span className="job-card__saved-chip">Saved</span>
          ) : null}
        </div>

        <div className="job-card__actions" aria-label="Job actions">
          <button
            type="button"
            className={`job-card__icon-button ${
              job.isSaved ? "job-card__icon-button--active" : ""
            }`}
            onClick={handleSaveClick}
            disabled={isSavePending}
            aria-label={job.isSaved ? "Remove saved job" : "Save job"}
            title={job.isSaved ? "Remove saved job" : "Save job"}
          >
            <span aria-hidden="true">{job.isSaved ? "★" : "☆"}</span>
          </button>

          <button
            type="button"
            className={`job-card__icon-button ${
              job.isHidden ? "job-card__icon-button--danger" : ""
            }`}
            onClick={handleHideClick}
            disabled={isHidePending}
            aria-label={resolvedHideLabel}
            title={resolvedHideLabel}
          >
            <span aria-hidden="true">{job.isHidden ? "↺" : "✕"}</span>
          </button>
        </div>
      </div>

      <button
        type="button"
        className="job-card__surface"
        onClick={handleOpen}
        aria-label={`Open details for ${title} at ${company}`}
      >
        <div className="job-card__content">
          <div className="job-card__heading">
            <h3 id={`job-card-title-${id}`} className="job-card__title">
              {title}
            </h3>

            <p className="job-card__company">{company}</p>
          </div>

          <p className="job-card__quick-take">{quickTake}</p>

          {visibleMatchedSkills.length > 0 ? (
            <div
              className="job-card__matched-skills"
              aria-label="Matched skills"
            >
              <p className="job-card__matched-skills-label">Matched skills</p>

              <div className="job-card__matched-skills-list">
                {visibleMatchedSkills.map((skill) => (
                  <span
                    key={`${id}-matched-skill-${skill}`}
                    className="job-card__matched-skill-chip"
                  >
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          ) : null}

          {metaItems.length > 0 ? (
            <div className="job-card__compact-meta" aria-label="Job metadata">
              {metaItems.map((item, index) => (
                <span key={`${id}-meta-${index}`} className="job-card__tag">
                  {item}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      </button>

      <div className="job-card__footer-row">
        <button
          type="button"
          className="jobs-chip jobs-chip--muted job-card__details-button"
          onClick={handleOpen}
        >
          Quick view
        </button>

        {applyUrl ? (
          <a
            className="button button--primary job-card__apply-button"
            href={applyUrl}
            target="_blank"
            rel="noreferrer"
            onClick={handleApplyClick}
          >
            Apply
          </a>
        ) : (
          <button
            type="button"
            className="button button--primary job-card__apply-button"
            onClick={handleOpen}
          >
            Apply
          </button>
        )}
      </div>
    </article>
  );
}

const JobCard = memo(JobCardComponent);

export default JobCard;