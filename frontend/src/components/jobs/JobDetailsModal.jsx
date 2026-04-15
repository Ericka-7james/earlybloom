import React, { useMemo, useState } from "react";
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
    return [];
  }

  const trimmed = text.trim();
  if (!trimmed) {
    return [];
  }

  return trimmed
    .split(/\n{2,}/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean);
}

function JobDetailsModal({ job, isOpen, onClose }) {
  const [copyState, setCopyState] = useState("idle");

  const summaryParagraphs = useMemo(() => renderParagraphs(job?.summary), [job]);

  async function handleCopySearchText() {
    const fallbackSearchText = [job?.title, job?.company]
      .filter(Boolean)
      .join(" ")
      .trim();

    const textToCopy = job?.searchQuery || fallbackSearchText;

    if (!textToCopy) {
      return;
    }

    try {
      await navigator.clipboard.writeText(textToCopy);
      setCopyState("copied");

      window.setTimeout(() => {
        setCopyState("idle");
      }, 1800);
    } catch {
      setCopyState("error");

      window.setTimeout(() => {
        setCopyState("idle");
      }, 1800);
    }
  }

  if (!job) {
    return (
      <CommonModal
        isOpen={isOpen}
        title="Job details"
        onClose={onClose}
        size="lg"
        iconImage={BloombugAppIcon}
        iconAlt="EarlyBloom Bloombug icon"
      />
    );
  }

  return (
    <CommonModal
      isOpen={isOpen}
      title="Job details"
      onClose={onClose}
      size="lg"
      iconImage={BloombugAppIcon}
      iconAlt="EarlyBloom Bloombug icon"
    >
      <div className="job-details-modal">
        <section className="job-details-modal__hero">
          <div className="job-details-modal__hero-top">
            <div className="job-details-modal__title-block">
              <div className="job-details-modal__badge-row">
                <span
                  className={`job-details-modal__fit-badge job-details-modal__fit-badge--${getFitTagModifier(
                    job.fitTag
                  )}`}
                >
                  {job.fitSummary || job.fitTag}
                </span>

                <span className="job-details-modal__score-badge">
                  {job.matchScore}% match
                </span>
              </div>

              <h3 className="job-details-modal__title">{job.title}</h3>

              <p className="job-details-modal__company-line">
                {job.company}
                {job.modalLocation ? ` • ${job.modalLocation}` : ""}
              </p>
            </div>
          </div>

          {job.qualificationSignal ? (
            <div
              className={`job-details-modal__quick-take job-details-modal__quick-take--${job.qualificationSignal.tone}`}
            >
              <p className="job-details-modal__quick-take-label">
                {job.qualificationSignal.label}
              </p>
              <p className="job-details-modal__quick-take-text">
                {job.qualificationSignal.text}
              </p>
            </div>
          ) : null}

          {Array.isArray(job.quickFacts) && job.quickFacts.length > 0 ? (
            <div className="job-details-modal__facts-grid">
              {job.quickFacts.map((fact) => (
                <div
                  key={`${job.id}-${fact.label}`}
                  className="job-details-modal__fact-card"
                >
                  <p className="job-details-modal__fact-label">{fact.label}</p>
                  <p className="job-details-modal__fact-value">{fact.value}</p>
                </div>
              ))}
            </div>
          ) : null}
        </section>

        {Array.isArray(job.requirementsSnapshot) &&
        job.requirementsSnapshot.length > 0 ? (
          <section className="job-details-modal__section">
            <div className="job-details-modal__section-heading">
              <h4 className="job-details-modal__section-title">Why it may fit</h4>
              <p className="job-details-modal__section-subtext">
                Fast reasons this role may be worth your time.
              </p>
            </div>

            <ul className="job-details-modal__signal-list">
              {job.requirementsSnapshot.map((reason, index) => (
                <li
                  key={`${job.id}-reason-${index}`}
                  className="job-details-modal__signal-item"
                >
                  {reason}
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {Array.isArray(job.blockersSnapshot) &&
        job.blockersSnapshot.length > 0 ? (
          <section className="job-details-modal__section">
            <div className="job-details-modal__section-heading">
              <h4 className="job-details-modal__section-title">Possible blockers</h4>
              <p className="job-details-modal__section-subtext">
                Things to double-check before applying.
              </p>
            </div>

            <ul className="job-details-modal__signal-list job-details-modal__signal-list--warning">
              {job.blockersSnapshot.map((warning, index) => (
                <li
                  key={`${job.id}-warning-${index}`}
                  className="job-details-modal__signal-item"
                >
                  {warning}
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {job.fullLocation && job.fullLocation !== job.modalLocation ? (
          <section className="job-details-modal__section">
            <div className="job-details-modal__section-heading">
              <h4 className="job-details-modal__section-title">Location details</h4>
            </div>

            <div className="job-details-modal__text-card">
              <p className="jobs-results__text">{job.fullLocation}</p>
            </div>
          </section>
        ) : null}

        {summaryParagraphs.length > 0 ? (
          <section className="job-details-modal__section">
            <div className="job-details-modal__section-heading">
              <h4 className="job-details-modal__section-title">Quick summary</h4>
              <p className="job-details-modal__section-subtext">
                The short version before you jump to the listing.
              </p>
            </div>

            <div className="job-details-modal__text-card">
              {summaryParagraphs.map((paragraph, index) => (
                <p
                  key={`${job.id}-summary-${index}`}
                  className="jobs-results__text"
                >
                  {paragraph}
                </p>
              ))}
            </div>
          </section>
        ) : null}

        <div className="job-details-modal__actions">
          {job.url ? (
            <a
              href={job.url}
              target="_blank"
              rel="noreferrer"
              className="button button--primary"
            >
              View listing
            </a>
          ) : (
            <button
              type="button"
              className="button button--primary"
              onClick={handleCopySearchText}
            >
              {copyState === "copied"
                ? "Copied search text"
                : copyState === "error"
                ? "Copy failed"
                : "Copy search text"}
            </button>
          )}
        </div>
      </div>
    </CommonModal>
  );
}

export default JobDetailsModal;