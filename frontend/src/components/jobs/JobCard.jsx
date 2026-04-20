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
 * Returns visible compact metadata chips.
 *
 * @param {Array<string>} metaItems Card meta items.
 * @returns {Array<string>} Visible metadata items.
 */
function getVisibleMetaItems(metaItems) {
  return Array.isArray(metaItems) ? metaItems.slice(0, 3) : [];
}

/**
 * Returns role recency copy.
 *
 * @param {Array<string>} metaItems Card meta items.
 * @returns {string | null} Recency label.
 */
function getRecencyLabel(metaItems) {
  if (!Array.isArray(metaItems)) {
    return null;
  }

  return (
    metaItems.find((item) => /ago|today|recent/i.test(item)) || null
  );
}

/**
 * Returns the non-recency metadata tags.
 *
 * @param {Array<string>} metaItems Card meta items.
 * @returns {Array<string>} Displayable metadata tags.
 */
function getSecondaryMetaItems(metaItems) {
  if (!Array.isArray(metaItems)) {
    return [];
  }

  return metaItems.filter((item) => !/ago|today|recent/i.test(item)).slice(0, 3);
}

/**
 * Renders the action buttons in the card header.
 *
 * @param {object} props Component props.
 * @returns {JSX.Element} Action UI.
 */
function JobCardActions({
  job,
  isSavePending,
  isHidePending,
  onSaveToggle,
  onHide,
  resolvedHideLabel,
}) {
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

  return (
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
  );
}

/**
 * Renders the top badge strip for a job card.
 *
 * @param {object} props Component props.
 * @returns {JSX.Element} Badge UI.
 */
function JobCardBadges({ fitTag, fitTagClassName, matchScore, isSaved }) {
  return (
    <div className="job-card__meta-row">
      <span className={`job-card__fit-tag ${fitTagClassName}`}>{fitTag}</span>

      <span
        className="job-card__match-badge"
        aria-label={`${matchScore} percent match`}
      >
        {matchScore}% match
      </span>

      {isSaved ? <span className="job-card__saved-chip">Saved</span> : null}
    </div>
  );
}

/**
 * Renders the main body content of a job card.
 *
 * @param {object} props Component props.
 * @returns {JSX.Element} Content UI.
 */
function JobCardBody({
  jobId,
  title,
  company,
  quickTake,
  recencyLabel,
  secondaryMetaItems,
  visibleMatchedSkills,
}) {
  return (
    <div className="job-card__content">
      <div className="job-card__heading">
        <h3 id={`job-card-title-${jobId}`} className="job-card__title">
          {title}
        </h3>

        <p className="job-card__company">{company}</p>
      </div>

      {recencyLabel ? (
        <div className="job-card__signal-row">
          <span className="job-card__signal-chip">{recencyLabel}</span>
        </div>
      ) : null}

      <p className="job-card__quick-take">{quickTake}</p>

      {visibleMatchedSkills.length > 0 ? (
        <div className="job-card__matched-skills" aria-label="Matched skills">
          <p className="job-card__matched-skills-label">Matched skills</p>

          <div className="job-card__matched-skills-list">
            {visibleMatchedSkills.map((skill) => (
              <span
                key={`${jobId}-matched-skill-${skill}`}
                className="job-card__matched-skill-chip"
              >
                {skill}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      {secondaryMetaItems.length > 0 ? (
        <div className="job-card__compact-meta" aria-label="Job metadata">
          {secondaryMetaItems.map((item, index) => (
            <span key={`${jobId}-meta-${index}`} className="job-card__tag">
              {item}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}

/**
 * Renders the footer actions for a job card.
 *
 * @param {object} props Component props.
 * @returns {JSX.Element} Footer UI.
 */
function JobCardFooter({ applyUrl, onOpenDetails }) {
  const handleApplyClick = useCallback((event) => {
    event.stopPropagation();
  }, []);

  return (
    <div className="job-card__footer-row">
      <button
        type="button"
        className="jobs-chip jobs-chip--muted job-card__details-button"
        onClick={onOpenDetails}
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
          onClick={onOpenDetails}
        >
          Apply
        </button>
      )}
    </div>
  );
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
  const jobId = job.id;
  const title = job.title || "Untitled role";
  const company = job.company || "Unknown company";
  const fitTag = useMemo(() => getSafeFitTag(job.fitTag), [job.fitTag]);
  const fitTagClassName = useMemo(() => getFitTagClassName(fitTag), [fitTag]);
  const matchScore = useMemo(
    () => getSafeMatchScore(job.matchScore),
    [job.matchScore]
  );

  const metaItems = useMemo(
    () => getVisibleMetaItems(job.cardMeta),
    [job.cardMeta]
  );
  const recencyLabel = useMemo(() => getRecencyLabel(metaItems), [metaItems]);
  const secondaryMetaItems = useMemo(
    () => getSecondaryMetaItems(metaItems),
    [metaItems]
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

  return (
    <article
      className="job-card section-card job-card--tracker-ready"
      aria-labelledby={`job-card-title-${jobId}`}
    >
      <div className="job-card__top-row">
        <JobCardBadges
          fitTag={fitTag}
          fitTagClassName={fitTagClassName}
          matchScore={matchScore}
          isSaved={job.isSaved}
        />

        <JobCardActions
          job={job}
          isSavePending={isSavePending}
          isHidePending={isHidePending}
          onSaveToggle={onSaveToggle}
          onHide={onHide}
          resolvedHideLabel={resolvedHideLabel}
        />
      </div>

      <button
        type="button"
        className="job-card__surface"
        onClick={handleOpen}
        aria-label={`Open details for ${title} at ${company}`}
      >
        <JobCardBody
          jobId={jobId}
          title={title}
          company={company}
          quickTake={quickTake}
          recencyLabel={recencyLabel}
          secondaryMetaItems={secondaryMetaItems}
          visibleMatchedSkills={visibleMatchedSkills}
        />
      </button>

      <JobCardFooter applyUrl={applyUrl} onOpenDetails={handleOpen} />
    </article>
  );
}

const JobCard = memo(JobCardComponent);

export default JobCard;