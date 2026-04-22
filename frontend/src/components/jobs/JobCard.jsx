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
 * Converts unknown values into safe display text.
 *
 * @param {unknown} value Raw value.
 * @param {string} fallback Fallback string.
 * @returns {string} Safe text.
 */
function toDisplayText(value, fallback = "") {
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed || fallback;
  }

  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  if (Array.isArray(value)) {
    const joined = value
      .map((item) => toDisplayText(item, ""))
      .filter(Boolean)
      .join(", ")
      .trim();

    return joined || fallback;
  }

  if (value && typeof value === "object") {
    if (typeof value.name === "string" && value.name.trim()) {
      return value.name.trim();
    }

    if (typeof value.label === "string" && value.label.trim()) {
      return value.label.trim();
    }

    if (typeof value.text === "string" && value.text.trim()) {
      return value.text.trim();
    }

    return fallback;
  }

  return fallback;
}

/**
 * Returns a capped list of matched skills for compact card display.
 *
 * @param {unknown} matchedSkills Matched skills.
 * @returns {string[]} Up to one matched skill.
 */
function getVisibleMatchedSkills(matchedSkills) {
  if (!Array.isArray(matchedSkills)) {
    return [];
  }

  return matchedSkills
    .map((skill) => toDisplayText(skill, ""))
    .filter(Boolean)
    .slice(0, 1);
}

/**
 * Returns visible compact metadata chips.
 *
 * @param {unknown} metaItems Card meta items.
 * @returns {string[]} Visible metadata items.
 */
function getVisibleMetaItems(metaItems) {
  if (!Array.isArray(metaItems)) {
    return [];
  }

  return metaItems
    .map((item) => toDisplayText(item, ""))
    .filter(Boolean)
    .slice(0, 3);
}

/**
 * Returns role recency copy.
 *
 * @param {string[]} metaItems Card meta items.
 * @returns {string | null} Recency label.
 */
function getRecencyLabel(metaItems) {
  if (!Array.isArray(metaItems)) {
    return null;
  }

  return metaItems.find((item) => /ago|today|recent/i.test(String(item))) || null;
}

/**
 * Returns the non-recency metadata tags.
 *
 * @param {string[]} metaItems Card meta items.
 * @returns {string[]} Displayable metadata tags.
 */
function getSecondaryMetaItems(metaItems) {
  if (!Array.isArray(metaItems)) {
    return [];
  }

  return metaItems
    .filter((item) => item && !/ago|today|recent/i.test(String(item)))
    .slice(0, 3);
}

/**
 * Returns a safe job object.
 *
 * @param {object | null | undefined} job Raw job.
 * @returns {object} Safe job object.
 */
function getSafeJob(job) {
  return job && typeof job === "object" && !Array.isArray(job) ? job : {};
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
  const isSaved = Boolean(job?.isSaved);
  const isHidden = Boolean(job?.isHidden);

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
        className={`job-card__icon-button job-card__icon-button--save ${
          isSaved ? "job-card__icon-button--active" : ""
        }`}
        onClick={handleSaveClick}
        disabled={isSavePending}
        aria-label={isSaved ? "Remove saved job" : "Save job"}
        title={isSaved ? "Remove saved job" : "Save job"}
      >
        <span aria-hidden="true">{isSaved ? "♥" : "♡"}</span>
      </button>

      <button
        type="button"
        className={`job-card__icon-button job-card__icon-button--hide ${
          isHidden ? "job-card__icon-button--danger-active" : ""
        }`}
        onClick={handleHideClick}
        disabled={isHidePending}
        aria-label={resolvedHideLabel}
        title={resolvedHideLabel}
      >
        <span aria-hidden="true">⊘</span>
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
  recencyLabel,
  secondaryMetaItems,
  visibleMatchedSkills,
}) {
  return (
    <div className="job-card__content">
      <div className="job-card__heading">
        <div className="job-card__identity">
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
      </div>

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
  const safeJob = getSafeJob(job);

  const rawJobId =
    safeJob.id ??
    safeJob.jobId ??
    safeJob.slug ??
    safeJob.url ??
    "job-card-fallback";

  const jobId = toDisplayText(rawJobId, "job-card-fallback");
  const title = toDisplayText(safeJob.title, "Untitled role");
  const company = toDisplayText(safeJob.company, "Unknown company");

  const fitTag = useMemo(() => getSafeFitTag(safeJob.fitTag), [safeJob.fitTag]);
  const fitTagClassName = useMemo(() => getFitTagClassName(fitTag), [fitTag]);
  const matchScore = useMemo(
    () => getSafeMatchScore(safeJob.matchScore),
    [safeJob.matchScore]
  );

  const metaItems = useMemo(
    () => getVisibleMetaItems(safeJob.cardMeta),
    [safeJob.cardMeta]
  );
  const recencyLabel = useMemo(() => getRecencyLabel(metaItems), [metaItems]);
  const secondaryMetaItems = useMemo(
    () => getSecondaryMetaItems(metaItems),
    [metaItems]
  );

  const applyUrl = toDisplayText(safeJob.url || safeJob.sourceUrl, "");
  const resolvedHideLabel =
    hideLabel || (safeJob.isHidden ? "Restore job" : "Hide job");

  const visibleMatchedSkills = useMemo(
    () => getVisibleMatchedSkills(safeJob.matchedSkills),
    [safeJob.matchedSkills]
  );

  const handleOpen = useCallback(() => {
    if (typeof onOpenDetails === "function") {
      onOpenDetails(safeJob);
    }
  }, [safeJob, onOpenDetails]);

  return (
    <article
      className="job-card section-card job-card--compact-modern"
      aria-labelledby={`job-card-title-${jobId}`}
    >
      <div className="job-card__top-row">
        <JobCardBadges
          fitTag={fitTag}
          fitTagClassName={fitTagClassName}
          matchScore={matchScore}
          isSaved={Boolean(safeJob.isSaved)}
        />

        <JobCardActions
          job={safeJob}
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
          recencyLabel={recencyLabel}
          secondaryMetaItems={secondaryMetaItems}
          visibleMatchedSkills={visibleMatchedSkills}
        />
      </button>

      <JobCardFooter applyUrl={applyUrl || null} onOpenDetails={handleOpen} />
    </article>
  );
}

const JobCard = memo(JobCardComponent);

export default JobCard;