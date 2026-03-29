import React, { useMemo, useState } from "react";
import JobCard from "../components/jobs/JobCard.jsx";
import CommonModal from "../components/common/CommonModal.jsx";
import "../styles/components/jobs.css";

import { MOCK_RAW_JOBS } from "../mock/jobs/jobs.raw";
import { MOCK_USER_PROFILE } from "../mock/jobs/jobs.user-profile";

import scoreJobsForUser from "../lib/jobs/scoreJobsForUser";
import mapJobsForDisplay from "../lib/jobs/mapJobsForDisplay";

import BloombugAppIcon from "../assets/bloombug/BloombugAppIcon.png";

/**
 * Defines the currently available filter groups.
 *
 * The UI is intentionally present but non-functional for now.
 * Keeping the structure separate makes it easier to attach state and query params later.
 */
const FILTER_GROUPS = {
  workplace: ["Remote", "Onsite", "Hybrid"],
  roleType: ["Frontend", "Backend", "Full Stack", "Data", "Product"],
};

/**
 * Returns a CSS-safe modifier from the visible fit label.
 *
 * @param {string | null | undefined} fitTag Fit tag label.
 * @returns {string} CSS-safe modifier string.
 */
function getFitTagModifier(fitTag) {
  return String(fitTag || "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "-");
}

/**
 * Renders the jobs discovery page.
 *
 * @returns {JSX.Element} Jobs page UI.
 */
function Jobs() {
  const [activeReasonsJob, setActiveReasonsJob] = useState(null);

  /**
   * Scores raw jobs against the current mock user profile.
   */
  const scoredJobs = useMemo(() => {
    return scoreJobsForUser(MOCK_RAW_JOBS, MOCK_USER_PROFILE);
  }, []);

  /**
   * Maps scored jobs into the display shape consumed by JobCard.
   */
  const jobs = useMemo(() => {
    return mapJobsForDisplay(MOCK_RAW_JOBS, scoredJobs).sort(
      (a, b) => b.matchScore - a.matchScore
    );
  }, [scoredJobs]);

  /**
   * Opens the shared reasons modal for a given job.
   *
   * @param {Object} job Display-ready job.
   * @returns {void}
   */
  function handleOpenReasonsModal(job) {
    setActiveReasonsJob(job);
  }

  /**
   * Closes the shared reasons modal.
   *
   * @returns {void}
   */
  function handleCloseReasonsModal() {
    setActiveReasonsJob(null);
  }

  return (
    <main className="jobs-page">
      <section className="section-pad">
        <div className="container">
          <div className="jobs-hero section-card">
            <div className="jobs-hero__content">
              <span className="eyebrow-pill">EarlyBloom Jobs</span>
              <h1 className="jobs-hero__title">
                Find roles that actually fit where you are.
              </h1>
              <p className="jobs-hero__text">
                We highlight realistic entry-level and junior opportunities so you
                can spend less time decoding vague listings and more time applying
                where it makes sense.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="section-pad jobs-section">
        <div className="container jobs-layout">
          <aside className="jobs-filters section-card" aria-label="Job filters">
            <div className="jobs-filters__header">
              <h2 className="jobs-results__title">Filters</h2>
              <p className="jobs-filters__text">
                UI only for now. Wiring can be added later without reshaping the
                page.
              </p>
            </div>

            <div className="jobs-filter-group">
              <h3 className="jobs-filter-group__title">Workplace</h3>
              <div className="jobs-chip-list">
                {FILTER_GROUPS.workplace.map((option) => (
                  <button
                    key={option}
                    type="button"
                    className="jobs-chip"
                    aria-pressed="false"
                  >
                    {option}
                  </button>
                ))}
              </div>
            </div>

            <div className="jobs-filter-group">
              <h3 className="jobs-filter-group__title">Role Type</h3>
              <div className="jobs-chip-list">
                {FILTER_GROUPS.roleType.map((option) => (
                  <button
                    key={option}
                    type="button"
                    className="jobs-chip"
                    aria-pressed="false"
                  >
                    {option}
                  </button>
                ))}
              </div>
            </div>
          </aside>

          <div className="jobs-results">
            <div className="jobs-results__header">
              <div>
                <h2 className="jobs-results__title">Open roles</h2>
                <p className="jobs-results__text">
                  {jobs.length} roles matched to your profile.
                </p>
              </div>
            </div>

            <div className="jobs-list">
              {jobs.map((job) => (
                <JobCard
                  key={job.id}
                  job={job}
                  onOpenReasonsModal={handleOpenReasonsModal}
                />
              ))}
            </div>
          </div>
        </div>
      </section>

      <CommonModal
        isOpen={Boolean(activeReasonsJob)}
        title="Why EarlyBloom surfaced this"
        onClose={handleCloseReasonsModal}
        size="md"
        iconImage={BloombugAppIcon}
        iconAlt="EarlyBloom Bloombug icon"
      >
        {activeReasonsJob ? (
          <div className="jobs-reasons-modal">
            <div className="jobs-reasons-modal__intro">
              <p className="jobs-reasons-modal__eyebrow">
                <span
                  className={`jobs-reasons-modal__eyebrow-fit jobs-reasons-modal__eyebrow-fit--${getFitTagModifier(
                    activeReasonsJob.fitTag
                  )}`}
                >
                  {activeReasonsJob.fitTag}
                </span>
                {" • "}
                {activeReasonsJob.matchScore}% match
              </p>

              <h3 className="jobs-reasons-modal__job-title">
                {activeReasonsJob.title}
              </h3>

              <p className="jobs-reasons-modal__job-meta">
                {activeReasonsJob.company} • {activeReasonsJob.location}
              </p>
            </div>

            <div className="jobs-reasons-modal__section">
              <p className="jobs-reasons-modal__label">Top reasons</p>
              <ul className="jobs-reasons-modal__list">
                {(activeReasonsJob.reasons || []).map((reason, index) => (
                  <li
                    key={`${activeReasonsJob.id}-modal-reason-${index}`}
                    className="jobs-reasons-modal__list-item"
                  >
                    {reason}
                  </li>
                ))}
              </ul>
            </div>

            {Array.isArray(activeReasonsJob.warningFlags) &&
            activeReasonsJob.warningFlags.length > 0 ? (
              <div className="jobs-reasons-modal__section">
                <p className="jobs-reasons-modal__label">Watchouts</p>
                <ul className="jobs-reasons-modal__list jobs-reasons-modal__list--warning">
                  {activeReasonsJob.warningFlags.map((warning, index) => (
                    <li
                      key={`${activeReasonsJob.id}-modal-warning-${index}`}
                      className="jobs-reasons-modal__list-item"
                    >
                      {warning}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        ) : null}
      </CommonModal>
    </main>
  );
}

export default Jobs;