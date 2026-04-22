// frontend/src/pages/Jobs.jsx
/**
 * @fileoverview Jobs discovery page for EarlyBloom.
 *
 * This page now focuses on composition:
 * - read page state from a dedicated jobs page hook
 * - render the shared jobs search hero
 * - render the results section
 * - render shared jobs modals
 */

import React from "react";
import JobsFiltersPanel from "../components/jobs/JobsFiltersPanel.jsx";
import JobsSearchHero from "../components/jobs/JobsSearchHero.jsx";
import JobsResultsPanel from "../components/jobs/JobsResultsPanel.jsx";
import JobsPageModals from "../components/jobs/JobsPageModals.jsx";
import { useJobsPageState } from "../hooks/jobs/useJobsPageState.js";
import "../styles/components/jobs.css";

/**
 * Renders the jobs discovery page.
 *
 * @returns {JSX.Element} Jobs page.
 */
function Jobs() {
  const jobsPage = useJobsPageState();

  const jobs = Array.isArray(jobsPage.jobs) ? jobsPage.jobs : [];
  const paginatedJobs = Array.isArray(jobsPage.paginatedJobs)
    ? jobsPage.paginatedJobs
    : [];
  const activeFilterTags = Array.isArray(jobsPage.activeFilterTags)
    ? jobsPage.activeFilterTags
    : [];
  const availableSkillOptions = Array.isArray(jobsPage.availableSkillOptions)
    ? jobsPage.availableSkillOptions
    : [];
  const visiblePageNumbers = Array.isArray(jobsPage.visiblePageNumbers)
    ? jobsPage.visiblePageNumbers
    : [];
  const pendingActions =
    jobsPage.pendingActions && typeof jobsPage.pendingActions === "object"
      ? jobsPage.pendingActions
      : {};

  const selectedExperienceLevels = Array.isArray(
    jobsPage.selectedExperienceLevels
  )
    ? jobsPage.selectedExperienceLevels
    : [];

  const selectedWorkplaces = Array.isArray(jobsPage.selectedWorkplaces)
    ? jobsPage.selectedWorkplaces
    : [];

  const selectedRoleTypes = Array.isArray(jobsPage.selectedRoleTypes)
    ? jobsPage.selectedRoleTypes
    : [];

  const selectedSkills = Array.isArray(jobsPage.selectedSkills)
    ? jobsPage.selectedSkills
    : [];

  return (
    <main className="jobs-page">
      <JobsSearchHero
        visibleResumeFile={jobsPage.visibleResumeFile ?? null}
        filtersSummary={jobsPage.filtersSummary ?? null}
        isLoading={Boolean(jobsPage.isLoading)}
        isRefreshing={Boolean(jobsPage.isRefreshing)}
        onOpenFilters={() => jobsPage.setIsFiltersModalOpen(true)}
        onRefresh={jobsPage.retry}
        onRequestResumeUpload={jobsPage.handleRequestResumeUpload}
      />

      <section className="jobs-page__browse section-pad">
        <div className="container jobs-page__browse-shell">
          <div className="jobs-mobile-filters-wrap">
            <button
              type="button"
              className="jobs-mobile-filters-button"
              onClick={() => jobsPage.setIsFiltersModalOpen(true)}
              aria-label="Open all filters"
            >
              <span className="jobs-mobile-filters-button__label">
                All Filters
              </span>

              <span
                className="jobs-mobile-filters-button__icon"
                aria-hidden="true"
              >
                <span className="jobs-mobile-filters-button__line jobs-mobile-filters-button__line--top" />
                <span className="jobs-mobile-filters-button__line jobs-mobile-filters-button__line--middle" />
                <span className="jobs-mobile-filters-button__line jobs-mobile-filters-button__line--bottom" />
              </span>
            </button>
          </div>

          <div className="jobs-layout">
            <aside
              className="jobs-filters jobs-filters--desktop section-card"
              aria-label="Job filters"
            >
              <JobsFiltersPanel
                hasActiveFilters={Boolean(jobsPage.hasActiveFilters)}
                locationQuery={jobsPage.locationQuery ?? ""}
                selectedExperienceLevels={selectedExperienceLevels}
                selectedWorkplaces={selectedWorkplaces}
                selectedRoleTypes={selectedRoleTypes}
                selectedSkills={selectedSkills}
                availableSkills={availableSkillOptions}
                setLocationQuery={jobsPage.setLocationQuery}
                setSelectedExperienceLevels={jobsPage.setSelectedExperienceLevels}
                setSelectedWorkplaces={jobsPage.setSelectedWorkplaces}
                setSelectedRoleTypes={jobsPage.setSelectedRoleTypes}
                setSelectedSkills={jobsPage.setSelectedSkills}
                onClearAll={jobsPage.clearAllFilters}
              />
            </aside>

            <JobsResultsPanel
              jobs={jobs}
              paginatedJobs={paginatedJobs}
              pendingActions={pendingActions}
              actionError={jobsPage.actionError ?? ""}
              error={jobsPage.error ?? ""}
              isMockMode={Boolean(jobsPage.isMockMode)}
              hasRawJobs={Boolean(jobsPage.hasRawJobs)}
              hasActiveFilters={Boolean(jobsPage.hasActiveFilters)}
              activeFilterTags={activeFilterTags}
              filtersSummary={jobsPage.filtersSummary ?? null}
              currentPage={Number.isFinite(jobsPage.currentPage)
                ? jobsPage.currentPage
                : 1}
              totalPages={Number.isFinite(jobsPage.totalPages)
                ? jobsPage.totalPages
                : 1}
              visiblePageNumbers={visiblePageNumbers}
              pageStartCount={Number.isFinite(jobsPage.pageStartCount)
                ? jobsPage.pageStartCount
                : 0}
              pageEndCount={Number.isFinite(jobsPage.pageEndCount)
                ? jobsPage.pageEndCount
                : 0}
              showInitialLoadingState={Boolean(jobsPage.showInitialLoadingState)}
              showRefreshState={Boolean(jobsPage.showRefreshState)}
              showLoadErrorCard={Boolean(jobsPage.showLoadErrorCard)}
              showJobsEmptyState={Boolean(jobsPage.showJobsEmptyState)}
              showJobsList={Boolean(jobsPage.showJobsList)}
              onOpenFilters={() => jobsPage.setIsFiltersModalOpen(true)}
              onRetry={jobsPage.retry}
              onClearAllFilters={jobsPage.clearAllFilters}
              onOpenDetails={jobsPage.handleOpenDetails}
              onToggleSave={jobsPage.handleToggleSave}
              onHideJob={jobsPage.handleHideJob}
              onChangePage={jobsPage.handleChangePage}
            />
          </div>
        </div>
      </section>

      <JobsPageModals
        activeJob={jobsPage.activeJob ?? null}
        isFiltersModalOpen={Boolean(jobsPage.isFiltersModalOpen)}
        isLoginRequiredModalOpen={Boolean(
          jobsPage.isLoginRequiredModalOpen
        )}
        isWelcomeModalOpen={Boolean(jobsPage.isWelcomeModalOpen)}
        isResumeModalOpen={Boolean(jobsPage.isResumeModalOpen)}
        hasActiveFilters={Boolean(jobsPage.hasActiveFilters)}
        loginContent={jobsPage.loginContent ?? null}
        availableSkillOptions={availableSkillOptions}
        locationQuery={jobsPage.locationQuery ?? ""}
        selectedExperienceLevels={selectedExperienceLevels}
        selectedWorkplaces={selectedWorkplaces}
        selectedRoleTypes={selectedRoleTypes}
        selectedSkills={selectedSkills}
        setLocationQuery={jobsPage.setLocationQuery}
        setSelectedExperienceLevels={jobsPage.setSelectedExperienceLevels}
        setSelectedWorkplaces={jobsPage.setSelectedWorkplaces}
        setSelectedRoleTypes={jobsPage.setSelectedRoleTypes}
        setSelectedSkills={jobsPage.setSelectedSkills}
        visibleResumeFile={jobsPage.visibleResumeFile ?? null}
        onCloseDetails={jobsPage.handleCloseDetails}
        onCloseFilters={() => jobsPage.setIsFiltersModalOpen(false)}
        onClearAllFilters={jobsPage.clearAllFilters}
        onCloseLoginRequired={jobsPage.handleCloseLoginRequiredModal}
        onGoToSignIn={jobsPage.handleGoToSignIn}
        onCloseWelcome={jobsPage.handleCloseWelcomeModal}
        onOpenResumeFromWelcome={jobsPage.handleOpenResumeFromWelcome}
        onCloseResumeModal={jobsPage.handleCloseResumeModal}
        onResumeSaved={jobsPage.handleResumeSaved}
      />
    </main>
  );
}

export default Jobs;