import React from "react";
import JobCard from "./JobCard.jsx";

/**
 * Renders the jobs results surface.
 *
 * @param {object} props Component props.
 * @returns {JSX.Element} Results panel.
 */
function JobsResultsPanel({
  jobs,
  paginatedJobs,
  pendingActions,
  actionError,
  error,
  isMockMode,
  hasRawJobs,
  hasActiveFilters,
  activeFilterTags,
  filtersSummary,
  currentPage,
  totalPages,
  visiblePageNumbers,
  pageStartCount,
  pageEndCount,
  showInitialLoadingState,
  showRefreshState,
  showLoadErrorCard,
  showJobsEmptyState,
  showJobsList,
  onRetry,
  onClearAllFilters,
  onOpenDetails,
  onToggleSave,
  onHideJob,
  onChangePage,
}) {
  return (
    <div className="jobs-results">
      <div className="jobs-results__surface section-card">
        <div className="jobs-results__header">
          <div className="jobs-results__header-copy">
            <p className="jobs-results__section-label">Top roles</p>
            <h2 className="jobs-results__title">Open roles</h2>

            <p className="jobs-results__text">
              {showInitialLoadingState
                ? "Loading roles..."
                : error && !hasRawJobs
                ? "We could not load jobs right now."
                : `${jobs.length} roles matched to your current view.`}
            </p>

            {!showInitialLoadingState && jobs.length > 0 ? (
              <p className="jobs-results__subtext">
                Showing {pageStartCount} to {pageEndCount} of {jobs.length}
                {" "}results.
              </p>
            ) : null}

            {isMockMode ? (
              <p className="jobs-results__subtext">Mock mode is active right now.</p>
            ) : null}
          </div>

          <div className="jobs-results__header-actions">
            <div className="jobs-results__summary-card">
              <p className="jobs-results__summary-label">Current view</p>
              <p className="jobs-results__summary-value">{filtersSummary}</p>
            </div>
          </div>
        </div>

        {hasActiveFilters ? (
          <div className="jobs-active-filters" aria-label="Active filters">
            <div className="jobs-active-filters__top">
              <p className="jobs-active-filters__label">Active filters</p>

              <button
                type="button"
                className="jobs-chip jobs-chip--muted"
                onClick={onClearAllFilters}
              >
                Clear all
              </button>
            </div>

            <div className="jobs-active-filters__list">
              {activeFilterTags.map((tag) => (
                <span key={tag.key} className="jobs-chip jobs-chip--active">
                  {tag.label}
                </span>
              ))}
            </div>
          </div>
        ) : null}

        {actionError ? (
          <div
            className="message-card message-card--error jobs-results__message"
            role="alert"
            aria-live="polite"
          >
            <p className="message-card__copy">{actionError}</p>
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
              <p className="card-copy">{error}</p>
            </div>

            <div className="empty-state-card__actions">
              <button type="button" className="jobs-chip" onClick={onRetry}>
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
                  onClick={onClearAllFilters}
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
              {paginatedJobs.map((job) => (
                <JobCard
                  key={job.id}
                  job={job}
                  onOpenDetails={onOpenDetails}
                  onSaveToggle={onToggleSave}
                  onHide={onHideJob}
                  isSavePending={Boolean(pendingActions[job.id]?.saving)}
                  isHidePending={Boolean(pendingActions[job.id]?.hiding)}
                />
              ))}
            </div>

            {totalPages > 1 ? (
              <nav
                className="jobs-pagination section-card"
                aria-label="Job results pages"
              >
                <div className="jobs-pagination__inner">
                  <button
                    type="button"
                    className="jobs-chip"
                    onClick={() => onChangePage(currentPage - 1)}
                    disabled={currentPage === 1}
                    aria-label="Go to previous page"
                  >
                    Prev
                  </button>

                  <div className="jobs-pagination__pages">
                    {visiblePageNumbers.map((pageNumber, index) => {
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
                          key={pageNumber}
                          type="button"
                          className={`jobs-chip ${
                            pageNumber === currentPage
                              ? "jobs-chip--active"
                              : ""
                          }`}
                          onClick={() => onChangePage(pageNumber)}
                          aria-label={`Go to page ${pageNumber}`}
                          aria-current={
                            pageNumber === currentPage ? "page" : undefined
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
                    onClick={() => onChangePage(currentPage + 1)}
                    disabled={currentPage === totalPages}
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