// frontend/src/hooks/jobs/useJobsPageState.js
/**
 * @fileoverview Shared state and behavior for the Jobs page.
 *
 * This hook centralizes:
 * - jobs data loading and scoring
 * - resume UI state hydration
 * - filters and pagination
 * - save/hide mutations
 * - modal state and handlers
 *
 * The page component can stay focused on layout and composition.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import scoreJobsForUser from "../../lib/jobs/scoreJobsForUser";
import mapJobsForDisplay from "../../lib/jobs/mapJobsForDisplay";
import { readCachedResumeUiState } from "../../lib/resumes";
import { fetchTracker } from "../../lib/tracker/trackerApi";
import { useJobs } from "../useJobs";
import { useAuth } from "../useAuth";
import { hideJob, saveJob, unsaveJob } from "../../lib/jobs/jobsApi";
import {
  DEFAULT_SELECTED_EXPERIENCE_LEVELS,
  filterJobs,
  getFilterSummary,
  getActiveFilterTags,
  getAvailableSkillOptions,
} from "../../lib/jobs/jobFilters";

const WELCOME_MODAL_PENDING_KEY = "earlybloom_welcome_modal_pending";
const RESUME_MODAL_DISMISSED_KEY = "earlybloom_resume_modal_dismissed";
const JOBS_PER_PAGE = 12;

/**
 * Returns whether browser storage is available.
 *
 * @returns {boolean} True when storage can be used.
 */
function canUseBrowserStorage() {
  return typeof window !== "undefined";
}

/**
 * Reads a value from session storage safely.
 *
 * @param {string} key Storage key.
 * @returns {string | null} Stored value.
 */
function readSessionStorageValue(key) {
  if (!canUseBrowserStorage()) {
    return null;
  }

  try {
    return window.sessionStorage.getItem(key);
  } catch {
    return null;
  }
}

/**
 * Writes a value to session storage safely.
 *
 * @param {string} key Storage key.
 * @param {string} value Storage value.
 * @returns {void}
 */
function writeSessionStorageValue(key, value) {
  if (!canUseBrowserStorage()) {
    return;
  }

  try {
    window.sessionStorage.setItem(key, value);
  } catch {
    // Ignore storage failures.
  }
}

/**
 * Removes a value from session storage safely.
 *
 * @param {string} key Storage key.
 * @returns {void}
 */
function removeSessionStorageValue(key) {
  if (!canUseBrowserStorage()) {
    return;
  }

  try {
    window.sessionStorage.removeItem(key);
  } catch {
    // Ignore storage failures.
  }
}

/**
 * Returns copy for login-required actions.
 *
 * @param {"save"|"hide"|"resume"} intent Action intent.
 * @returns {{eyebrow:string,title:string,body:string}} Modal content.
 */
function getLoginRequiredContent(intent) {
  switch (intent) {
    case "save":
      return {
        eyebrow: "Save jobs to come back to them later.",
        title: "Sign in to save jobs",
        body: "Saved roles live on your tracker so you can return to strong leads without digging through the feed again.",
      };
    case "hide":
      return {
        eyebrow: "Hide jobs you do not want to keep seeing.",
        title: "Sign in to hide jobs",
        body: "Signing in lets EarlyBloom remember the jobs you have passed on and keep the feed cleaner.",
      };
    case "resume":
    default:
      return {
        eyebrow: "Resume upload is available after sign in.",
        title: "Sign in to upload your resume",
        body: "Adding your resume helps EarlyBloom personalize skills and fit signals around your background.",
      };
  }
}

/**
 * Tracks viewport width for responsive pagination behavior.
 *
 * @returns {number} Current viewport width.
 */
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

    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  return viewportWidth;
}

/**
 * Returns a compact pagination config for a viewport width.
 *
 * @param {number} viewportWidth Current viewport width.
 * @returns {{nearStartCount:number,middleNeighborCount:number,nearEndCount:number}}
 * Pagination display config.
 */
