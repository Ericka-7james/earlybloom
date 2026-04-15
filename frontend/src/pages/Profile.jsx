import React, { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import CommonModal from "../components/common/CommonModal.jsx";
import CommonLoadingModal from "../components/common/CommonLoadingModal.jsx";
import BloombugAppIcon from "../assets/bloombug/BloombugAppIcon.png";
import { useAuth } from "../hooks/useAuth";
import { fetchTracker } from "../lib/tracker/trackerApi";
import "../styles/components/profile.css";

const DEFAULT_PROFILE = {
  display_name: null,
  career_interests: [],
  desired_levels: ["entry-level", "junior"],
  preferred_role_types: [],
  preferred_workplace_types: [],
  preferred_locations: [],
  is_lgbt_friendly_only: false,
};

const DEFAULT_PREFERENCES = {
  desired_levels: ["entry-level", "junior"],
  preferred_role_types: [],
  preferred_workplace_types: [],
  preferred_locations: [],
  is_lgbt_friendly_only: false,
};

const DEFAULT_TRACKER_DATA = {
  profile: DEFAULT_PROFILE,
  preferences: DEFAULT_PREFERENCES,
  resume: null,
  stats: {
    saved_jobs_count: 0,
    hidden_jobs_count: 0,
  },
};

function titleCase(value) {
  return String(value || "")
    .split(/[\s_-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatList(values, emptyLabel = "Not set yet") {
  if (!Array.isArray(values) || values.length === 0) {
    return emptyLabel;
  }

  return values.map(titleCase).join(", ");
}

function getFallbackDisplayName(user) {
  return (
    user?.user_metadata?.display_name ||
    user?.user_metadata?.full_name ||
    user?.user_metadata?.name ||
    user?.email?.split("@")[0] ||
    "EarlyBloom user"
  );
}

function getResolvedDisplayName(profile, user) {
  const profileDisplayName =
    profile?.display_name && String(profile.display_name).trim();

  return profileDisplayName || getFallbackDisplayName(user);
}

function formatResumeStatus(resume) {
  if (!resume?.parse_status) {
    return "No resume uploaded";
  }

  return titleCase(resume.parse_status);
}

function getFriendlyProfileError(error) {
  const message =
    error instanceof Error
      ? error.message
      : "Profile details could not be loaded right now.";

  const lowered = message.toLowerCase();

  if (
    lowered.includes("please sign in before saving your resume") ||
    lowered.includes("sign in before saving your resume")
  ) {
    return "";
  }

  return message;
}

function normalizeTrackerPayload(payload) {
  if (!payload || typeof payload !== "object") {
    return DEFAULT_TRACKER_DATA;
  }

  return {
    profile: {
      ...DEFAULT_PROFILE,
      ...(payload.profile && typeof payload.profile === "object"
        ? payload.profile
        : {}),
    },
    preferences: {
      ...DEFAULT_PREFERENCES,
      ...(payload.preferences && typeof payload.preferences === "object"
        ? payload.preferences
        : {}),
    },
    resume:
      payload.resume && typeof payload.resume === "object" ? payload.resume : null,
    stats: {
      ...DEFAULT_TRACKER_DATA.stats,
      ...(payload.stats && typeof payload.stats === "object" ? payload.stats : {}),
    },
  };
}

function useViewportWidth() {
  const [viewportWidth, setViewportWidth] = useState(() =>
    typeof window === "undefined" ? 1280 : window.innerWidth
  );

  useEffect(() => {
    if (typeof window === "undefined") {
      return undefined;
    }

    function handleResize() {
      setViewportWidth(window.innerWidth);
    }

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  return viewportWidth;
}

function Profile() {
  const navigate = useNavigate();
  const { user, loading: authLoading, handleSignOut } = useAuth();
  const viewportWidth = useViewportWidth();
  const isMobile = viewportWidth < 768;

  const [trackerData, setTrackerData] = useState(DEFAULT_TRACKER_DATA);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [isSignOutModalOpen, setIsSignOutModalOpen] = useState(false);
  const [isSigningOut, setIsSigningOut] = useState(false);
  const [isPreferencesModalOpen, setIsPreferencesModalOpen] = useState(false);

  useEffect(() => {
    let isMounted = true;

    async function loadProfileData() {
      if (!user) {
        setTrackerData(DEFAULT_TRACKER_DATA);
        setError("");
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      setError("");

      try {
        const tracker = await fetchTracker();

        if (!isMounted) {
          return;
        }

        setTrackerData(normalizeTrackerPayload(tracker));
      } catch (err) {
        if (!isMounted) {
          return;
        }

        setTrackerData(DEFAULT_TRACKER_DATA);
        setError(getFriendlyProfileError(err));
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadProfileData();

    return () => {
      isMounted = false;
    };
  }, [user]);

  const profile = trackerData?.profile || DEFAULT_PROFILE;
  const preferences = trackerData?.preferences || DEFAULT_PREFERENCES;
  const latestResume = trackerData?.resume || null;

  const displayName = useMemo(
    () => getResolvedDisplayName(profile, user),
    [profile, user]
  );

  async function handleConfirmSignOut() {
    setIsSigningOut(true);

    try {
      await handleSignOut();
      setIsSignOutModalOpen(false);
      navigate("/");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "We could not sign you out right now."
      );
    } finally {
      setIsSigningOut(false);
    }
  }

  function renderPreferencesContent() {
    return (
      <div className="settings-section">
        <div className="settings-section__header">
          <p className="section-label">Preferences</p>
          <h2 className="card-title">Search and profile defaults</h2>
          <p className="card-copy">
            These reflect your durable account setup and the same
            preference language used by Tracker.
          </p>
        </div>

        <div className="settings-section__body">
          <div className="settings-section__group">
            <div className="form-field">
              <p className="form-field__label">Display name</p>
              <p className="card-copy">{displayName}</p>
            </div>

            <div className="form-field">
              <p className="form-field__label">Career interests</p>
              <p className="card-copy">
                {formatList(profile.career_interests, "Not set yet")}
              </p>
            </div>

            <div className="form-field">
              <p className="form-field__label">Preferred job levels</p>
              <p className="card-copy">
                {formatList(
                  preferences.desired_levels?.length
                    ? preferences.desired_levels
                    : profile.desired_levels,
                  "Entry-level, Junior"
                )}
              </p>
            </div>

            <div className="form-field">
              <p className="form-field__label">Preferred role types</p>
              <p className="card-copy">
                {formatList(
                  preferences.preferred_role_types?.length
                    ? preferences.preferred_role_types
                    : profile.preferred_role_types,
                  "Not set yet"
                )}
              </p>
            </div>

            <div className="form-field">
              <p className="form-field__label">Location preferences</p>
              <p className="card-copy">
                {formatList(
                  preferences.preferred_locations?.length
                    ? preferences.preferred_locations
                    : profile.preferred_locations,
                  "Not set yet"
                )}
              </p>
            </div>

            <div className="form-field">
              <p className="form-field__label">Remote / hybrid preference</p>
              <p className="card-copy">
                {formatList(
                  preferences.preferred_workplace_types?.length
                    ? preferences.preferred_workplace_types
                    : profile.preferred_workplace_types,
                  "Not set yet"
                )}
              </p>
            </div>

            <div className="form-field">
              <p className="form-field__label">LGBTQ-friendly only</p>
              <p className="card-copy">
                {(typeof preferences.is_lgbt_friendly_only === "boolean"
                  ? preferences.is_lgbt_friendly_only
                  : profile.is_lgbt_friendly_only)
                  ? "On"
                  : "Off"}
              </p>
            </div>
          </div>

          <div className="settings-section__actions">
            <Link to="/tracker" className="button button--secondary">
              Edit in tracker
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (authLoading) {
    return (
      <>
        <main className="app-page profile-page" aria-hidden="true" />
        <CommonLoadingModal
          isOpen
          message="Growing your profile..."
          label="Loading your profile"
        />
      </>
    );
  }

  if (!user) {
    return (
      <main className="app-page profile-page">
        <section className="section-pad">
          <div className="container--product">
            <div className="empty-state-card empty-state-card--centered">
              <div className="empty-state-card__header">
                <span className="eyebrow-pill">Your Profile</span>
                <h1 className="section-title">Sign in to view your profile</h1>
                <p className="section-copy">
                  Your preferences, resume status, and tracker shortcuts live here.
                </p>
              </div>

              <div className="empty-state-card__actions">
                <button
                  type="button"
                  className="button button--primary"
                  onClick={() => navigate("/sign-in")}
                >
                  Sign in
                </button>

                <Link to="/jobs" className="button button--secondary">
                  Browse jobs
                </Link>
              </div>
            </div>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="app-page profile-page">
      <section className="section-pad">
        <div className="container--product app-content-stack">
          <section className="app-page__hero">
            <div className="hero-card app-page__hero-card profile-hero">
              <div className="app-page__hero-content">
                <span className="eyebrow-pill">Profile</span>

                <div className="stack-sm">
                  <h1 className="section-title">{displayName}</h1>
                  <p className="section-copy">
                    Your EarlyBloom home base for defaults, resume signals, and
                    the tracker shortcuts you will use most.
                  </p>
                </div>

                <div className="app-page__hero-meta">
                  <span className="tag-chip">{user.email}</span>
                  <span className="tag-chip">
                    Resume: {formatResumeStatus(latestResume)}
                  </span>
                </div>

                <div className="app-page__hero-actions">
                  <Link to="/tracker" className="button button--primary">
                    Open tracker
                  </Link>
                  <Link to="/jobs" className="button button--secondary">
                    Browse jobs
                  </Link>
                </div>
              </div>

              <div className="app-page__hero-aside profile-hero__aside">
                <div className="info-panel info-panel--soft">
                  <div className="info-panel__header">
                    <p className="section-label">Account snapshot</p>
                    <h2 className="card-title">What is set up right now</h2>
                  </div>

                  <div className="info-panel__content">
                    <p className="card-copy">
                      Preferred levels:{" "}
                      {formatList(
                        preferences.desired_levels?.length
                          ? preferences.desired_levels
                          : profile.desired_levels,
                        "Entry-level, Junior"
                      )}
                    </p>
                    <p className="card-copy">
                      Workplace:{" "}
                      {formatList(
                        preferences.preferred_workplace_types?.length
                          ? preferences.preferred_workplace_types
                          : profile.preferred_workplace_types,
                        "Not set yet"
                      )}
                    </p>
                    <p className="card-copy">
                      Locations:{" "}
                      {formatList(
                        preferences.preferred_locations?.length
                          ? preferences.preferred_locations
                          : profile.preferred_locations,
                        "Not set yet"
                      )}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section className="app-section">
            <div className="app-section-heading">
              <p className="section-label">Stats</p>
              <h2 className="card-title">Your current snapshot</h2>
            </div>

            <div className="app-grid app-grid--stats">
              <article className="compact-stat-card">
                <p className="compact-stat-card__label">Saved jobs</p>
                <p className="compact-stat-card__value">
                  {trackerData?.stats?.saved_jobs_count ?? 0}
                </p>
                <p className="compact-stat-card__meta">
                  Roles you bookmarked to revisit.
                </p>
              </article>

              <article className="compact-stat-card">
                <p className="compact-stat-card__label">Hidden jobs</p>
                <p className="compact-stat-card__value">
                  {trackerData?.stats?.hidden_jobs_count ?? 0}
                </p>
                <p className="compact-stat-card__meta">
                  Roles removed from your main feed.
                </p>
              </article>

              <article className="compact-stat-card">
                <p className="compact-stat-card__label">Resume status</p>
                <p className="compact-stat-card__value">
                  {latestResume?.parse_status
                    ? titleCase(latestResume.parse_status)
                    : "None"}
                </p>
                <p className="compact-stat-card__meta">
                  Latest parser state for your uploaded resume.
                </p>
              </article>

              <article className="compact-stat-card">
                <p className="compact-stat-card__label">LGBTQ-friendly only</p>
                <p className="compact-stat-card__value">
                  {(typeof preferences.is_lgbt_friendly_only === "boolean"
                    ? preferences.is_lgbt_friendly_only
                    : profile.is_lgbt_friendly_only)
                    ? "On"
                    : "Off"}
                </p>
                <p className="compact-stat-card__meta">
                  Whether this preference is active in your defaults.
                </p>
              </article>
            </div>
          </section>

          <section className="app-split-layout app-split-layout--balanced">
            <div className="app-content-stack app-content-stack--tight">
              {!isMobile ? (
                <section className="app-panel-card">
                  {renderPreferencesContent()}
                </section>
              ) : (
                <section className="app-panel-card">
                  <div className="settings-section">
                    <div className="settings-section__header">
                      <p className="section-label">Preferences</p>
                      <h2 className="card-title">Search and profile defaults</h2>
                      <p className="card-copy">
                        Open a cleaner modal view instead of scrolling through a
                        long mobile card.
                      </p>
                    </div>

                    <div className="settings-section__body">
                      <div className="settings-section__actions">
                        <button
                          type="button"
                          className="button button--secondary"
                          onClick={() => setIsPreferencesModalOpen(true)}
                        >
                          View preferences
                        </button>
                        <Link to="/tracker" className="button button--secondary">
                          Edit in tracker
                        </Link>
                      </div>
                    </div>
                  </div>
                </section>
              )}
            </div>

            <div className="app-content-stack app-content-stack--tight">
              <section className="app-panel-card">
                <div className="settings-section">
                  <div className="settings-section__header">
                    <p className="section-label">Shortcuts</p>
                    <h2 className="card-title">Jump back into your flow</h2>
                  </div>

                  <div className="settings-section__body">
                    <div className="settings-section__actions profile-shortcuts">
                      <Link to="/tracker" className="button button--primary">
                        Open tracker
                      </Link>
                      <Link to="/jobs" className="button button--secondary">
                        Open jobs
                      </Link>
                    </div>
                  </div>
                </div>
              </section>

              <section className="app-panel-card app-panel-card--soft">
                <div className="settings-section">
                  <div className="settings-section__header">
                    <p className="section-label">Resume</p>
                    <h2 className="card-title">Your latest upload</h2>
                    <p className="card-copy">
                      Manage your resume parsing and uploads from Tracker.
                    </p>
                  </div>

                  <div className="settings-section__body">
                    <div className="info-panel">
                      <div className="info-panel__content">
                        <p className="card-copy">
                          Current file:{" "}
                          {latestResume?.original_filename || "No resume uploaded yet"}
                        </p>
                        <p className="card-copy">
                          Status: {formatResumeStatus(latestResume)}
                        </p>
                      </div>
                    </div>

                    <div className="settings-section__actions">
                      <Link to="/tracker" className="button button--secondary">
                        Manage resume in tracker
                      </Link>
                    </div>
                  </div>
                </div>
              </section>

              <section className="app-panel-card app-panel-card--soft">
                <div className="settings-section">
                  <div className="settings-section__header">
                    <p className="section-label">Account actions</p>
                    <h2 className="card-title">Sign out</h2>
                    <p className="card-copy">
                      End your current session on this device.
                    </p>
                  </div>

                  <div className="settings-section__body">
                    <div className="settings-section__actions profile-account-actions">
                      <button
                        type="button"
                        className="button button--secondary"
                        onClick={() => setIsSignOutModalOpen(true)}
                      >
                        Sign out
                      </button>
                    </div>
                  </div>
                </div>
              </section>

              {error ? (
                <div className="message-card message-card--warning">
                  <p className="message-card__title">Some profile details are missing</p>
                  <p className="message-card__copy">{error}</p>
                </div>
              ) : null}
            </div>
          </section>
        </div>
      </section>

      <CommonLoadingModal
        isOpen={isLoading}
        message="Growing your profile..."
        label="Refreshing profile details"
      />

      <CommonModal
        isOpen={isPreferencesModalOpen}
        title="Profile preferences"
        onClose={() => setIsPreferencesModalOpen(false)}
        size="md"
        iconImage={BloombugAppIcon}
        iconAlt="EarlyBloom Bloombug icon"
      >
        {renderPreferencesContent()}
      </CommonModal>

      <CommonModal
        isOpen={isSignOutModalOpen}
        title="Sign out"
        onClose={() => setIsSignOutModalOpen(false)}
        size="sm"
        iconImage={BloombugAppIcon}
        iconAlt="EarlyBloom Bloombug icon"
      >
        <div className="form-stack">
          <p className="card-copy">
            You are about to sign out of EarlyBloom on this device.
          </p>

          <div className="form-actions form-actions--end">
            <button
              type="button"
              className="button button--secondary"
              onClick={() => setIsSignOutModalOpen(false)}
              disabled={isSigningOut}
            >
              Cancel
            </button>

            <button
              type="button"
              className="button button--primary"
              onClick={handleConfirmSignOut}
              disabled={isSigningOut}
            >
              {isSigningOut ? "Signing out..." : "Sign out"}
            </button>
          </div>
        </div>
      </CommonModal>
    </main>
  );
}

export default Profile;