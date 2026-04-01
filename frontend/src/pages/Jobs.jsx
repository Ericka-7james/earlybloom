import React, { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import JobCard from "../components/jobs/JobCard.jsx";
import ResumeUploadModal from "../components/jobs/ResumeUploadModal.jsx";
import CommonModal from "../components/common/CommonModal.jsx";
import "../styles/components/jobs.css";

import scoreJobsForUser from "../lib/jobs/scoreJobsForUser";
import mapJobsForDisplay from "../lib/jobs/mapJobsForDisplay";
import { readCachedResumeUiState } from "../lib/resumes";
import { useJobs } from "../hooks/useJobs";
import { useAuth } from "../hooks/useAuth";

import BloombugAppIcon from "../assets/bloombug/BloombugAppIcon.png";

const FILTER_GROUPS = {
  experienceLevel: [
    { label: "Entry-level", value: "entry-level" },
    { label: "Junior", value: "junior" },
    { label: "Mid-level", value: "mid-level" },
    { label: "Senior", value: "senior" },
  ],
  workplace: [
    { label: "Remote", value: "remote" },
    { label: "Onsite", value: "onsite" },
    { label: "Hybrid", value: "hybrid" },
  ],
  roleType: [
    { label: "Frontend", value: "frontend" },
    { label: "Backend", value: "backend" },
    { label: "Full Stack", value: "full-stack" },
    { label: "Software Engineering", value: "software-engineering" },
    { label: "Mobile", value: "mobile" },
    { label: "Data", value: "data" },
    { label: "Data Engineering", value: "data-engineering" },
    { label: "Data Analyst", value: "data-analyst" },
    { label: "Machine Learning", value: "machine-learning" },
    { label: "AI", value: "ai" },
    { label: "DevOps", value: "devops" },
    { label: "SRE", value: "sre" },
    { label: "Cloud", value: "cloud" },
    { label: "Infrastructure", value: "infrastructure" },
    { label: "Cybersecurity", value: "cybersecurity" },
    { label: "QA", value: "qa" },
    { label: "Test Automation", value: "test-automation" },
    { label: "Product", value: "product" },
    { label: "Product Design", value: "product-design" },
    { label: "UX", value: "ux" },
    { label: "Solutions Engineering", value: "solutions-engineering" },
    { label: "Technical Support", value: "technical-support" },
    { label: "IT", value: "it" },
    { label: "Business Analyst", value: "business-analyst" },
    { label: "Platform", value: "platform" },
    { label: "Developer Tools", value: "developer-tools" },
  ],
};

const DEFAULT_SELECTED_EXPERIENCE_LEVELS = ["entry-level", "junior"];

const RESUME_MODAL_DISMISSED_KEY = "earlybloom_resume_modal_dismissed";
const WELCOME_MODAL_PENDING_KEY = "earlybloom_welcome_modal_pending";

function getFitTagModifier(fitTag) {
  return String(fitTag || "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "-");
}

function normalizeValue(value) {
  return String(value || "")
    .trim()
    .toLowerCase();
}

function getJobExperienceLevel(job) {
  const directLevel = normalizeValue(
    job.experienceLevel || job.experience_level || job.level
  );

  if (
    directLevel === "entry-level" ||
    directLevel === "junior" ||
    directLevel === "mid-level" ||
    directLevel === "senior"
  ) {
    return directLevel;
  }

  if (directLevel === "mid") {
    return "mid-level";
  }

  const title = normalizeValue(job.title);
  const summary = normalizeValue(job.summary);
  const description = normalizeValue(job.description);
  const haystack = `${title} ${summary} ${description}`;

  if (
    haystack.includes("entry-level") ||
    haystack.includes("entry level") ||
    haystack.includes("new grad") ||
    haystack.includes("graduate") ||
    haystack.includes("early career")
  ) {
    return "entry-level";
  }

  if (haystack.includes("junior") || haystack.includes("jr ")) {
    return "junior";
  }

  if (
    haystack.includes("senior") ||
    haystack.includes("staff") ||
    haystack.includes("principal") ||
    haystack.includes("lead") ||
    haystack.includes("chief") ||
    haystack.includes("director")
  ) {
    return "senior";
  }

  if (
    haystack.includes("mid-level") ||
    haystack.includes("mid level") ||
    haystack.includes("intermediate") ||
    haystack.includes("level ii") ||
    haystack.includes("level 2")
  ) {
    return "mid-level";
  }

  return "unknown";
}

function getJobWorkplace(job) {
  const remoteType = normalizeValue(job.remoteType || job.remote_type);
  if (
    remoteType === "remote" ||
    remoteType === "onsite" ||
    remoteType === "hybrid"
  ) {
    return remoteType;
  }

  if (job.remote === true) {
    return "remote";
  }

  const haystack = normalizeValue(
    `${job.location || ""} ${job.summary || ""} ${job.description || ""}`
  );

  if (haystack.includes("hybrid")) {
    return "hybrid";
  }

  if (haystack.includes("remote") || haystack.includes("telework")) {
    return "remote";
  }

  if (haystack.includes("onsite") || haystack.includes("on-site")) {
    return "onsite";
  }

  return "unknown";
}

function inferRoleType(job) {
  const directRoleType = normalizeValue(job.roleType || job.role_type);
  if (directRoleType) {
    return directRoleType;
  }

  const haystack = normalizeValue(
    `${job.title || ""} ${job.summary || ""} ${job.description || ""}`
  );

  if (
    haystack.includes("frontend") ||
    haystack.includes("front-end") ||
    haystack.includes("react") ||
    haystack.includes("ui engineer")
  ) {
    return "frontend";
  }

  if (
    haystack.includes("backend") ||
    haystack.includes("back-end") ||
    haystack.includes("api") ||
    haystack.includes("server-side")
  ) {
    return "backend";
  }

  if (
    haystack.includes("full stack") ||
    haystack.includes("full-stack") ||
    haystack.includes("fullstack")
  ) {
    return "full-stack";
  }

  if (
    haystack.includes("software engineer") ||
    haystack.includes("software developer") ||
    haystack.includes("application developer") ||
    haystack.includes("programmer")
  ) {
    return "software-engineering";
  }

  if (
    haystack.includes("ios") ||
    haystack.includes("android") ||
    haystack.includes("mobile")
  ) {
    return "mobile";
  }

  if (
    haystack.includes("data engineer") ||
    haystack.includes("etl") ||
    haystack.includes("pipeline")
  ) {
    return "data-engineering";
  }

  if (
    haystack.includes("data analyst") ||
    haystack.includes("business intelligence") ||
    haystack.includes("reporting analyst")
  ) {
    return "data-analyst";
  }

  if (
    haystack.includes("data ") ||
    haystack.includes("analytics") ||
    haystack.includes("analyst")
  ) {
    return "data";
  }

  if (
    haystack.includes("machine learning") ||
    haystack.includes("ml engineer")
  ) {
    return "machine-learning";
  }

  if (
    haystack.includes("artificial intelligence") ||
    haystack.includes(" ai ")
  ) {
    return "ai";
  }

  if (
    haystack.includes("devops") ||
    haystack.includes("devsecops") ||
    haystack.includes("ci/cd")
  ) {
    return "devops";
  }

  if (
    haystack.includes("site reliability") ||
    haystack.includes(" sre ")
  ) {
    return "sre";
  }

  if (haystack.includes("cloud")) {
    return "cloud";
  }

  if (
    haystack.includes("infrastructure") ||
    haystack.includes("sysadmin") ||
    haystack.includes("systems administration")
  ) {
    return "infrastructure";
  }

  if (
    haystack.includes("cyber") ||
    haystack.includes("security") ||
    haystack.includes("infosec")
  ) {
    return "cybersecurity";
  }

  if (
    haystack.includes("qa") ||
    haystack.includes("quality assurance") ||
    haystack.includes("test automation") ||
    haystack.includes("sdet")
  ) {
    return haystack.includes("automation") ? "test-automation" : "qa";
  }

  if (haystack.includes("product manager")) {
    return "product";
  }

  if (
    haystack.includes("product design") ||
    haystack.includes("product designer")
  ) {
    return "product-design";
  }

  if (
    haystack.includes("ux") ||
    haystack.includes("user experience") ||
    haystack.includes("ui/ux")
  ) {
    return "ux";
  }

  if (
    haystack.includes("solutions engineer") ||
    haystack.includes("sales engineer") ||
    haystack.includes("implementation engineer")
  ) {
    return "solutions-engineering";
  }

  if (
    haystack.includes("technical support") ||
    haystack.includes("support engineer") ||
    haystack.includes("help desk")
  ) {
    return "technical-support";
  }

  if (
    haystack.includes("it specialist") ||
    haystack.includes("it support") ||
    haystack.includes("information technology")
  ) {
    return "it";
  }

  if (
    haystack.includes("business analyst") ||
    haystack.includes("systems analyst")
  ) {
    return "business-analyst";
  }

  if (haystack.includes("platform")) {
    return "platform";
  }

  if (
    haystack.includes("developer tools") ||
    haystack.includes("devtools")
  ) {
    return "developer-tools";
  }

  return "unknown";
}

function toggleSelectedValue(currentValues, value) {
  if (currentValues.includes(value)) {
    return currentValues.filter((item) => item !== value);
  }

  return [...currentValues, value];
}

function getFilterSummary({
  selectedExperienceLevels,
  selectedWorkplaces,
  selectedRoleTypes,
}) {
  const parts = [];

  if (selectedExperienceLevels.length > 0) {
    parts.push(`${selectedExperienceLevels.length} level`);
  }

  if (selectedWorkplaces.length > 0) {
    parts.push(`${selectedWorkplaces.length} workplace`);
  }

  if (selectedRoleTypes.length > 0) {
    parts.push(`${selectedRoleTypes.length} role type`);
  }

  if (parts.length === 0) {
    return "All roles";
  }

  return parts.join(" • ");
}

function Jobs() {
  const navigate = useNavigate();
  const { user, loading: authLoading } = useAuth();

  const [activeReasonsJob, setActiveReasonsJob] = useState(null);
  const [isFiltersModalOpen, setIsFiltersModalOpen] = useState(false);
  const [isLoginRequiredModalOpen, setIsLoginRequiredModalOpen] =
    useState(false);
  const [resumeFile, setResumeFile] = useState(() => readCachedResumeUiState());
  const [selectedExperienceLevels, setSelectedExperienceLevels] = useState(
    DEFAULT_SELECTED_EXPERIENCE_LEVELS
  );
  const [selectedWorkplaces, setSelectedWorkplaces] = useState([]);
  const [selectedRoleTypes, setSelectedRoleTypes] = useState([]);

  const visibleResumeFile = useMemo(() => {
    if (!user) {
      return null;
    }

    return resumeFile;
  }, [user, resumeFile]);

  const hasUploadedResume = Boolean(visibleResumeFile);
  const hasCachedResume = Boolean(visibleResumeFile);
  const welcomePending =
    window.sessionStorage.getItem(WELCOME_MODAL_PENDING_KEY) === "true";

  const [isWelcomeModalOpen, setIsWelcomeModalOpen] = useState(
    welcomePending && !hasCachedResume && !hasUploadedResume
  );

  const {
    jobs: rawJobs,
    resolvedUserProfile,
    isLoading,
    error,
    isMockMode,
    retry,
  } = useJobs();

  const [isResumeModalOpen, setIsResumeModalOpen] = useState(false);

  const scoredJobs = useMemo(() => {
    return scoreJobsForUser(rawJobs, resolvedUserProfile);
  }, [rawJobs, resolvedUserProfile]);

  const mappedJobs = useMemo(() => {
    return mapJobsForDisplay(rawJobs, scoredJobs).sort(
      (a, b) => b.matchScore - a.matchScore
    );
  }, [rawJobs, scoredJobs]);

  const jobs = useMemo(() => {
    return mappedJobs.filter((job) => {
      const experienceLevel = getJobExperienceLevel(job);
      const workplace = getJobWorkplace(job);
      const roleType = inferRoleType(job);

      const matchesExperienceLevel =
        selectedExperienceLevels.length === 0 ||
        selectedExperienceLevels.includes(experienceLevel);

      const matchesWorkplace =
        selectedWorkplaces.length === 0 ||
        selectedWorkplaces.includes(workplace);

      const matchesRoleType =
        selectedRoleTypes.length === 0 || selectedRoleTypes.includes(roleType);

      return matchesExperienceLevel && matchesWorkplace && matchesRoleType;
    });
  }, [
    mappedJobs,
    selectedExperienceLevels,
    selectedWorkplaces,
    selectedRoleTypes,
  ]);

  const filtersSummary = useMemo(() => {
    return getFilterSummary({
      selectedExperienceLevels,
      selectedWorkplaces,
      selectedRoleTypes,
    });
  }, [selectedExperienceLevels, selectedWorkplaces, selectedRoleTypes]);

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
    window.sessionStorage.removeItem(RESUME_MODAL_DISMISSED_KEY);
  }

  function handleCloseWelcomeModal() {
    setIsWelcomeModalOpen(false);
    window.sessionStorage.removeItem(WELCOME_MODAL_PENDING_KEY);
  }

  function handleOpenResumeFromWelcome() {
    handleRequestResumeUpload();
  }

  function handleCloseLoginRequiredModal() {
    setIsLoginRequiredModalOpen(false);
  }

  function handleGoToSignIn() {
    setIsLoginRequiredModalOpen(false);
    navigate("/sign-in");
  }

  function handleRequestResumeUpload() {
    if (authLoading) {
      return;
    }

    if (!user) {
      setIsWelcomeModalOpen(false);
      setIsResumeModalOpen(false);
      setIsLoginRequiredModalOpen(true);
      return;
    }

    setIsLoginRequiredModalOpen(false);
    setIsResumeModalOpen(true);
  }

  function renderFilterChips(options, selectedValues, onToggle) {
    return (
      <div className="jobs-chip-list">
        {options.map((option) => {
          const isSelected = selectedValues.includes(option.value);

          return (
            <button
              key={option.value}
              type="button"
              className={`jobs-chip ${isSelected ? "jobs-chip--active" : ""}`}
              aria-pressed={isSelected}
              onClick={() => onToggle(option.value)}
            >
              {option.label}
            </button>
          );
        })}
      </div>
    );
  }

  function renderFiltersContent() {
    return (
      <>
        <div className="jobs-filters__header">
          <h2 className="jobs-results__title">Filters</h2>
          <p className="jobs-filters__text">
            Entry-level and junior are selected by default for development, but
            you can widen the search whenever you want.
          </p>
        </div>

        <div className="jobs-filter-group">
          <h3 className="jobs-filter-group__title">Experience level</h3>
          {renderFilterChips(
            FILTER_GROUPS.experienceLevel,
            selectedExperienceLevels,
            (value) =>
              setSelectedExperienceLevels((currentValues) =>
                toggleSelectedValue(currentValues, value)
              )
          )}
        </div>

        <div className="jobs-filter-group">
          <h3 className="jobs-filter-group__title">Workplace</h3>
          {renderFilterChips(
            FILTER_GROUPS.workplace,
            selectedWorkplaces,
            (value) =>
              setSelectedWorkplaces((currentValues) =>
                toggleSelectedValue(currentValues, value)
              )
          )}
        </div>

        <div className="jobs-filter-group">
          <h3 className="jobs-filter-group__title">Role type</h3>
          {renderFilterChips(
            FILTER_GROUPS.roleType,
            selectedRoleTypes,
            (value) =>
              setSelectedRoleTypes((currentValues) =>
                toggleSelectedValue(currentValues, value)
              )
          )}
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
              onClick={handleRequestResumeUpload}
            >
              <div className="jobs-hero__upload-box">
                <p className="jobs-hero__upload-title">
                  {visibleResumeFile ? "Resume uploaded" : "Upload your resume"}
                </p>
                <p className="jobs-hero__upload-subtext">
                  {visibleResumeFile
                    ? visibleResumeFile.name
                    : "PDF only • click to upload"}
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
                  {filtersSummary}
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
                <h3 className="jobs-results__title">No roles match these filters</h3>
                <p
                  className="jobs-results__text"
                  style={{ marginTop: "0.5rem" }}
                >
                  Try widening your experience level, workplace, or role type
                  filters to see more jobs.
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
        isOpen={isLoginRequiredModalOpen}
        title="Sign in required"
        onClose={handleCloseLoginRequiredModal}
        size="md"
        iconImage={BloombugAppIcon}
        iconAlt="EarlyBloom Bloombug icon"
      >
        <div className="jobs-reasons-modal">
          <div className="jobs-reasons-modal__intro">
            <p className="jobs-reasons-modal__job-meta">
              Resume upload is available after sign in.
            </p>

            <h3 className="jobs-reasons-modal__job-title">
              Sign in to upload your resume
            </h3>

            <p className="jobs-results__text" style={{ marginTop: "0.5rem" }}>
              This helps us connect your resume to your account and keep your
              job search data in one place.
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
              onClick={handleGoToSignIn}
            >
              Sign in
            </button>

            <button
              type="button"
              className="jobs-chip"
              onClick={handleCloseLoginRequiredModal}
            >
              Cancel
            </button>
          </div>
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
        resumeFile={visibleResumeFile}
      />
    </main>
  );
}

export default Jobs;