function getPaginationConfig(viewportWidth) {
  if (viewportWidth <= 375) {
    return {
      nearStartCount: 2,
      middleNeighborCount: 0,
      nearEndCount: 2,
    };
  }

  if (viewportWidth <= 600) {
    return {
      nearStartCount: 4,
      middleNeighborCount: 0,
      nearEndCount: 2,
    };
  }

  if (viewportWidth <= 875) {
    return {
      nearStartCount: 2,
      middleNeighborCount: 0,
      nearEndCount: 2,
    };
  }

  if (viewportWidth >= 1024) {
    return {
      nearStartCount: 7,
      middleNeighborCount: 1,
      nearEndCount: 3,
    };
  }

  return {
    nearStartCount: 5,
    middleNeighborCount: 1,
    nearEndCount: 4,
  };
}

/**
 * Returns visible pagination items.
 *
 * @param {number} currentPage Current page number.
 * @param {number} totalPages Total number of pages.
 * @param {number} viewportWidth Current viewport width.
 * @returns {(number|string)[]} Visible page items.
 */
function getVisiblePageNumbers(currentPage, totalPages, viewportWidth) {
  if (totalPages <= 1) {
    return [1];
  }

  const {
    nearStartCount,
    middleNeighborCount,
    nearEndCount,
  } = getPaginationConfig(viewportWidth);

  const pages = new Set([1, totalPages]);

  if (currentPage <= nearStartCount) {
    for (let page = 1; page <= Math.min(totalPages, nearStartCount); page += 1) {
      pages.add(page);
    }
  } else if (currentPage >= totalPages - nearEndCount + 1) {
    for (
      let page = Math.max(1, totalPages - nearEndCount + 1);
      page <= totalPages;
      page += 1
    ) {
      pages.add(page);
    }
  } else {
    pages.add(currentPage);

    for (
      let page = currentPage - middleNeighborCount;
      page <= currentPage + middleNeighborCount;
      page += 1
    ) {
      if (page > 1 && page < totalPages) {
        pages.add(page);
      }
    }
  }

  const sortedPages = Array.from(pages).sort((a, b) => a - b);
  const result = [];

  for (let index = 0; index < sortedPages.length; index += 1) {
    const pageNumber = sortedPages[index];
    const previousPage = sortedPages[index - 1];

    if (index > 0 && pageNumber - previousPage > 1) {
      result.push("...");
    }

    result.push(pageNumber);
  }

  return result;
}

/**
 * Maps tracker resume data into resume UI state.
 *
 * @param {object | null} resume Tracker resume data.
 * @returns {object | null} Resume UI state.
 */
function buildResumeUiStateFromTrackerResume(resume) {
  if (!resume || typeof resume !== "object") {
    return null;
  }

  return {
    id: resume.id || null,
    name: resume.original_filename || "Saved resume",
    size: null,
    type: resume.file_type || "application/pdf",
    uploadedAt: resume.updated_at || null,
    parseStatus: resume.parse_status || "pending",
    atsTags: Array.isArray(resume.ats_tags) ? resume.ats_tags : [],
    isLocalOnly: false,
  };
}

/**
 * Shared Jobs page state hook.
 *
 * @returns {object} Jobs page state and actions.
 */
