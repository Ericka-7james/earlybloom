import React from "react";
import JobCard from "./JobCard.jsx";

function toSafeArray(value) {
  return Array.isArray(value) ? value : [];
}

function toSafeObject(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function toSafeText(value, fallback = "") {
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed || fallback;
  }

  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  return fallback;
}

function toSafeNumber(value, fallback = 0) {
  return Number.isFinite(value) ? Number(value) : fallback;
}

function getSafeRenderableJob(job, index) {
  if (!job || typeof job !== "object" || Array.isArray(job)) {
    return null;
  }

  const safeJobId =
    job.id ??
    job.jobId ??
    job.slug ??
    job.url ??
    job.sourceUrl ??
    `job-${index}`;

  return {
    ...job,
    id: safeJobId,
    title: toSafeText(job.title, "Untitled role"),
    company: toSafeText(job.company, "Unknown company"),
    location: toSafeText(job.location, "Location not listed"),
    summary: toSafeText(job.summary, ""),
    fitTag: toSafeText(job.fitTag, "Too Senior"),
    sourceLabel: toSafeText(job.sourceLabel, ""),
    cardMeta: Array.isArray(job.cardMeta) ? job.cardMeta : [],
    matchedSkills: Array.isArray(job.matchedSkills) ? job.matchedSkills : [],
  };
}

