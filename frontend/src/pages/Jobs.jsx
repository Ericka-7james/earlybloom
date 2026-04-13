import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import JobCard from "../components/jobs/JobCard.jsx";
import JobsFiltersPanel from "../components/jobs/JobsFiltersPanel.jsx";
import JobsActiveFilters from "../components/jobs/JobsActiveFilters.jsx";
import JobDetailsModal from "../components/jobs/JobDetailsModal.jsx";
import ResumeUploadModal from "../components/jobs/ResumeUploadModal.jsx";
import CommonModal from "../components/common/CommonModal.jsx";
import "../styles/components/jobs.css";

import scoreJobsForUser from "../lib/jobs/scoreJobsForUser";
import mapJobsForDisplay from "../lib/jobs/mapJobsForDisplay";
import { readCachedResumeUiState } from "../lib/resumes";
import { useJobs } from "../hooks/useJobs";
import { useAuth } from "../hooks/useAuth";
import {
  hideJob,
  saveJob,
  unsaveJob,
} from "../lib/jobs/jobsApi";
import {
  DEFAULT_SELECTED_EXPERIENCE_LEVELS,
  arraysEqualAsSets,
  filterJobs,
  getFilterSummary,
  getActiveFilterTags,
} from "../lib/jobs/jobFilters";

import BloombugAppIcon from "../assets/bloombug/BloombugAppIcon.png";

const RESUME_MODAL_DISMISSED_KEY = "earlybloom_resume_modal_dismissed";
const WELCOME_MODAL_PENDING_KEY = "earlybloom_welcome_modal_pending";

function getLoginRequiredContent(intent) {
  switch (intent) {
    case "save":
      return {
        eyebrow: "Save jobs to come back to them later.",
        title: "Sign in to save jobs",
        body: "Your saved jobs live on your tracker, so you can revisit strong leads without hunting them down again.",
      };
    case "hide":
      return {
        eyebrow: "Hide jobs you do not want to keep seeing.",
        title: "Sign in to hide jobs",
        body: "Signing in lets EarlyBloom remember which roles you have already passed on and keep your feed cleaner.",
      };
    case "resume":
    default:
      return {
        eyebrow: "Resume upload is available after sign in.",
        title: "Sign in to upload your resume",
        body: "This helps us connect your resume to your account and keep your job search data in one place.",
      };
  }
}