export function useJobsPageState() {
  const navigate = useNavigate();
  const { user, loading: authLoading } = useAuth();
  const viewerKey = user?.id ? `user:${user.id}` : "guest";
  const viewportWidth = useViewportWidth();

  const [activeJob, setActiveJob] = useState(null);
  const [isFiltersModalOpen, setIsFiltersModalOpen] = useState(false);
  const [isLoginRequiredModalOpen, setIsLoginRequiredModalOpen] =
    useState(false);
  const [loginRequiredIntent, setLoginRequiredIntent] = useState("resume");
  const [resumeFile, setResumeFile] = useState(() => readCachedResumeUiState());
  const [trackerResume, setTrackerResume] = useState(null);
  const [locationQuery, setLocationQuery] = useState("");
  const [selectedExperienceLevels, setSelectedExperienceLevels] = useState(
    DEFAULT_SELECTED_EXPERIENCE_LEVELS
  );
  const [selectedWorkplaces, setSelectedWorkplaces] = useState([]);
  const [selectedRoleTypes, setSelectedRoleTypes] = useState([]);
  const [selectedSkills, setSelectedSkills] = useState([]);
  const [isResumeModalOpen, setIsResumeModalOpen] = useState(false);

  const [viewerStateStore, setViewerStateStore] = useState({
    scope: null,
    overrides: {},
    pendingActions: {},
    actionError: "",
  });

  const [pageState, setPageState] = useState({
    key: "",
    page: 1,
  });

  const [isWelcomeModalDismissed, setIsWelcomeModalDismissed] = useState(false);

  const {
    jobs: rawJobs,
    resolvedUserProfile,
    isLoading,
    isRefreshing,
    hasLoadedOnce,
    error,
    isMockMode,
    retry,
  } = useJobs({
    viewerKey,
    locationQuery,
  });

  useEffect(() => {
    let isMounted = true;

    async function loadTrackerResume() {
      if (!user) {
        if (isMounted) {
          setTrackerResume(null);
        }
        return;
      }

      try {
        const tracker = await fetchTracker();

        if (!isMounted) {
          return;
        }

        setTrackerResume(
          tracker?.resume && typeof tracker.resume === "object"
            ? buildResumeUiStateFromTrackerResume(tracker.resume)
            : null
        );
      } catch {
        if (isMounted) {
          setTrackerResume(null);
        }
      }
    }

    void loadTrackerResume();

    return () => {
      isMounted = false;
    };
  }, [user]);

  const visibleResumeFile = useMemo(() => {
    if (!user) {
      return null;
    }

    return trackerResume || resumeFile || null;
  }, [user, trackerResume, resumeFile]);

  const hasVisibleResume = Boolean(visibleResumeFile);
  const hasRawJobs = Array.isArray(rawJobs) && rawJobs.length > 0;

  const profileSkills = useMemo(
    () =>
      Array.isArray(resolvedUserProfile?.skills)
        ? resolvedUserProfile.skills
        : [],
    [resolvedUserProfile]
  );

  useEffect(() => {
    if (hasVisibleResume) {
      removeSessionStorageValue(WELCOME_MODAL_PENDING_KEY);
    }
  }, [hasVisibleResume]);

  const viewerScope = useMemo(
    () => ({ viewerKey, rawJobs }),
    [viewerKey, rawJobs]
  );

  const effectiveViewerState = useMemo(() => {
    if (viewerStateStore.scope === viewerScope) {
      return viewerStateStore;
    }

    return {
      scope: viewerScope,
      overrides: {},
      pendingActions: {},
      actionError: "",
    };
  }, [viewerStateStore, viewerScope]);

  const scoredJobs = useMemo(() => {
    if (!hasRawJobs) {
      return [];
    }

    return scoreJobsForUser(rawJobs, resolvedUserProfile);
  }, [hasRawJobs, rawJobs, resolvedUserProfile]);

  const mappedJobs = useMemo(() => {
    if (!hasRawJobs) {
      return [];
    }

    return mapJobsForDisplay(rawJobs, scoredJobs, {
      viewerStateOverrides: effectiveViewerState.overrides,
    }).sort((a, b) => b.matchScore - a.matchScore);
  }, [hasRawJobs, rawJobs, scoredJobs, effectiveViewerState.overrides]);

  const availableSkillOptions = useMemo(() => {
    if (!mappedJobs.length && !profileSkills.length) {
      return [];
    }

    return getAvailableSkillOptions(mappedJobs, profileSkills);
  }, [mappedJobs, profileSkills]);

  const jobs = useMemo(() => {
    if (!mappedJobs.length) {
      return [];
    }

    return filterJobs(mappedJobs, {
      locationQuery,
      selectedExperienceLevels,
      selectedWorkplaces,
      selectedRoleTypes,
      selectedSkills,
    }).filter((job) => !job.isHidden);
  }, [
    mappedJobs,
    locationQuery,
    selectedExperienceLevels,
    selectedWorkplaces,
    selectedRoleTypes,
    selectedSkills,
  ]);

  const filterStateKey = useMemo(
    () =>
      JSON.stringify({
        locationQuery: String(locationQuery || "").trim().toLowerCase(),
        selectedExperienceLevels,
        selectedWorkplaces,
        selectedRoleTypes,
        selectedSkills,
      }),
    [
      locationQuery,
      selectedExperienceLevels,
      selectedWorkplaces,
      selectedRoleTypes,
      selectedSkills,
    ]
  );

  const totalPages = useMemo(
    () => Math.max(1, Math.ceil(jobs.length / JOBS_PER_PAGE)),
    [jobs.length]
  );

  const currentPage =
    pageState.key === filterStateKey
      ? Math.min(pageState.page, totalPages)
      : 1;

  const paginatedJobs = useMemo(() => {
    const startIndex = (currentPage - 1) * JOBS_PER_PAGE;
    return jobs.slice(startIndex, startIndex + JOBS_PER_PAGE);
  }, [jobs, currentPage]);

  const visiblePageNumbers = useMemo(() => {
    return getVisiblePageNumbers(currentPage, totalPages, viewportWidth);
  }, [currentPage, totalPages, viewportWidth]);

  const pageStartCount =
    jobs.length === 0 ? 0 : (currentPage - 1) * JOBS_PER_PAGE + 1;
  const pageEndCount = Math.min(currentPage * JOBS_PER_PAGE, jobs.length);

  const filtersSummary = useMemo(() => {
    return getFilterSummary({
      locationQuery,
      selectedExperienceLevels,
      selectedWorkplaces,
      selectedRoleTypes,
      selectedSkills,
    });
  }, [
    locationQuery,
    selectedExperienceLevels,
    selectedWorkplaces,
    selectedRoleTypes,
    selectedSkills,
  ]);

  const activeFilterTags = useMemo(() => {
    return getActiveFilterTags({
      locationQuery,
      selectedExperienceLevels,
      selectedWorkplaces,
      selectedRoleTypes,
      selectedSkills,
    });
  }, [
    locationQuery,
    selectedExperienceLevels,
    selectedWorkplaces,
    selectedRoleTypes,
    selectedSkills,
  ]);

  const hasActiveFilters = activeFilterTags.length > 0;

  const loginContent = useMemo(
    () => getLoginRequiredContent(loginRequiredIntent),
    [loginRequiredIntent]
  );

  const shouldShowPendingWelcome =
    readSessionStorageValue(WELCOME_MODAL_PENDING_KEY) === "true";
  const hasCachedResume = Boolean(readCachedResumeUiState());
  const isWelcomeModalOpen =
    !isWelcomeModalDismissed &&
    shouldShowPendingWelcome &&
    !hasCachedResume &&
    !hasVisibleResume;

  const showInitialLoadingState = isLoading && !hasLoadedOnce && !hasRawJobs;
  const showRefreshState = isRefreshing && hasRawJobs;
  const showLoadErrorCard = !showInitialLoadingState && !!error && !hasRawJobs;
  const showJobsEmptyState =
    !showInitialLoadingState && !error && jobs.length === 0;
  const showJobsList = jobs.length > 0;

  const handleOpenDetails = useCallback((job) => {
    setActiveJob(job);
  }, []);

  const handleCloseDetails = useCallback(() => {
    setActiveJob(null);
  }, []);

  const handleCloseResumeModal = useCallback(() => {
    setIsResumeModalOpen(false);
    writeSessionStorageValue(RESUME_MODAL_DISMISSED_KEY, "true");
  }, []);

  const handleResumeSaved = useCallback((savedResumeUiState) => {
    setResumeFile(savedResumeUiState);
    setTrackerResume(savedResumeUiState);
    setIsResumeModalOpen(false);
    setIsWelcomeModalDismissed(true);
    removeSessionStorageValue(WELCOME_MODAL_PENDING_KEY);
    removeSessionStorageValue(RESUME_MODAL_DISMISSED_KEY);
  }, []);

  const handleCloseWelcomeModal = useCallback(() => {
    setIsWelcomeModalDismissed(true);
    removeSessionStorageValue(WELCOME_MODAL_PENDING_KEY);
  }, []);

  const handleOpenResumeFromWelcome = useCallback(() => {
    if (authLoading) {
      return;
    }

    if (!user) {
      setIsWelcomeModalDismissed(true);
      setIsResumeModalOpen(false);
      setLoginRequiredIntent("resume");
      setIsLoginRequiredModalOpen(true);
      return;
    }

    setIsLoginRequiredModalOpen(false);
    setIsResumeModalOpen(true);
  }, [authLoading, user]);

  const handleCloseLoginRequiredModal = useCallback(() => {
    setIsLoginRequiredModalOpen(false);
  }, []);

  const handleGoToSignIn = useCallback(() => {
    setIsLoginRequiredModalOpen(false);
    navigate("/sign-in");
  }, [navigate]);

  const openLoginRequiredModal = useCallback((intent) => {
    setLoginRequiredIntent(intent);
    setIsLoginRequiredModalOpen(true);
  }, []);

  const handleRequestResumeUpload = useCallback(() => {
    if (authLoading) {
      return;
    }

    if (!user) {
      setIsWelcomeModalDismissed(true);
      setIsResumeModalOpen(false);
      openLoginRequiredModal("resume");
      return;
    }

    setIsLoginRequiredModalOpen(false);
    setIsResumeModalOpen(true);
  }, [authLoading, user, openLoginRequiredModal]);

  const clearAllFilters = useCallback(() => {
    setLocationQuery("");
    setSelectedExperienceLevels([]);
    setSelectedWorkplaces([]);
    setSelectedRoleTypes([]);
    setSelectedSkills([]);
    setPageState({
      key: "",
      page: 1,
    });
  }, []);

  const updatePendingAction = useCallback((jobId, nextState) => {
    setViewerStateStore((current) => {
      const base =
        current.scope === viewerScope
          ? current
          : {
              scope: viewerScope,
              overrides: {},
              pendingActions: {},
              actionError: "",
            };

      return {
        ...base,
        pendingActions: {
          ...base.pendingActions,
          [jobId]: {
            ...(base.pendingActions[jobId] || {}),
            ...nextState,
          },
        },
      };
    });
  }, [viewerScope]);

  const clearPendingAction = useCallback((jobId, key) => {
    setViewerStateStore((current) => {
      const base =
        current.scope === viewerScope
          ? current
          : {
              scope: viewerScope,
              overrides: {},
              pendingActions: {},
              actionError: "",
            };

      const nextPendingActions = { ...base.pendingActions };
      const currentEntry = { ...(nextPendingActions[jobId] || {}) };

      delete currentEntry[key];

      if (Object.keys(currentEntry).length === 0) {
        delete nextPendingActions[jobId];
      } else {
        nextPendingActions[jobId] = currentEntry;
      }

      return {
        ...base,
        pendingActions: nextPendingActions,
      };
    });
  }, [viewerScope]);

  const applyViewerOverride = useCallback((jobId, patch) => {
    setViewerStateStore((current) => {
      const base =
        current.scope === viewerScope
          ? current
          : {
              scope: viewerScope,
              overrides: {},
              pendingActions: {},
              actionError: "",
            };

      return {
        ...base,
        overrides: {
          ...base.overrides,
          [jobId]: {
            ...(base.overrides[jobId] || {}),
            ...patch,
          },
        },
      };
    });
  }, [viewerScope]);

  const removeViewerOverride = useCallback((jobId) => {
    setViewerStateStore((current) => {
      const base =
        current.scope === viewerScope
          ? current
          : {
              scope: viewerScope,
              overrides: {},
              pendingActions: {},
              actionError: "",
            };

      const nextOverrides = { ...base.overrides };
      delete nextOverrides[jobId];

      return {
        ...base,
        overrides: nextOverrides,
      };
    });
  }, [viewerScope]);

  const setScopedActionError = useCallback((nextMessage) => {
    setViewerStateStore((current) => {
      const base =
        current.scope === viewerScope
          ? current
          : {
              scope: viewerScope,
              overrides: {},
              pendingActions: {},
              actionError: "",
            };

      return {
        ...base,
        actionError: nextMessage,
      };
    });
  }, [viewerScope]);

  const handleToggleSave = useCallback(
    async (job) => {
      if (authLoading) {
        return;
      }

      if (!user) {
        openLoginRequiredModal("save");
        return;
      }

      const jobId = job.id;
      const nextSaved = !job.isSaved;
      const previousOverride = effectiveViewerState.overrides[jobId];

      setScopedActionError("");
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
      } catch (saveError) {
        if (previousOverride) {
          applyViewerOverride(jobId, previousOverride);
        } else {
          removeViewerOverride(jobId);
        }

        setScopedActionError(
          saveError instanceof Error
            ? saveError.message
            : "We could not update that saved job right now."
        );
      } finally {
        clearPendingAction(jobId, "saving");
      }
    },
    [
      authLoading,
      user,
      openLoginRequiredModal,
      effectiveViewerState.overrides,
      updatePendingAction,
      applyViewerOverride,
      removeViewerOverride,
      clearPendingAction,
      setScopedActionError,
    ]
  );

  const handleHideJob = useCallback(
    async (job) => {
      if (authLoading) {
        return;
      }

      if (!user) {
        openLoginRequiredModal("hide");
        return;
      }

      const jobId = job.id;
      const previousOverride = effectiveViewerState.overrides[jobId];

      setScopedActionError("");
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
      } catch (hideError) {
        if (previousOverride) {
          applyViewerOverride(jobId, previousOverride);
        } else {
          removeViewerOverride(jobId);
        }

        setScopedActionError(
          hideError instanceof Error
            ? hideError.message
            : "We could not hide that job right now."
        );
      } finally {
        clearPendingAction(jobId, "hiding");
      }
    },
    [
      authLoading,
      user,
      openLoginRequiredModal,
      effectiveViewerState.overrides,
      updatePendingAction,
      applyViewerOverride,
      removeViewerOverride,
      clearPendingAction,
      setScopedActionError,
    ]
  );

  const handleChangePage = useCallback(
    (nextPage) => {
      if (nextPage < 1 || nextPage > totalPages || nextPage === currentPage) {
        return;
      }

      setPageState({
        key: filterStateKey,
        page: nextPage,
      });

      if (typeof window !== "undefined") {
        window.scrollTo({
          top: 0,
          behavior: "smooth",
        });
      }
    },
    [currentPage, totalPages, filterStateKey]
  );

  return {
    activeJob,
    actionError: effectiveViewerState.actionError,
    activeFilterTags,
    availableSkillOptions,
    clearAllFilters,
    currentPage,
    error,
    filtersSummary,
    handleChangePage,
    handleCloseDetails,
    handleCloseLoginRequiredModal,
    handleCloseResumeModal,
    handleCloseWelcomeModal,
    handleGoToSignIn,
    handleHideJob,
    handleOpenDetails,
    handleOpenResumeFromWelcome,
    handleRequestResumeUpload,
    handleResumeSaved,
    handleToggleSave,
    hasActiveFilters,
    hasRawJobs,
    isFiltersModalOpen,
    isLoading,
    isLoginRequiredModalOpen,
    isMockMode,
    isRefreshing,
    isResumeModalOpen,
    isWelcomeModalOpen,
    jobs,
    locationQuery,
    loginContent,
    pageEndCount,
    pageStartCount,
    paginatedJobs,
    pendingActions: effectiveViewerState.pendingActions,
    retry,
    selectedExperienceLevels,
    selectedRoleTypes,
    selectedSkills,
    selectedWorkplaces,
    setIsFiltersModalOpen,
    setLocationQuery,
    setSelectedExperienceLevels,
    setSelectedRoleTypes,
    setSelectedSkills,
    setSelectedWorkplaces,
    showInitialLoadingState,
    showJobsEmptyState,
    showJobsList,
    showLoadErrorCard,
    showRefreshState,
    totalPages,
    visiblePageNumbers,
    visibleResumeFile,
  };
}