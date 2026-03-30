import React, { useEffect, useMemo, useRef, useState } from "react";
import JobCard from "../components/jobs/JobCard.jsx";
import CommonModal from "../components/common/CommonModal.jsx";
import "../styles/components/jobs.css";

import { MOCK_RAW_JOBS } from "../mock/jobs/jobs.raw";
import { MOCK_USER_PROFILE } from "../mock/jobs/jobs.user-profile";

import scoreJobsForUser from "../lib/jobs/scoreJobsForUser";
import mapJobsForDisplay from "../lib/jobs/mapJobsForDisplay";

import BloombugAppIcon from "../assets/bloombug/BloombugAppIcon.png";
import BloomHire from "../assets/bloombug/BloomHire.png";

const FILTER_GROUPS = {
  workplace: ["Remote", "Onsite", "Hybrid"],
  roleType: ["Frontend", "Backend", "Full Stack", "Data", "Product"],
};

const RESUME_STORAGE_KEY = "earlybloom_resume_upload";
const RESUME_MODAL_DISMISSED_KEY = "earlybloom_resume_modal_dismissed";

function getFitTagModifier(fitTag) {
  return String(fitTag || "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "-");
}

function Jobs() {
  const [activeReasonsJob, setActiveReasonsJob] = useState(null);
  const [isResumeModalOpen, setIsResumeModalOpen] = useState(false);
  const [resumeError, setResumeError] = useState("");
  const [resumeFile, setResumeFile] = useState(() => {
    try {
      const cachedResume = window.localStorage.getItem(RESUME_STORAGE_KEY);
      return cachedResume ? JSON.parse(cachedResume) : null;
    } catch {
      return null;
    }
  });

  const fileInputRef = useRef(null);

  const scoredJobs = useMemo(() => {
    return scoreJobsForUser(MOCK_RAW_JOBS, MOCK_USER_PROFILE);
  }, []);

  const jobs = useMemo(() => {
    return mapJobsForDisplay(MOCK_RAW_JOBS, scoredJobs).sort(
      (a, b) => b.matchScore - a.matchScore
    );
  }, [scoredJobs]);

  useEffect(() => {
    const wasDismissed =
      window.sessionStorage.getItem(RESUME_MODAL_DISMISSED_KEY) === "true";

    const hasCachedResume = Boolean(resumeFile);

    /**
     * Placeholder for future signed-in resume checks.
     * Example later:
     * const hasUploadedResume = Boolean(user?.resumeUrl);
     */
    const hasUploadedResume = false;

    if (!hasCachedResume && !hasUploadedResume && !wasDismissed) {
      setIsResumeModalOpen(true);
    }
  }, [resumeFile]);

  function handleOpenReasonsModal(job) {
    setActiveReasonsJob(job);
  }

  function handleCloseReasonsModal() {
    setActiveReasonsJob(null);
  }

  function handleCloseResumeModal() {
    setResumeError("");
    setIsResumeModalOpen(false);
    window.sessionStorage.setItem(RESUME_MODAL_DISMISSED_KEY, "true");
  }

  function isPdfFile(file) {
    if (!file) {
      return false;
    }

    const isPdfMimeType = file.type === "application/pdf";
    const hasPdfExtension = file.name.toLowerCase().endsWith(".pdf");

    return isPdfMimeType || hasPdfExtension;
  }

  function cacheResumeFile(file) {
    const cachedResume = {
      name: file.name,
      size: file.size,
      type: file.type,
      uploadedAt: new Date().toISOString(),
    };

    setResumeFile(cachedResume);
    window.localStorage.setItem(
      RESUME_STORAGE_KEY,
      JSON.stringify(cachedResume)
    );

    window.sessionStorage.setItem(RESUME_MODAL_DISMISSED_KEY, "true");
    setIsResumeModalOpen(false);
  }

  function handleResumeFileChange(event) {
    const file = event.target.files?.[0];

    if (!file) {
      return;
    }

    if (!isPdfFile(file)) {
      setResumeError("Please upload a PDF resume.");
      event.target.value = "";
      return;
    }

    setResumeError("");
    cacheResumeFile(file);
    event.target.value = "";
  }

  function handleResumeDrop(event) {
    event.preventDefault();

    const file = event.dataTransfer.files?.[0];

    if (!file) {
      return;
    }

    if (!isPdfFile(file)) {
      setResumeError("Please upload a PDF resume.");
      return;
    }

    setResumeError("");
    cacheResumeFile(file);
  }

  function handleResumeDragOver(event) {
    event.preventDefault();
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

      <CommonModal
        isOpen={isResumeModalOpen}
        title="Upload your resume"
        onClose={handleCloseResumeModal}
        size="sm"
        iconImage={BloomHire}
        iconAlt="EarlyBloom resume upload icon"
      >
        <div className="resume-upload-modal">
          <p className="resume-upload-modal__text">
            Upload your resume to personalize your job matches.
          </p>

          <button
            type="button"
            className="resume-upload-dropzone"
            onClick={() => fileInputRef.current?.click()}
            onDrop={handleResumeDrop}
            onDragOver={handleResumeDragOver}
          >
            <span className="resume-upload-dropzone__label">Upload file</span>
            <span className="resume-upload-dropzone__hint">PDF only</span>
          </button>

          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,application/pdf"
            className="resume-upload-modal__input"
            onChange={handleResumeFileChange}
          />

          {resumeError ? (
            <p className="resume-upload-modal__error" role="alert">
              {resumeError}
            </p>
          ) : null}

          {resumeFile ? (
            <p className="resume-upload-modal__success" aria-live="polite">
              Cached resume: {resumeFile.name}
            </p>
          ) : null}
        </div>
      </CommonModal>
    </main>
  );
}

export default Jobs;