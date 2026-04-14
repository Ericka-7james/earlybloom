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

function stopCardEvent(event) {
  event.preventDefault();
  event.stopPropagation();
}

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

function JobCard({
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
  const fitTag = getSafeFitTag(job.fitTag);
  const matchScore = getSafeMatchScore(job.matchScore);
  const metaItems = Array.isArray(job.cardMeta) ? job.cardMeta : [];
  const quickTake = getQuickTake(job);
  const applyUrl = job.url || job.sourceUrl || null;
  const resolvedHideLabel = hideLabel || (job.isHidden ? "Restore job" : "Hide job");

  function handleOpen() {
    if (typeof onOpenDetails === "function") {
      onOpenDetails(job);
    }
  }

  function handleSaveClick(event) {
    stopCardEvent(event);

    if (typeof onSaveToggle === "function" && !isSavePending) {
      onSaveToggle(job);
    }
  }

  function handleHideClick(event) {
    stopCardEvent(event);

    if (typeof onHide === "function" && !isHidePending) {
      onHide(job);
    }
  }

  return (
    <article
      className="job-card section-card job-card--tracker-ready"
      aria-labelledby={`job-card-title-${id}`}
    >
      <div className="job-card__top-row">
        <div className="job-card__meta-row">
          <span className={`job-card__fit-tag ${getFitTagClassName(fitTag)}`}>
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
            onClick={(event) => event.stopPropagation()}
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

export default JobCard;