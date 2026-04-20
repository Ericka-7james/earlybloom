import React from "react";

/**
 * Jobs page search-style hero panel.
 *
 * @param {object} props Component props.
 * @returns {JSX.Element} Search hero.
 */
function JobsSearchHero({
  visibleResumeFile,
  filtersSummary,
  isLoading,
  isRefreshing,
  onOpenFilters,
  onRefresh,
  onRequestResumeUpload,
}) {
  return (
    <section className="jobs-page__search-shell">
      <div className="container">
        <div className="jobs-search-panel">
          <div className="jobs-search-panel__hero">
            <div className="jobs-search-panel__hero-copy">
              <span className="jobs-search-panel__eyebrow">EarlyBloom jobs</span>

              <h1 className="jobs-search-panel__title">
                Find roles that feel right for where you are.
              </h1>

              <p className="jobs-search-panel__text">
                Browse a cleaner early-career feed with practical fit signals,
                quick filtering, and less noise between you and the next role.
              </p>
            </div>

            <button
              type="button"
              className="jobs-search-panel__resume"
              onClick={onRequestResumeUpload}
            >
              <div className="jobs-search-panel__resume-box">
                <p className="jobs-search-panel__resume-label">Resume fit</p>
                <p className="jobs-search-panel__resume-title">
                  {visibleResumeFile ? "Resume connected" : "Upload your resume"}
                </p>
                <p className="jobs-search-panel__resume-text">
                  {visibleResumeFile
                    ? visibleResumeFile.name
                    : "PDF only. Personalize skills and fit signals."}
                </p>
              </div>
            </button>
          </div>

          <div className="jobs-search-panel__controls">
            <button
              type="button"
              className="jobs-search-panel__input"
              onClick={onOpenFilters}
            >
              <span className="jobs-search-panel__input-label">Browse setup</span>
              <span className="jobs-search-panel__input-value">
                {filtersSummary}
              </span>
            </button>

            <div className="jobs-search-panel__action-row">
              <button
                type="button"
                className="jobs-search-panel__filters-button"
                onClick={onOpenFilters}
              >
                All filters
              </button>

              <button
                type="button"
                className="jobs-search-panel__refresh-button"
                onClick={onRefresh}
                disabled={isLoading || isRefreshing}
              >
                {isRefreshing ? "Refreshing..." : "Refresh results"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export default JobsSearchHero;