function JobsResultsPanel({
  jobs = [],
  paginatedJobs = [],
  pendingActions = {},
  actionError = "",
  error = "",
  isMockMode = false,
  hasRawJobs = false,
  hasActiveFilters = false,
  activeFilterTags = [],
  filtersSummary = "",
  currentPage = 1,
  totalPages = 1,
  visiblePageNumbers = [],
  pageStartCount = 0,
  pageEndCount = 0,
  showInitialLoadingState = false,
  showRefreshState = false,
  showLoadErrorCard = false,
  showJobsEmptyState = false,
  showJobsList = false,
  onRetry,
  onClearAllFilters,
  onOpenDetails,
  onToggleSave,
  onHideJob,
  onChangePage,
}) {
  const safeJobs = toSafeArray(jobs).filter(
    (job) => job && typeof job === "object" && !Array.isArray(job)
  );

  const safePaginatedJobs = toSafeArray(paginatedJobs)
    .map((job, index) => getSafeRenderableJob(job, index))
    .filter(Boolean);

  const safePendingActions = toSafeObject(pendingActions);

  const safeActiveFilterTags = toSafeArray(activeFilterTags)
    .map((tag, index) => {
      const safeTag = toSafeObject(tag);
      const label = toSafeText(safeTag.label, "");
      const key =
        safeTag.key ??
        safeTag.id ??
        safeTag.value ??
        label ??
        `filter-${index}`;

      if (!label) {
        return null;
      }

      return {
        key: String(key),
        label,
      };
    })
    .filter(Boolean);

  const safeVisiblePageNumbers = toSafeArray(visiblePageNumbers).filter(
    (pageNumber) =>
      pageNumber === "..." ||
      (Number.isFinite(pageNumber) && Number(pageNumber) > 0)
  );

  const safeFiltersSummary = toSafeText(filtersSummary, "All current roles");
  const safeActionError = toSafeText(actionError, "");
  const safeError = toSafeText(error, "Unknown error");
  const safeCurrentPage = Math.max(1, toSafeNumber(currentPage, 1));
  const safeTotalPages = Math.max(1, toSafeNumber(totalPages, 1));
  const safePageStartCount = Math.max(0, toSafeNumber(pageStartCount, 0));
  const safePageEndCount = Math.max(0, toSafeNumber(pageEndCount, 0));

  return (
    <div className="jobs-results">
      <div className="jobs-results__surface">
        <div className="jobs-results__header">
          <div className="jobs-results__header-copy">
            <p className="jobs-results__section-label">Top roles</p>
            <h2 className="jobs-results__title">Open roles</h2>

            <p className="jobs-results__text">
              {showInitialLoadingState
                ? "Loading roles..."
                : safeError && !hasRawJobs
                  ? "We could not load jobs right now."
                  : `${safeJobs.length} roles matched to your current view.`}
            </p>

            {!showInitialLoadingState && safeJobs.length > 0 ? (
              <p className="jobs-results__subtext">
                Showing {safePageStartCount} to {safePageEndCount} of {safeJobs.length} results.
              </p>
            ) : null}

            {isMockMode ? (
              <p className="jobs-results__subtext">Mock mode is active right now.</p>
            ) : null}
          </div>

          <div className="jobs-results__header-actions">
            <div className="jobs-results__summary-card">
              <p className="jobs-results__summary-label">Current view</p>
              <p className="jobs-results__summary-value">{safeFiltersSummary}</p>
            </div>
          </div>
        </div>

        {hasActiveFilters && safeActiveFilterTags.length > 0 ? (
          <div className="jobs-active-filters" aria-label="Active filters">
            <div className="jobs-active-filters__top">
              <p className="jobs-active-filters__label">Active filters</p>

              <button
                type="button"
                className="jobs-chip jobs-chip--muted"
                onClick={typeof onClearAllFilters === "function" ? onClearAllFilters : undefined}
              >
                Clear all
              </button>
            </div>

            <div className="jobs-active-filters__list">
              {safeActiveFilterTags.map((tag) => (
                <span key={tag.key} className="jobs-chip jobs-chip--active">
                  {tag.label}
                </span>
              ))}
            </div>
          </div>
        ) : null}

        {safeActionError ? (
          <div
            className="message-card message-card--error jobs-results__message"
            role="alert"
            aria-live="polite"
          >
            <p className="message-card__copy">{safeActionError}</p>
          </div>
        ) : null}

        {showRefreshState ? (
          <div
            className="message-card jobs-results__message"
            role="status"
            aria-live="polite"
          >
            <p className="message-card__copy">Refreshing jobs...</p>
          </div>
        ) : null}

        {showInitialLoadingState ? (
          <div
            className="message-card jobs-results__message"
            role="status"
            aria-live="polite"
          >
            <p className="message-card__copy">Loading jobs...</p>
          </div>
        ) : null}

        {showLoadErrorCard ? (
          <div className="empty-state-card jobs-results__empty" role="alert">
            <div className="empty-state-card__header">
              <h3 className="card-title">Unable to load jobs</h3>
              <p className="card-copy">{safeError}</p>
            </div>

            <div className="empty-state-card__actions">
              <button
                type="button"
                className="jobs-chip"
                onClick={typeof onRetry === "function" ? onRetry : undefined}
              >
                Try again
              </button>
            </div>
          </div>
        ) : null}

        {showJobsEmptyState ? (
          <div className="empty-state-card jobs-results__empty">
            <div className="empty-state-card__header">
              <h3 className="card-title">
                {hasActiveFilters
                  ? "No roles match these filters"
                  : "No roles available right now"}
              </h3>

              <p className="card-copy">
                {hasActiveFilters
                  ? "Try clearing a few filters or widening your view."
                  : "Refresh and try again in a moment."}
              </p>
            </div>

            {hasActiveFilters ? (
              <div className="empty-state-card__actions">
                <button
                  type="button"
                  className="jobs-chip"
                  onClick={typeof onClearAllFilters === "function" ? onClearAllFilters : undefined}
                >
                  Clear filters
                </button>
              </div>
            ) : null}
          </div>
        ) : null}

        {showJobsList ? (
          <>
            <div className="jobs-list" aria-busy={showRefreshState}>
              {safePaginatedJobs.map((job, index) => {
                const safeJobId =
                  job.id ?? job.jobId ?? job.slug ?? job.url ?? `job-${index}`;

                const actionState = toSafeObject(safePendingActions[safeJobId]);

                return (
                  <JobCard
                    key={String(safeJobId)}
                    job={job}
                    onOpenDetails={typeof onOpenDetails === "function" ? onOpenDetails : undefined}
                    onSaveToggle={typeof onToggleSave === "function" ? onToggleSave : undefined}
                    onHide={typeof onHideJob === "function" ? onHideJob : undefined}
                    isSavePending={Boolean(actionState.saving)}
                    isHidePending={Boolean(actionState.hiding)}
                  />
                );
              })}
            </div>

            {safeTotalPages > 1 ? (
              <nav
                className="jobs-pagination"
                aria-label="Job results pages"
              >
                <div className="jobs-pagination__inner">
                  <button
                    type="button"
                    className="jobs-chip"
                    onClick={() =>
                      typeof onChangePage === "function" &&
                      onChangePage(safeCurrentPage - 1)
                    }
                    disabled={safeCurrentPage === 1}
                    aria-label="Go to previous page"
                  >
                    Prev
                  </button>

                  <div className="jobs-pagination__pages">
                    {safeVisiblePageNumbers.map((pageNumber, index) => {
                      if (pageNumber === "...") {
                        return (
                          <span
                            key={`ellipsis-${index}`}
                            className="jobs-pagination__ellipsis"
                            aria-hidden="true"
                          >
                            ...
                          </span>
                        );
                      }

                      return (
                        <button
                          key={`page-${pageNumber}`}
                          type="button"
                          className={`jobs-chip ${
                            pageNumber === safeCurrentPage ? "jobs-chip--active" : ""
                          }`}
                          onClick={() =>
                            typeof onChangePage === "function" &&
                            onChangePage(pageNumber)
                          }
                          aria-label={`Go to page ${pageNumber}`}
                          aria-current={
                            pageNumber === safeCurrentPage ? "page" : undefined
                          }
                        >
                          {pageNumber}
                        </button>
                      );
                    })}
                  </div>

                  <button
                    type="button"
                    className="jobs-chip"
                    onClick={() =>
                      typeof onChangePage === "function" &&
                      onChangePage(safeCurrentPage + 1)
                    }
                    disabled={safeCurrentPage === safeTotalPages}
                    aria-label="Go to next page"
                  >
                    Next
                  </button>
                </div>
              </nav>
            ) : null}
          </>
        ) : null}
      </div>
    </div>
  );
}

export default JobsResultsPanel;