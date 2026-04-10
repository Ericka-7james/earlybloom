import React from "react";
import CommonModal from "../common/CommonModal.jsx";
import BloombugAppIcon from "../../assets/bloombug/BloombugAppIcon.png";

function getFitTagModifier(fitTag) {
  return String(fitTag || "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "-");
}

function renderParagraphs(text) {
  if (!text || typeof text !== "string") {
    return null;
  }

  const trimmed = text.trim();
  if (!trimmed) {
    return null;
  }

  return trimmed.split(/\n{2,}/).map((paragraph, index) => (
    <p key={`${index}-${paragraph.slice(0, 16)}`} className="jobs-results__text">
      {paragraph.trim()}
    </p>
  ));
}

function JobDetailsModal({ job, isOpen, onClose }) {
  const detailMeta = job
    ? [
        job.experienceLevel,
        job.compensation,
        job.sourceLabel ? `Source: ${job.sourceLabel}` : null,
      ].filter(Boolean)
    : [];

  const shouldShowLocationDetails =
    job?.fullLocation &&
    job?.modalLocation &&
    job.fullLocation !== job.modalLocation;

  return (
    <CommonModal
      isOpen={isOpen}
      title="Job details"
      onClose={onClose}
      size="lg"
      iconImage={BloombugAppIcon}
      iconAlt="EarlyBloom Bloombug icon"
    >
      {job ? (
        <div className="jobs-reasons-modal">
          <div className="jobs-reasons-modal__intro">
            <p className="jobs-reasons-modal__eyebrow">
              <span
                className={`jobs-reasons-modal__eyebrow-fit jobs-reasons-modal__eyebrow-fit--${getFitTagModifier(
                  job.fitTag
                )}`}
              >
                {job.fitTag}
              </span>
              {" • "}
              {job.matchScore}% match
            </p>

            <h3 className="jobs-reasons-modal__job-title">{job.title}</h3>

            <p className="jobs-reasons-modal__job-meta">
              {job.company}
              {job.modalLocation ? ` • ${job.modalLocation}` : ""}
            </p>

            {detailMeta.length > 0 ? (
              <div className="jobs-detail-modal__meta">
                {detailMeta.map((item, index) => (
                  <span key={`${job.id}-detail-meta-${index}`} className="job-card__tag">
                    {item}
                  </span>
                ))}
              </div>
            ) : null}
          </div>

          {Array.isArray(job.reasons) && job.reasons.length > 0 ? (
            <div className="jobs-reasons-modal__section">
              <p className="jobs-reasons-modal__label">Top reasons</p>
              <ul className="jobs-reasons-modal__list">
                {job.reasons.map((reason, index) => (
                  <li
                    key={`${job.id}-modal-reason-${index}`}
                    className="jobs-reasons-modal__list-item"
                  >
                    {reason}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {Array.isArray(job.warningFlags) && job.warningFlags.length > 0 ? (
            <div className="jobs-reasons-modal__section">
              <p className="jobs-reasons-modal__label">Watchouts</p>
              <ul className="jobs-reasons-modal__list jobs-reasons-modal__list--warning">
                {job.warningFlags.map((warning, index) => (
                  <li
                    key={`${job.id}-modal-warning-${index}`}
                    className="jobs-reasons-modal__list-item"
                  >
                    {warning}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {shouldShowLocationDetails ? (
            <div className="jobs-reasons-modal__section">
              <p className="jobs-reasons-modal__label">Location details</p>
              <p className="jobs-results__text">{job.fullLocation}</p>
            </div>
          ) : null}

          {job.summary ? (
            <div className="jobs-reasons-modal__section">
              <p className="jobs-reasons-modal__label">Summary</p>
              <div className="jobs-detail-modal__copy">
                {renderParagraphs(job.summary)}
              </div>
            </div>
          ) : null}

          {job.description ? (
            <div className="jobs-reasons-modal__section">
              <p className="jobs-reasons-modal__label">Description</p>
              <div className="jobs-detail-modal__copy">
                {renderParagraphs(job.description)}
              </div>
            </div>
          ) : null}

          {job.url ? (
            <div className="jobs-detail-modal__actions">
              <a
                href={job.url}
                target="_blank"
                rel="noreferrer"
                className="button button--primary jobs-reasons-modal__listing-link"
              >
                View listing
              </a>
            </div>
          ) : null}
        </div>
      ) : null}
    </CommonModal>
  );
}

export default JobDetailsModal;