function Jobs() {
  const navigate = useNavigate();
  const { user, loading: authLoading } = useAuth();
  const viewerKey = user?.id ? `user:${user.id}` : "guest";

  const [activeJob, setActiveJob] = useState(null);
  const [isFiltersModalOpen, setIsFiltersModalOpen] = useState(false);
  const [isLoginRequiredModalOpen, setIsLoginRequiredModalOpen] =
    useState(false);
  const [loginRequiredIntent, setLoginRequiredIntent] = useState("resume");
  const [resumeFile, setResumeFile] = useState(() => readCachedResumeUiState());
  const [selectedExperienceLevels, setSelectedExperienceLevels] = useState(
    DEFAULT_SELECTED_EXPERIENCE_LEVELS
  );
  const [selectedWorkplaces, setSelectedWorkplaces] = useState([]);
  const [selectedRoleTypes, setSelectedRoleTypes] = useState([]);
  const [isResumeModalOpen, setIsResumeModalOpen] = useState(false);
  const [jobViewerOverrides, setJobViewerOverrides] = useState({});
  const [pendingActions, setPendingActions] = useState({});
  const [actionError, setActionError] = useState("");

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
  } = useJobs({ viewerKey });

  useEffect(() => {
    setJobViewerOverrides({});
    setPendingActions({});
    setActionError("");
  }, [viewerKey, rawJobs]);

  const scoredJobs = useMemo(() => {
    return scoreJobsForUser(rawJobs, resolvedUserProfile);
  }, [rawJobs, resolvedUserProfile]);

  const mappedJobs = useMemo(() => {
    return mapJobsForDisplay(rawJobs, scoredJobs, {
      viewerStateOverrides: jobViewerOverrides,
    }).sort((a, b) => b.matchScore - a.matchScore);
  }, [rawJobs, scoredJobs, jobViewerOverrides]);

  const jobs = useMemo(() => {
    return filterJobs(mappedJobs, {
      selectedExperienceLevels,
      selectedWorkplaces,
      selectedRoleTypes,
    }).filter((job) => !job.isHidden);
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

  const hasActiveFilters =
    selectedExperienceLevels.length > 0 ||
    selectedWorkplaces.length > 0 ||
    selectedRoleTypes.length > 0;

  const isUsingDefaultExperiencePreset = useMemo(() => {
    return arraysEqualAsSets(
      selectedExperienceLevels,
      DEFAULT_SELECTED_EXPERIENCE_LEVELS
    );
  }, [selectedExperienceLevels]);

  const activeFilterTags = useMemo(() => {
    return getActiveFilterTags({
      selectedExperienceLevels,
      selectedWorkplaces,
      selectedRoleTypes,
    });
  }, [selectedExperienceLevels, selectedWorkplaces, selectedRoleTypes]);

  function handleOpenDetails(job) {
    setActiveJob(job);
  }

  function handleCloseDetails() {
    setActiveJob(null);
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

  function openLoginRequiredModal(intent) {
    setLoginRequiredIntent(intent);
    setIsLoginRequiredModalOpen(true);
  }

  function handleRequestResumeUpload() {
    if (authLoading) {
      return;
    }

    if (!user) {
      setIsWelcomeModalOpen(false);
      setIsResumeModalOpen(false);
      openLoginRequiredModal("resume");
      return;
    }

    setIsLoginRequiredModalOpen(false);
    setIsResumeModalOpen(true);
  }

  function clearAllFilters() {
    setSelectedExperienceLevels([]);
    setSelectedWorkplaces([]);
    setSelectedRoleTypes([]);
  }

  function removeActiveFilterTag(tag) {
    if (tag.type === "experience") {
      setSelectedExperienceLevels((currentValues) =>
        currentValues.filter((value) => value !== tag.value)
      );
      return;
    }

    if (tag.type === "workplace") {
      setSelectedWorkplaces((currentValues) =>
        currentValues.filter((value) => value !== tag.value)
      );
      return;
    }

    setSelectedRoleTypes((currentValues) =>
      currentValues.filter((value) => value !== tag.value)
    );
  }

  function updatePendingAction(jobId, nextState) {
    setPendingActions((current) => ({
      ...current,
      [jobId]: {
        ...(current[jobId] || {}),
        ...nextState,
      },
    }));
  }

  function clearPendingAction(jobId, key) {
    setPendingActions((current) => {
      const next = { ...current };
      const currentEntry = { ...(next[jobId] || {}) };
      delete currentEntry[key];

      if (Object.keys(currentEntry).length === 0) {
        delete next[jobId];
      } else {
        next[jobId] = currentEntry;
      }

      return next;
    });
  }

  function applyViewerOverride(jobId, patch) {
    setJobViewerOverrides((current) => ({
      ...current,
      [jobId]: {
        ...(current[jobId] || {}),
        ...patch,
      },
    }));
  }

  function removeViewerOverride(jobId) {
    setJobViewerOverrides((current) => {
      const next = { ...current };
      delete next[jobId];
      return next;
    });
  }

  async function handleToggleSave(job) {
    if (authLoading) {
      return;
    }

    if (!user) {
      openLoginRequiredModal("save");
      return;
    }

    const jobId = job.id;
    const nextSaved = !job.isSaved;
    const previousOverride = jobViewerOverrides[jobId];

    setActionError("");
    updatePendingAction(jobId, { saving: true });
    applyViewerOverride(jobId, {
      is_saved: nextSaved,
      saved_at: nextSaved ? new Date().toISOString() : null,
    });

    try {
      const result = nextSaved ? await saveJob(jobId) : await unsaveJob(jobId);
      const nextViewerState = result?.viewer_state ?? null;

      if (nextViewerState) {
        applyViewerOverride(jobId, nextViewerState);
      }
    } catch (err) {
      if (previousOverride) {
        applyViewerOverride(jobId, previousOverride);
      } else {
        removeViewerOverride(jobId);
      }

      setActionError(
        err instanceof Error
          ? err.message
          : "We could not update that saved job right now."
      );
    } finally {
      clearPendingAction(jobId, "saving");
    }
  }

  async function handleHideJob(job) {
    if (authLoading) {
      return;
    }

    if (!user) {
      openLoginRequiredModal("hide");
      return;
    }

    const jobId = job.id;
    const previousOverride = jobViewerOverrides[jobId];

    setActionError("");
    updatePendingAction(jobId, { hiding: true });
    applyViewerOverride(jobId, {
      is_hidden: true,
      hidden_at: new Date().toISOString(),
    });

    try {
      const result = await hideJob(jobId);
      const nextViewerState = result?.viewer_state ?? null;

      if (nextViewerState) {
        applyViewerOverride(jobId, nextViewerState);
      }
    } catch (err) {
      if (previousOverride) {
        applyViewerOverride(jobId, previousOverride);
      } else {
        removeViewerOverride(jobId);
      }

      setActionError(
        err instanceof Error
          ? err.message
          : "We could not hide that job right now."
      );
    } finally {
      clearPendingAction(jobId, "hiding");
    }
  }

  const loginContent = getLoginRequiredContent(loginRequiredIntent);

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
            <JobsFiltersPanel
              hasActiveFilters={hasActiveFilters}
              selectedExperienceLevels={selectedExperienceLevels}
              selectedWorkplaces={selectedWorkplaces}
              selectedRoleTypes={selectedRoleTypes}
              setSelectedExperienceLevels={setSelectedExperienceLevels}
              setSelectedWorkplaces={setSelectedWorkplaces}
              setSelectedRoleTypes={setSelectedRoleTypes}
              onClearAll={clearAllFilters}
            />
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

            <JobsActiveFilters
              hasActiveFilters={hasActiveFilters}
              isUsingDefaultExperiencePreset={isUsingDefaultExperiencePreset}
              selectedWorkplaces={selectedWorkplaces}
              selectedRoleTypes={selectedRoleTypes}
              activeFilterTags={activeFilterTags}
              onClearAll={clearAllFilters}
              onRemoveTag={removeActiveFilterTag}
            />

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

            {actionError ? (
              <div className="section-card" role="alert" aria-live="polite">
                <p className="jobs-results__text">{actionError}</p>
              </div>
            ) : null}

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
                  <button type="button" className="jobs-chip" onClick={retry}>
                    Try again
                  </button>
                </div>
              </div>
            ) : null}

            {!isLoading && !error && jobs.length === 0 ? (
              <div className="section-card" aria-live="polite">
                <h3 className="jobs-results__title">
                  {hasActiveFilters
                    ? "No roles match these filters"
                    : "No roles available right now"}
                </h3>

                <p
                  className="jobs-results__text"
                  style={{ marginTop: "0.5rem" }}
                >
                  {hasActiveFilters
                    ? "Try clearing a few filters or widening your search to see more roles."
                    : "We could not find any roles to show right now. Refresh and try again in a moment."}
                </p>

                {hasActiveFilters ? (
                  <div style={{ marginTop: "1rem" }}>
                    <button
                      type="button"
                      className="jobs-chip"
                      onClick={clearAllFilters}
                    >
                      Clear filters
                    </button>
                  </div>
                ) : null}
              </div>
            ) : null}

            {!isLoading && !error && jobs.length > 0 ? (
              <div className="jobs-list">
                {jobs.map((job) => (
                  <JobCard
                    key={job.id}
                    job={job}
                    onOpenDetails={handleOpenDetails}
                    onSaveToggle={handleToggleSave}
                    onHide={handleHideJob}
                    isSavePending={Boolean(pendingActions[job.id]?.saving)}
                    isHidePending={Boolean(pendingActions[job.id]?.hiding)}
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
          <JobsFiltersPanel
            hasActiveFilters={hasActiveFilters}
            selectedExperienceLevels={selectedExperienceLevels}
            selectedWorkplaces={selectedWorkplaces}
            selectedRoleTypes={selectedRoleTypes}
            setSelectedExperienceLevels={setSelectedExperienceLevels}
            setSelectedWorkplaces={setSelectedWorkplaces}
            setSelectedRoleTypes={setSelectedRoleTypes}
            onClearAll={clearAllFilters}
          />
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
            <p className="jobs-reasons-modal__job-meta">{loginContent.eyebrow}</p>

            <h3 className="jobs-reasons-modal__job-title">
              {loginContent.title}
            </h3>

            <p className="jobs-results__text" style={{ marginTop: "0.5rem" }}>
              {loginContent.body}
            </p>
          </div>

          <div className="jobs-inline-actions">
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

          <div className="jobs-inline-actions">
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

      <JobDetailsModal
        job={activeJob}
        isOpen={Boolean(activeJob)}
        onClose={handleCloseDetails}
      />

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