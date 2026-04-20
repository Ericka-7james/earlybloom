import React from "react";
import JobCard from "./JobCard.jsx";

/**
 * Renders the jobs results surface.
 *
 * Cleaner version:
 * - header card only
 * - transparent results list area
 * - no current view card
 * - no active filter chip section
 *
 * @param {object} props Component props.
 * @returns {JSX.Element}
 */
function JobsResultsPanel({
  jobs,
  paginatedJobs,
  pendingActions,
  actionError,
  error,
  isMockMode,
  hasRawJobs,
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
  onOpenDetails,
  onToggleSave,
  onHideJob,
  onChangePage,
}) {
  return (
    <div className="jobs-results">
      <div className="jobs-results__header-card section-card">
        <div className="jobs-results__header">
          <div className="jobs-results__header-copy">
            <p className="jobs-results__section-label">Top roles</p>
            <h2 className="jobs-results__title">Open roles</h2>

            <p className="jobs-results__text">
              {showInitialLoadingState
                ? "Loading roles..."
                : error && !hasRawJobs
                ? "We could not load jobs right now."
                : `${jobs.length} roles matched.`}
            </p>

            {!showInitialLoadingState && jobs.length > 0 ? (
              <p className="jobs-results__subtext">
                Showing {pageStartCount} to {pageEndCount} of {jobs.length}
                {" "}results.
              </p>
            ) : null}

            {isMockMode ? (
              <p className="jobs-results__subtext">
                Mock mode is active right now.
              </p>
            ) : null}
          </div>
        </div>
      </div>

      {actionError ? (
        <div className="message-card jobs-results__message">
          <p className="message-card__copy">{actionError}</p>
        </div>
      ) : null}

      {showRefreshState ? (
        <div className="message-card jobs-results__message">
          <p className="message-card__copy">Refreshing jobs...</p>
        </div>
      ) : null}

      {showInitialLoadingState ? (
        <div className="message-card jobs-results__message">
          <p className="message-card__copy">Loading jobs...</p>
        </div>
      ) : null}

      {showLoadErrorCard ? (
        <div className="empty-state-card jobs-results__empty">
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
            <h3 className="card-title">No roles available right now</h3>
            <p className="card-copy">
              Refresh and try again in a moment.
            </p>
          </div>
        </div>
      ) : null}

      {showJobsList ? (
        <>
          <div className="jobs-list">
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
            <nav className="jobs-pagination section-card">
              <div className="jobs-pagination__inner">
                <button
                  type="button"
                  className="jobs-chip"
                  onClick={() => onChangePage(currentPage - 1)}
                  disabled={currentPage === 1}
                >
                  Prev
                </button>

                <div className="jobs-pagination__pages">
                  {visiblePageNumbers.map((pageNumber, index) => {
                    if (pageNumber === "...") {
                      return (
                        <span key={index} className="jobs-pagination__ellipsis">
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
                >
                  Next
                </button>
              </div>
            </nav>
          ) : null}
        </>
      ) : null}
    </div>
  );
}

export default JobsResultsPanel;