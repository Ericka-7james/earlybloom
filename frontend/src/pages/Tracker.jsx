import React, { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import JobCard from "../components/jobs/JobCard.jsx";
import CommonModal from "../components/common/CommonModal.jsx";
import ResumeUploadModal from "../components/jobs/ResumeUploadModal.jsx";
import TrackerPreferencesPanel from "../components/tracker/TrackerPreferencesPanel.jsx";
import BloombugAppIcon from "../assets/bloombug/BloombugAppIcon.png";
import { useAuth } from "../hooks/useAuth";
import {
  fetchHiddenJobs,
  fetchSavedJobs,
  hideJob,
  saveJob,
  unhideJob,
  unsaveJob,
} from "../lib/jobs/jobsApi";
import scoreJobsForUser from "../lib/jobs/scoreJobsForUser";
import mapJobsForDisplay from "../lib/jobs/mapJobsForDisplay";
import {
  fetchTracker,
  updateTrackerPreferences,
} from "../lib/tracker/trackerApi";
import "../styles/components/tracker.css";

const TRACKER_TABS = {
  SAVED: "saved",
  HIDDEN: "hidden",
};

const DEFAULT_PREFERENCES = {
  desired_levels: ["entry-level", "junior"],
  preferred_role_types: [],
  preferred_workplace_types: [],
  preferred_locations: [],
  is_lgbt_friendly_only: false,
};

function titleCase(value) {
  return String(value || "")
    .split(/[\s_-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatDate(value) {
  if (!value) {
    return "Not available";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Not available";
  }

  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatResumeLocation(location) {
  if (!location || typeof location !== "object") {
    return "Not detected";
  }

  const cityRegion = [location.city, location.region]
    .filter(Boolean)
    .join(", ")
    .trim();

  if (cityRegion) {
    return cityRegion;
  }

  const raw = String(location.raw || "").trim();

  if (!raw) {
    return "Not detected";
  }

  if (raw.length > 40) {
    return "Not detected";
  }

  if (
    /\b[A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+,\s*[A-Z]{2}\b/.test(
      raw
    )
  ) {
    return "Not detected";
  }

  return raw;
}

function normalizeWarnings(warnings) {
  if (!Array.isArray(warnings)) {
    return [];
  }

  return warnings
    .map((warning) => String(warning || "").trim())
    .filter(Boolean);
}

function useViewportWidth() {
  const [viewportWidth, setViewportWidth] = useState(() =>
    typeof window === "undefined" ? 1280 : window.innerWidth
  );

  useEffect(() => {
    function handleResize() {
      setViewportWidth(window.innerWidth);
    }

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  return viewportWidth;
}

function Tracker() {
  const navigate = useNavigate();
  const { user, loading: authLoading } = useAuth();
  const viewportWidth = useViewportWidth();
  const isMobile = viewportWidth <= 920;

  const [activeTab, setActiveTab] = useState(TRACKER_TABS.SAVED);
  const [savedJobsRaw, setSavedJobsRaw] = useState([]);
  const [hiddenJobsRaw, setHiddenJobsRaw] = useState([]);
  const [resolvedUserProfile, setResolvedUserProfile] = useState({
    desiredLevels: ["entry-level", "junior"],
    preferredRoleTypes: [],
    preferredWorkplaceTypes: [],
    preferredLocations: [],
    skills: [],
    isLgbtFriendlyOnly: false,
  });

  const [trackerData, setTrackerData] = useState({
    preferences: DEFAULT_PREFERENCES,
    resume: null,
    stats: {
      saved_jobs_count: 0,
      hidden_jobs_count: 0,
    },
  });

  const [preferencesDraft, setPreferencesDraft] = useState(DEFAULT_PREFERENCES);
  const [isSavingPreferences, setIsSavingPreferences] = useState(false);
  const [isResumeModalOpen, setIsResumeModalOpen] = useState(false);
  const [isPreferencesModalOpen, setIsPreferencesModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [pendingActions, setPendingActions] = useState({});
  const [viewerOverrides, setViewerOverrides] = useState({});

  useEffect(() => {
    let isMounted = true;
    const controller = new AbortController();

    async function loadTrackerData() {
      if (!user) {
        setSavedJobsRaw([]);
        setHiddenJobsRaw([]);
        setTrackerData({
          preferences: DEFAULT_PREFERENCES,
          resume: null,
          stats: {
            saved_jobs_count: 0,
            hidden_jobs_count: 0,
          },
        });
        setPreferencesDraft(DEFAULT_PREFERENCES);
        setIsLoading(false);
        setError("");
        return;
      }

      setIsLoading(true);
      setError("");

      const [savedJobsResult, hiddenJobsResult, trackerResult] =
        await Promise.allSettled([
          fetchSavedJobs({ signal: controller.signal }),
          fetchHiddenJobs({ signal: controller.signal }),
          fetchTracker(),
        ]);

      if (!isMounted || controller.signal.aborted) {
        return;
      }

      const nextSavedJobs =
        savedJobsResult.status === "fulfilled" &&
        Array.isArray(savedJobsResult.value)
          ? savedJobsResult.value
          : [];

      const nextHiddenJobs =
        hiddenJobsResult.status === "fulfilled" &&
        Array.isArray(hiddenJobsResult.value)
          ? hiddenJobsResult.value
          : [];

      const tracker =
        trackerResult.status === "fulfilled" && trackerResult.value
          ? trackerResult.value
          : {
              preferences: DEFAULT_PREFERENCES,
              resume: null,
              stats: {
                saved_jobs_count: nextSavedJobs.length,
                hidden_jobs_count: nextHiddenJobs.length,
              },
            };

      const nextPreferences = tracker?.preferences || DEFAULT_PREFERENCES;

      const nextResolvedProfile = {
        desiredLevels: nextPreferences.desired_levels?.length
          ? nextPreferences.desired_levels
          : ["entry-level", "junior"],
        preferredRoleTypes: nextPreferences.preferred_role_types || [],
        preferredWorkplaceTypes:
          nextPreferences.preferred_workplace_types || [],
        preferredLocations: nextPreferences.preferred_locations || [],
        skills:
          tracker?.resume?.parsed_json?.skills?.normalized ||
          tracker?.resume?.parsed_json?.summary?.top_skill_keywords ||
          [],
        isLgbtFriendlyOnly: Boolean(nextPreferences.is_lgbt_friendly_only),
      };

      const loadErrors = [];

      if (savedJobsResult.status === "rejected") {
        loadErrors.push("Saved jobs could not be loaded.");
      }

      if (hiddenJobsResult.status === "rejected") {
        loadErrors.push("Hidden jobs could not be loaded.");
      }

      setSavedJobsRaw(nextSavedJobs);
      setHiddenJobsRaw(nextHiddenJobs);
      setTrackerData(tracker);
      setPreferencesDraft(nextPreferences);
      setResolvedUserProfile(nextResolvedProfile);
      setError(loadErrors.join(" "));
      setIsLoading(false);
    }

    loadTrackerData();

    return () => {
      isMounted = false;
      controller.abort();
    };
  }, [user]);

  function updatePendingAction(jobId, patch) {
    setPendingActions((current) => ({
      ...current,
      [jobId]: {
        ...(current[jobId] || {}),
        ...patch,
      },
    }));
  }

  function clearPendingAction(jobId, key) {
    setPendingActions((current) => {
      const next = { ...current };
      const entry = { ...(next[jobId] || {}) };

      delete entry[key];

      if (Object.keys(entry).length === 0) {
        delete next[jobId];
      } else {
        next[jobId] = entry;
      }

      return next;
    });
  }

  function applyViewerOverride(jobId, patch) {
    setViewerOverrides((current) => ({
      ...current,
      [jobId]: {
        ...(current[jobId] || {}),
        ...patch,
      },
    }));
  }

  const savedScoredJobs = useMemo(() => {
    return scoreJobsForUser(savedJobsRaw, resolvedUserProfile);
  }, [savedJobsRaw, resolvedUserProfile]);

  const hiddenScoredJobs = useMemo(() => {
    return scoreJobsForUser(hiddenJobsRaw, resolvedUserProfile);
  }, [hiddenJobsRaw, resolvedUserProfile]);

  const savedJobs = useMemo(() => {
    return mapJobsForDisplay(savedJobsRaw, savedScoredJobs, {
      viewerStateOverrides: viewerOverrides,
    }).sort((a, b) => {
      const aTime = new Date(a.savedAt || 0).getTime();
      const bTime = new Date(b.savedAt || 0).getTime();
      return bTime - aTime;
    });
  }, [savedJobsRaw, savedScoredJobs, viewerOverrides]);

  const hiddenJobs = useMemo(() => {
    return mapJobsForDisplay(hiddenJobsRaw, hiddenScoredJobs, {
      viewerStateOverrides: viewerOverrides,
    }).sort((a, b) => {
      const aTime = new Date(a.hiddenAt || 0).getTime();
      const bTime = new Date(b.hiddenAt || 0).getTime();
      return bTime - aTime;
    });
  }, [hiddenJobsRaw, hiddenScoredJobs, viewerOverrides]);

  const visibleJobs =
    activeTab === TRACKER_TABS.SAVED ? savedJobs : hiddenJobs;
  const latestResume = trackerData?.resume || null;
  const parsedResume = latestResume?.parsed_json || null;
  const resumeSummary = parsedResume?.summary || {};
  const resumeSkills = parsedResume?.skills?.normalized || [];
  const resumeWarnings = latestResume?.parse_warnings || [];
  const cleanResumeWarnings = normalizeWarnings(resumeWarnings);
  const displayedResumeLocation = formatResumeLocation(
    parsedResume?.basics?.location
  );

  function resetPreferencesDraft() {
    setPreferencesDraft(DEFAULT_PREFERENCES);
  }

  async function handleToggleSave(job) {
    const jobId = job.id;
    const nextSaved = !job.isSaved;

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

      setSavedJobsRaw((current) => {
        if (nextSaved) {
          const alreadyExists = current.some((item) => item.id === jobId);
          if (alreadyExists) {
            return current;
          }
          return [job.rawBackendJob || job, ...current];
        }

        return current.filter((item) => item.id !== jobId);
      });
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "We could not update that saved job right now."
      );
    } finally {
      clearPendingAction(jobId, "saving");
    }
  }

  async function handleHideOrUnhide(job) {
    const jobId = job.id;
    const isCurrentlyHidden = Boolean(job.isHidden);

    updatePendingAction(jobId, { hiding: true });
    applyViewerOverride(jobId, {
      is_hidden: !isCurrentlyHidden,
      hidden_at: !isCurrentlyHidden ? new Date().toISOString() : null,
    });

    try {
      const result = isCurrentlyHidden
        ? await unhideJob(jobId)
        : await hideJob(jobId);

      const nextViewerState = result?.viewer_state ?? null;

      if (nextViewerState) {
        applyViewerOverride(jobId, nextViewerState);
      }

      if (isCurrentlyHidden) {
        setHiddenJobsRaw((current) =>
          current.filter((item) => item.id !== jobId)
        );
      } else {
        setHiddenJobsRaw((current) => {
          const alreadyExists = current.some((item) => item.id === jobId);
          if (alreadyExists) {
            return current;
          }
          return [job.rawBackendJob || job, ...current];
        });

        setSavedJobsRaw((current) =>
          current.filter((item) => item.id !== jobId)
        );
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "We could not update that hidden job right now."
      );
    } finally {
      clearPendingAction(jobId, "hiding");
    }
  }

  async function handleSavePreferences() {
    setIsSavingPreferences(true);
    setError("");

    try {
      const result = await updateTrackerPreferences(preferencesDraft);
      const nextPreferences = result?.preferences || preferencesDraft;

      setTrackerData((current) => ({
        ...current,
        preferences: nextPreferences,
      }));

      setResolvedUserProfile((current) => ({
        ...current,
        desiredLevels: nextPreferences.desired_levels?.length
          ? nextPreferences.desired_levels
          : ["entry-level", "junior"],
        preferredRoleTypes: nextPreferences.preferred_role_types || [],
        preferredWorkplaceTypes:
          nextPreferences.preferred_workplace_types || [],
        preferredLocations: nextPreferences.preferred_locations || [],
        isLgbtFriendlyOnly: Boolean(nextPreferences.is_lgbt_friendly_only),
      }));

      if (isMobile) {
        setIsPreferencesModalOpen(false);
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "We could not save your tracker preferences right now."
      );
    } finally {
      setIsSavingPreferences(false);
    }
  }

  async function handleResumeSaved(savedResumeUiState) {
    setIsResumeModalOpen(false);
    setError("");

    try {
      const freshTracker = await fetchTracker();
      const nextPreferences =
        freshTracker?.preferences || DEFAULT_PREFERENCES;

      setTrackerData(
        freshTracker && typeof freshTracker === "object"
          ? freshTracker
          : {
              preferences: DEFAULT_PREFERENCES,
              resume: null,
              stats: {
                saved_jobs_count: 0,
                hidden_jobs_count: 0,
              },
            }
      );

      setPreferencesDraft(nextPreferences);
      setResolvedUserProfile((current) => ({
        ...current,
        desiredLevels: nextPreferences.desired_levels?.length
          ? nextPreferences.desired_levels
          : ["entry-level", "junior"],
        preferredRoleTypes: nextPreferences.preferred_role_types || [],
        preferredWorkplaceTypes:
          nextPreferences.preferred_workplace_types || [],
        preferredLocations: nextPreferences.preferred_locations || [],
        skills:
          freshTracker?.resume?.parsed_json?.skills?.normalized ||
          freshTracker?.resume?.parsed_json?.summary?.top_skill_keywords ||
          current.skills ||
          [],
        isLgbtFriendlyOnly: Boolean(nextPreferences.is_lgbt_friendly_only),
      }));
    } catch (err) {
      setTrackerData((current) => ({
        ...current,
        resume: {
          ...(current.resume || {}),
          id: savedResumeUiState?.id || current.resume?.id || null,
          original_filename:
            savedResumeUiState?.name || current.resume?.original_filename,
          file_type:
            savedResumeUiState?.type ||
            current.resume?.file_type ||
            "application/pdf",
          parse_status: savedResumeUiState?.parseStatus || "pending",
          updated_at: savedResumeUiState?.uploadedAt || new Date().toISOString(),
          ats_tags:
            savedResumeUiState?.atsTags || current.resume?.ats_tags || [],
          parse_warnings: current.resume?.parse_warnings || [],
          parsed_json: current.resume?.parsed_json || null,
        },
      }));

      setError(
        err instanceof Error
          ? err.message
          : "Your resume uploaded, but we could not refresh tracker details yet."
      );
    }
  }

  function renderEmptyState() {
    if (activeTab === TRACKER_TABS.SAVED) {
      return (
        <div className="tracker-empty section-card">
          <h3 className="tracker-empty__title">No saved jobs yet</h3>
          <p className="tracker-empty__text">
            When you find a role worth circling back to, save it and it will
            land here.
          </p>
          <div className="tracker-empty__actions">
            <Link to="/jobs" className="button button--primary">
              Browse jobs
            </Link>
          </div>
        </div>
      );
    }

    return (
      <div className="tracker-empty section-card">
        <h3 className="tracker-empty__title">No hidden jobs right now</h3>
        <p className="tracker-empty__text">
          Hidden roles live here so your main feed stays cleaner and less
          repetitive.
        </p>
        <div className="tracker-empty__actions">
          <Link to="/jobs" className="button button--primary">
            Back to jobs
          </Link>
        </div>
      </div>
    );
  }

  if (authLoading) {
    return (
      <main className="tracker-page">
        <section className="section-pad">
          <div className="container">
            <div className="section-card tracker-status">
              <h1 className="tracker-status__title">Loading your tracker...</h1>
            </div>
          </div>
        </section>
      </main>
    );
  }

  if (!user) {
    return (
      <main className="tracker-page">
        <section className="section-pad">
          <div className="container">
            <div className="tracker-gate section-card">
              <span className="eyebrow-pill">Your Job Tracker</span>
              <h1 className="tracker-gate__title">Sign in to use your tracker</h1>
              <p className="tracker-gate__text">
                Saved jobs, preferences, and your latest resume all live here.
              </p>

              <div className="tracker-gate__actions">
                <button
                  type="button"
                  className="button button--primary"
                  onClick={() => navigate("/sign-in")}
                >
                  Sign in
                </button>

                <Link to="/jobs" className="button button--secondary">
                  Keep browsing
                </Link>
              </div>
            </div>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="tracker-page">
      <section className="section-pad">
        <div className="container tracker-stack">
          <div className="tracker-main-layout">
            {!isMobile ? (
              <aside className="tracker-sidebar">
                <TrackerPreferencesPanel
                  preferencesDraft={preferencesDraft}
                  setPreferencesDraft={setPreferencesDraft}
                  isSavingPreferences={isSavingPreferences}
                  onSavePreferences={handleSavePreferences}
                  onResetPreferences={resetPreferencesDraft}
                />
              </aside>
            ) : null}

            <div className="tracker-content">
              <div className="tracker-stats">
                <article className="tracker-stat tracker-stat--saved section-card">
                  <span className="tracker-stat__label">Saved</span>
                  <strong className="tracker-stat__value">
                    {trackerData?.stats?.saved_jobs_count ?? savedJobs.length}
                  </strong>
                </article>

                <article className="tracker-stat tracker-stat--hidden section-card">
                  <span className="tracker-stat__label">Hidden</span>
                  <strong className="tracker-stat__value">
                    {trackerData?.stats?.hidden_jobs_count ?? hiddenJobs.length}
                  </strong>
                </article>

                <article className="tracker-stat tracker-stat--resume section-card">
                  <span className="tracker-stat__label">Resume status</span>
                  <strong className="tracker-stat__value">
                    {latestResume?.parse_status
                      ? titleCase(latestResume.parse_status)
                      : "None"}
                  </strong>
                </article>

                  <button
                    type="button"
                    className="tracker-stat tracker-stat--preferences section-card"
                    onClick={() => setIsPreferencesModalOpen(true)}
                    aria-label="Edit tracker preferences"
                  >
                    <span className="tracker-stat__label">Preferences</span>
                    <strong className="tracker-stat__value">Edit →</strong>
                  </button>
              </div>

              <section className="section-card tracker-resume-card">
                <div className="tracker-section-head">
                  <div>
                    <p className="tracker-stat__label">Latest resume</p>
                    <h2 className="tracker-empty__title">
                      {latestResume?.original_filename || "No resume uploaded yet"}
                    </h2>
                  </div>

                  <button
                    type="button"
                    className="button button--secondary tracker-resume-card__button"
                    onClick={() => setIsResumeModalOpen(true)}
                  >
                    {latestResume ? "Replace resume" : "Upload resume"}
                  </button>
                </div>

                <p className="tracker-empty__text">
                  {latestResume
                    ? `Last updated ${formatDate(
                        latestResume.updated_at
                      )} • ${titleCase(latestResume.parse_status || "pending")}`
                    : "Upload a resume so EarlyBloom can explain what your current resume is signaling."}
                </p>
              </section>

              <section className="section-card tracker-signals-card">
                <div className="tracker-section-head">
                  <div>
                    <p className="tracker-stat__label">Resume signals</p>
                    <h2 className="tracker-empty__title">
                      What your resume is currently displaying
                    </h2>
                  </div>
                </div>

                {parsedResume ? (
                  <div className="tracker-signals">
                    <div className="tracker-signals__row">
                      <span className="tracker-stat__label">Seniority</span>
                      <strong>
                        {titleCase(resumeSummary.seniority || "unknown")}
                      </strong>
                    </div>

                    <div className="tracker-signals__row">
                      <span className="tracker-stat__label">
                        Estimated experience
                      </span>
                      <strong>
                        {typeof resumeSummary.estimated_years_experience ===
                        "number"
                          ? `${resumeSummary.estimated_years_experience} years`
                          : "Not detected"}
                      </strong>
                    </div>

                    <div className="tracker-signals__row">
                      <span className="tracker-stat__label">
                        Likely role signals
                      </span>
                      <strong>
                        {(resumeSummary.primary_role_signals || [])
                          .map(titleCase)
                          .join(", ") || "Not detected"}
                      </strong>
                    </div>

                    <div className="tracker-signals__row">
                      <span className="tracker-stat__label">Top skills</span>
                      <strong>
                        {resumeSkills.length > 0
                          ? resumeSkills
                              .slice(0, 12)
                              .map(titleCase)
                              .join(", ")
                          : "Not detected"}
                      </strong>
                    </div>

                    <div className="tracker-signals__row">
                      <span className="tracker-stat__label">
                        Inferred location
                      </span>
                      <strong>{displayedResumeLocation}</strong>
                    </div>

                    {cleanResumeWarnings.length > 0 ? (
                      <div className="tracker-signals__warnings">
                        <span className="tracker-stat__label">Parser notes</span>
                        <ul>
                          {cleanResumeWarnings.map((warning) => (
                            <li key={warning}>{warning}</li>
                          ))}
                        </ul>
                      </div>
                    ) : null}
                  </div>
                ) : (
                  <p className="tracker-empty__text">
                    No parsed resume data yet. Once you upload a resume, this
                    section will explain what EarlyBloom is seeing instead of
                    making users manually choose ATS tags.
                  </p>
                )}
              </section>

              <div
                className="tracker-tabs section-card"
                role="tablist"
                aria-label="Tracker sections"
              >
                <button
                  type="button"
                  role="tab"
                  aria-selected={activeTab === TRACKER_TABS.SAVED}
                  className={`tracker-tab ${
                    activeTab === TRACKER_TABS.SAVED
                      ? "tracker-tab--active"
                      : ""
                  }`}
                  onClick={() => setActiveTab(TRACKER_TABS.SAVED)}
                >
                  Saved Jobs
                </button>

                <button
                  type="button"
                  role="tab"
                  aria-selected={activeTab === TRACKER_TABS.HIDDEN}
                  className={`tracker-tab ${
                    activeTab === TRACKER_TABS.HIDDEN
                      ? "tracker-tab--active"
                      : ""
                  }`}
                  onClick={() => setActiveTab(TRACKER_TABS.HIDDEN)}
                >
                  Hidden Jobs
                </button>
              </div>

              {error ? (
                <div
                  className="section-card tracker-error"
                  role="alert"
                  aria-live="polite"
                >
                  <p className="tracker-error__text">{error}</p>
                </div>
              ) : null}

              {isLoading ? (
                <div
                  className="section-card tracker-status"
                  role="status"
                  aria-live="polite"
                >
                  <p className="tracker-status__title">
                    Loading tracker jobs...
                  </p>
                </div>
              ) : visibleJobs.length === 0 ? (
                renderEmptyState()
              ) : (
                <div className="tracker-list">
                  {visibleJobs.map((job) => (
                    <JobCard
                      key={`${activeTab}-${job.id}`}
                      job={job}
                      onOpenDetails={() => navigate("/jobs")}
                      onSaveToggle={handleToggleSave}
                      onHide={handleHideOrUnhide}
                      isSavePending={Boolean(pendingActions[job.id]?.saving)}
                      isHidePending={Boolean(pendingActions[job.id]?.hiding)}
                      hideLabel={
                        activeTab === TRACKER_TABS.HIDDEN ? "Unhide" : "Hide"
                      }
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      <CommonModal
        isOpen={isPreferencesModalOpen}
        title="Tracker preferences"
        onClose={() => setIsPreferencesModalOpen(false)}
        size="md"
        iconImage={BloombugAppIcon}
        iconAlt="EarlyBloom Bloombug icon"
      >
        <TrackerPreferencesPanel
          preferencesDraft={preferencesDraft}
          setPreferencesDraft={setPreferencesDraft}
          isSavingPreferences={isSavingPreferences}
          onSavePreferences={handleSavePreferences}
          onResetPreferences={resetPreferencesDraft}
        />
      </CommonModal>

      <ResumeUploadModal
        isOpen={isResumeModalOpen}
        onClose={() => setIsResumeModalOpen(false)}
        onResumeSaved={handleResumeSaved}
        resumeFile={
          latestResume
            ? {
                id: latestResume.id,
                name: latestResume.original_filename,
                type: latestResume.file_type,
                parseStatus: latestResume.parse_status,
                uploadedAt: latestResume.updated_at,
                atsTags: latestResume.ats_tags || [],
              }
            : null
        }
      />
    </main>
  );
}

export default Tracker;