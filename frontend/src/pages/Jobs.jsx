import React, { useMemo, useState } from "react";
import JobCard from "../components/jobs/JobCard.jsx";
import ResumeUploadModal from "../components/jobs/ResumeUploadModal.jsx";
import CommonModal from "../components/common/CommonModal.jsx";
import "../styles/components/jobs.css";

import { MOCK_USER_PROFILE } from "../mock/jobs/jobs.user-profile";

import scoreJobsForUser from "../lib/jobs/scoreJobsForUser";
import mapJobsForDisplay from "../lib/jobs/mapJobsForDisplay";
import { readCachedResumeUiState } from "../lib/resumes";
import { useJobs } from "../hooks/useJobs";

import BloombugAppIcon from "../assets/bloombug/BloombugAppIcon.png";

const FILTER_GROUPS = {
  workplace: ["Remote", "Onsite", "Hybrid"],
  roleType: ["Frontend", "Backend", "Full Stack", "Data", "Product"],
};

const RESUME_MODAL_DISMISSED_KEY = "earlybloom_resume_modal_dismissed";
const WELCOME_MODAL_PENDING_KEY = "earlybloom_welcome_modal_pending";

function getFitTagModifier(fitTag) {
  return String(fitTag || "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "-");
}

function Jobs() {
  const [activeReasonsJob, setActiveReasonsJob] = useState(null);
  const [isFiltersModalOpen, setIsFiltersModalOpen] = useState(false);
  const [resumeFile, setResumeFile] = useState(() => readCachedResumeUiState());

  const hasUploadedResume = false;
  const hasCachedResume = Boolean(readCachedResumeUiState());
  const wasDismissed =
    window.sessionStorage.getItem(RESUME_MODAL_DISMISSED_KEY) === "true";
  const welcomePending =
    window.sessionStorage.getItem(WELCOME_MODAL_PENDING_KEY) === "true";

  const [isWelcomeModalOpen, setIsWelcomeModalOpen] = useState(
    welcomePending && !hasCachedResume && !hasUploadedResume
  );

  const { jobs: rawJobs, isLoading, error, isMockMode, retry } = useJobs();

  const hasResumeCachedNow = Boolean(resumeFile);

  const [isResumeModalOpen, setIsResumeModalOpen] = useState(
    !hasResumeCachedNow && !hasUploadedResume && !wasDismissed
  );

  const scoredJobs = useMemo(() => {
    return scoreJobsForUser(rawJobs, MOCK_USER_PROFILE);
  }, [rawJobs]);

  const jobs = useMemo(() => {
    return mapJobsForDisplay(rawJobs, scoredJobs).sort(
      (a, b) => b.matchScore - a.matchScore
    );
  }, [rawJobs, scoredJobs]);

  function handleOpenReasonsModal(job) {
    setActiveReasonsJob(job);
  }

  function handleCloseReasonsModal() {
    setActiveReasonsJob(null);
  }

  function handleCloseResumeModal() {
    setIsResumeModalOpen(false);
    window.sessionStorage.setItem(RESUME_MODAL_DISMISSED_KEY, "true");
  }

  function handleResumeSaved(savedResumeUiState) {
    setResumeFile(savedResumeUiState);
    setIsResumeModalOpen(false);
    setIsWelcomeModalOpen(false);
    window.sessionStorage.removeItem(WELCOME_MODAL_PENDING_KEY);
  }

  function handleCloseWelcomeModal() {
    setIsWelcomeModalOpen(false);
    window.sessionStorage.removeItem(WELCOME_MODAL_PENDING_KEY);
  }

  function handleOpenResumeFromWelcome() {
    setIsWelcomeModalOpen(false);
    setIsResumeModalOpen(true);
    window.sessionStorage.removeItem(WELCOME_MODAL_PENDING_KEY);
  }

  function renderFiltersContent() {
    return (
      <>
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
      </>
    );
  }

  return (
    <main className="jobs-page">
      <section className="section-pad">
        <div className="container">
          <div className="jobs-hero section-card jobs-hero--with-upload">
            <div className="jobs-hero__content">
              <span className="eyebrow-pill">EarlyBloom Jobs</span>
              <h1 className="jobs-hero__title">
                Find roles that actually fit where you are.
              </h1>
              <p className="jobs-hero__text">
                We highlight realistic opportunities so you can spend less time
                decoding cluttered listings and more time applying where it
                makes sense.
              </p>

              {isMockMode ? (
                <p className="jobs-hero__text" style={{ marginTop: "0.75rem" }}>
                  Using mock mode right now.
                </p>
              ) : null}
            </div>

            <button
              type="button"
              className="jobs-hero__upload"
              onClick={() => setIsResumeModalOpen(true)}
            >
              <div className="jobs-hero__upload-box">
                <p className="jobs-hero__upload-title">
                  {resumeFile ? "Resume uploaded" : "Upload your resume"}
                </p>
                <p className="jobs-hero__upload-subtext">
                  {resumeFile ? resumeFile.name : "PDF only • click to upload"}
                </p>
              </div>
            </button>
          </div>
        </div>
      </section>

      <section className="section-pad jobs-section">
        <div className="container jobs-layout">
          <aside
            className="jobs-filters section-card jobs-filters--desktop"
            aria-label="Job filters"
          >
            {renderFiltersContent()}
          </aside>

          <div className="jobs-results">
            <div className="jobs-mobile-filters">
              <button
                type="button"
                className="jobs-mobile-filters__trigger section-card"
                onClick={() => setIsFiltersModalOpen(true)}
                aria-label="Open job filters"
              >
                <span className="jobs-mobile-filters__label">Filters</span>
                <span className="jobs-mobile-filters__summary">
                  Workplace, role type
                </span>
              </button>
            </div>

            <div className="jobs-results__header">
              <div>
                <h2 className="jobs-results__title">Open roles</h2>
                <p className="jobs-results__text">
                  {isLoading
                    ? "Loading roles..."
                    : error
                    ? "We could not load jobs right now."
                    : `${jobs.length} roles matched to your profile.`}
                </p>
              </div>

              {!isLoading ? (
                <button
                  type="button"
                  className="jobs-chip"
                  onClick={retry}
                  aria-label="Refresh jobs"
                >
                  Refresh
                </button>
              ) : null}
            </div>

            {isLoading ? (
              <div className="section-card" role="status" aria-live="polite">
                <p className="jobs-results__text">Loading jobs...</p>
              </div>
            ) : null}

            {!isLoading && error ? (
              <div className="section-card" role="alert" aria-live="polite">
                <h3 className="jobs-results__title">Unable to load jobs</h3>
                <p
                  className="jobs-results__text"
                  style={{ marginTop: "0.5rem" }}
                >
                  {error}
                </p>
                <div style={{ marginTop: "1rem" }}>
                  <button
                    type="button"
                    className="jobs-chip"
                    onClick={retry}
                  >
                    Try again
                  </button>
                </div>
              </div>
            ) : null}

            {!isLoading && !error && jobs.length === 0 ? (
              <div className="section-card" aria-live="polite">
                <h3 className="jobs-results__title">No jobs available yet</h3>
                <p
                  className="jobs-results__text"
                  style={{ marginTop: "0.5rem" }}
                >
                  There are no roles to show right now. Try refreshing in a bit
                  or switch to mock mode while backend data is still being wired.
                </p>
              </div>
            ) : null}

            {!isLoading && !error && jobs.length > 0 ? (
              <div className="jobs-list">
                {jobs.map((job) => (
                  <JobCard
                    key={job.id}
                    job={job}
                    onOpenReasonsModal={handleOpenReasonsModal}
                  />
                ))}
              </div>
            ) : null}
          </div>
        </div>
      </section>

      <CommonModal
        isOpen={isFiltersModalOpen}
        title="Filters"
        onClose={() => setIsFiltersModalOpen(false)}
        size="md"
        iconImage={BloombugAppIcon}
        iconAlt="EarlyBloom Bloombug icon"
      >
        <div className="jobs-filters jobs-filters--modal">
          {renderFiltersContent()}
        </div>
      </CommonModal>

      <CommonModal
        isOpen={isWelcomeModalOpen}
        title="Welcome to EarlyBloom"
        onClose={handleCloseWelcomeModal}
        size="md"
        iconImage={BloombugAppIcon}
        iconAlt="EarlyBloom Bloombug icon"
      >
        <div className="jobs-reasons-modal">
          <div className="jobs-reasons-modal__intro">
            <p className="jobs-reasons-modal__job-meta">
              You’re in 🌱 Let’s get your setup started.
            </p>

            <h3 className="jobs-reasons-modal__job-title">
              Upload your resume to make your search feel more tailored.
            </h3>

            <p className="jobs-results__text" style={{ marginTop: "0.5rem" }}>
              You can skip it for now, but adding your resume helps EarlyBloom
              organize your experience and shape the flow around you.
            </p>
          </div>

          <div
            style={{
              display: "flex",
              gap: "0.75rem",
              flexWrap: "wrap",
              marginTop: "1rem",
            }}
          >
            <button
              type="button"
              className="button button--primary"
              onClick={handleOpenResumeFromWelcome}
            >
              Upload resume
            </button>

            <button
              type="button"
              className="jobs-chip"
              onClick={handleCloseWelcomeModal}
            >
              Maybe later
            </button>
          </div>
        </div>
      </CommonModal>

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

            {activeReasonsJob.summary ? (
              <div className="jobs-reasons-modal__section">
                <p className="jobs-reasons-modal__label">Summary</p>
                <p className="jobs-results__text">{activeReasonsJob.summary}</p>
              </div>
            ) : null}

            {activeReasonsJob.url ? (
              <div style={{ marginTop: "1rem" }}>
                <a
                  href={activeReasonsJob.url}
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

      <ResumeUploadModal
        isOpen={isResumeModalOpen}
        onClose={handleCloseResumeModal}
        onResumeSaved={handleResumeSaved}
        resumeFile={resumeFile}
      />
    </main>
  );
}

export default Jobs;