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

  return (
    <main className="jobs-page">
      <JobsSearchHero
        visibleResumeFile={jobsPage.visibleResumeFile}
        filtersSummary={jobsPage.filtersSummary}
        isLoading={jobsPage.isLoading}
        isRefreshing={jobsPage.isRefreshing}
        onOpenFilters={() => jobsPage.setIsFiltersModalOpen(true)}
        onRefresh={jobsPage.retry}
        onRequestResumeUpload={jobsPage.handleRequestResumeUpload}
      />

      <section className="jobs-page__browse section-pad">
        <div className="container jobs-layout">
          <aside
            className="jobs-filters jobs-filters--desktop section-card"
            aria-label="Job filters"
          >
            <JobsFiltersPanel
              hasActiveFilters={jobsPage.hasActiveFilters}
              selectedExperienceLevels={jobsPage.selectedExperienceLevels}
              selectedWorkplaces={jobsPage.selectedWorkplaces}
              selectedRoleTypes={jobsPage.selectedRoleTypes}
              selectedSkills={jobsPage.selectedSkills}
              availableSkills={jobsPage.availableSkillOptions}
              setSelectedExperienceLevels={jobsPage.setSelectedExperienceLevels}
              setSelectedWorkplaces={jobsPage.setSelectedWorkplaces}
              setSelectedRoleTypes={jobsPage.setSelectedRoleTypes}
              setSelectedSkills={jobsPage.setSelectedSkills}
              onClearAll={jobsPage.clearAllFilters}
            />
          </aside>

          <JobsResultsPanel
            jobs={jobsPage.jobs}
            paginatedJobs={jobsPage.paginatedJobs}
            pendingActions={jobsPage.pendingActions}
            actionError={jobsPage.actionError}
            error={jobsPage.error}
            isMockMode={jobsPage.isMockMode}
            hasRawJobs={jobsPage.hasRawJobs}
            hasActiveFilters={jobsPage.hasActiveFilters}
            activeFilterTags={jobsPage.activeFilterTags}
            filtersSummary={jobsPage.filtersSummary}
            currentPage={jobsPage.currentPage}
            totalPages={jobsPage.totalPages}
            visiblePageNumbers={jobsPage.visiblePageNumbers}
            pageStartCount={jobsPage.pageStartCount}
            pageEndCount={jobsPage.pageEndCount}
            showInitialLoadingState={jobsPage.showInitialLoadingState}
            showRefreshState={jobsPage.showRefreshState}
            showLoadErrorCard={jobsPage.showLoadErrorCard}
            showJobsEmptyState={jobsPage.showJobsEmptyState}
            showJobsList={jobsPage.showJobsList}
            onOpenFilters={() => jobsPage.setIsFiltersModalOpen(true)}
            onRetry={jobsPage.retry}
            onClearAllFilters={jobsPage.clearAllFilters}
            onOpenDetails={jobsPage.handleOpenDetails}
            onToggleSave={jobsPage.handleToggleSave}
            onHideJob={jobsPage.handleHideJob}
            onChangePage={jobsPage.handleChangePage}
          />
        </div>
      </section>

      <JobsPageModals
        activeJob={jobsPage.activeJob}
        isFiltersModalOpen={jobsPage.isFiltersModalOpen}
        isLoginRequiredModalOpen={jobsPage.isLoginRequiredModalOpen}
        isWelcomeModalOpen={jobsPage.isWelcomeModalOpen}
        isResumeModalOpen={jobsPage.isResumeModalOpen}
        hasActiveFilters={jobsPage.hasActiveFilters}
        loginContent={jobsPage.loginContent}
        availableSkillOptions={jobsPage.availableSkillOptions}
        selectedExperienceLevels={jobsPage.selectedExperienceLevels}
        selectedWorkplaces={jobsPage.selectedWorkplaces}
        selectedRoleTypes={jobsPage.selectedRoleTypes}
        selectedSkills={jobsPage.selectedSkills}
        setSelectedExperienceLevels={jobsPage.setSelectedExperienceLevels}
        setSelectedWorkplaces={jobsPage.setSelectedWorkplaces}
        setSelectedRoleTypes={jobsPage.setSelectedRoleTypes}
        setSelectedSkills={jobsPage.setSelectedSkills}
        visibleResumeFile={jobsPage.visibleResumeFile}
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