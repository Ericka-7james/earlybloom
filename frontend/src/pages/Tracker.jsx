import React, { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import JobCard from "../components/jobs/JobCard.jsx";
import { useAuth } from "../hooks/useAuth";
import {
  fetchHiddenJobs,
  fetchResolvedJobProfile,
  fetchSavedJobs,
  hideJob,
  saveJob,
  unhideJob,
  unsaveJob,
} from "../lib/jobs/jobsApi";
import scoreJobsForUser from "../lib/jobs/scoreJobsForUser";
import mapJobsForDisplay from "../lib/jobs/mapJobsForDisplay";
import "../styles/components/tracker.css";

const TRACKER_TABS = {
  SAVED: "saved",
  HIDDEN: "hidden",
};

function Tracker() {
  const navigate = useNavigate();
  const { user, loading: authLoading } = useAuth();

  const [activeTab, setActiveTab] = useState(TRACKER_TABS.SAVED);
  const [savedJobsRaw, setSavedJobsRaw] = useState([]);
  const [hiddenJobsRaw, setHiddenJobsRaw] = useState([]);
  const [resolvedUserProfile, setResolvedUserProfile] = useState({
    desiredLevels: ["entry-level", "junior"],
    preferredRoleTypes: [],
    preferredWorkplaceTypes: [],
    skills: [],
    isLgbtFriendlyOnly: false,
  });
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
        setIsLoading(false);
        setError("");
        return;
      }

      setIsLoading(true);
      setError("");

      try {
        const [savedJobs, hiddenJobs, profile] = await Promise.all([
          fetchSavedJobs({ signal: controller.signal }),
          fetchHiddenJobs({ signal: controller.signal }),
          fetchResolvedJobProfile({ signal: controller.signal }),
        ]);

        if (!isMounted || controller.signal.aborted) {
          return;
        }

        setSavedJobsRaw(Array.isArray(savedJobs) ? savedJobs : []);
        setHiddenJobsRaw(Array.isArray(hiddenJobs) ? hiddenJobs : []);
        setResolvedUserProfile(
          profile && typeof profile === "object"
            ? {
                desiredLevels: ["entry-level", "junior"],
                preferredRoleTypes: [],
                preferredWorkplaceTypes: [],
                skills: [],
                isLgbtFriendlyOnly: false,
                ...profile,
              }
            : {
                desiredLevels: ["entry-level", "junior"],
                preferredRoleTypes: [],
                preferredWorkplaceTypes: [],
                skills: [],
                isLgbtFriendlyOnly: false,
              }
        );
      } catch (err) {
        if (!isMounted || err?.name === "AbortError") {
          return;
        }

        setSavedJobsRaw([]);
        setHiddenJobsRaw([]);
        setError(
          err instanceof Error
            ? err.message
            : "Something went wrong while loading your tracker."
        );
      } finally {
        if (isMounted && !controller.signal.aborted) {
          setIsLoading(false);
        }
      }
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

  const visibleJobs = activeTab === TRACKER_TABS.SAVED ? savedJobs : hiddenJobs;

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
        setHiddenJobsRaw((current) => current.filter((item) => item.id !== jobId));
      } else {
        setHiddenJobsRaw((current) => {
          const alreadyExists = current.some((item) => item.id === jobId);
          if (alreadyExists) {
            return current;
          }
          return [job.rawBackendJob || job, ...current];
        });

        setSavedJobsRaw((current) => current.filter((item) => item.id !== jobId));
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
                Saved jobs and hidden jobs are tied to your account, so they are
                ready when you come back.
              </p>

              <div className="tracker-gate__actions">
                <button
                  type="button"
                  className="button button--primary"
                  onClick={() => navigate("/sign-in")}
                >
                  Sign in
                </button>

                <Link to="/jobs" className="jobs-chip">
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
          <div className="tracker-hero section-card">
            <span className="eyebrow-pill">Your Job Tracker</span>
            <h1 className="tracker-hero__title">Keep the promising ones close</h1>
            <p className="tracker-hero__text">
              Saved jobs help you revisit strong leads. Hidden jobs keep your
              feed from turning into wallpaper.
            </p>
          </div>

          <div className="tracker-stats">
            <article className="tracker-stat section-card">
              <span className="tracker-stat__label">Saved</span>
              <strong className="tracker-stat__value">{savedJobs.length}</strong>
            </article>

            <article className="tracker-stat section-card">
              <span className="tracker-stat__label">Hidden</span>
              <strong className="tracker-stat__value">{hiddenJobs.length}</strong>
            </article>

            <article className="tracker-stat section-card">
              <span className="tracker-stat__label">Tracker status</span>
              <strong className="tracker-stat__value">Growing</strong>
            </article>
          </div>

          <div className="tracker-tabs section-card" role="tablist" aria-label="Tracker sections">
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === TRACKER_TABS.SAVED}
              className={`tracker-tab ${
                activeTab === TRACKER_TABS.SAVED ? "tracker-tab--active" : ""
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
                activeTab === TRACKER_TABS.HIDDEN ? "tracker-tab--active" : ""
              }`}
              onClick={() => setActiveTab(TRACKER_TABS.HIDDEN)}
            >
              Hidden Jobs
            </button>
          </div>

          {error ? (
            <div className="section-card tracker-error" role="alert" aria-live="polite">
              <p className="tracker-error__text">{error}</p>
            </div>
          ) : null}

          {isLoading ? (
            <div className="section-card tracker-status" role="status" aria-live="polite">
              <p className="tracker-status__title">Loading tracker jobs...</p>
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
                  hideLabel={activeTab === TRACKER_TABS.HIDDEN ? "Unhide" : "Hide"}
                />
              ))}
            </div>
          )}
        </div>
      </section>
    </main>
  );
}

export default Tracker;