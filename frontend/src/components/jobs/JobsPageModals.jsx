import React from "react";
import JobDetailsModal from "./JobDetailsModal.jsx";
import ResumeUploadModal from "./ResumeUploadModal.jsx";
import JobsFiltersPanel from "./JobsFiltersPanel.jsx";
import CommonModal from "../common/CommonModal.jsx";
import BloombugAppIcon from "../../assets/bloombug/BloombugAppIcon.png";

/**
 * Renders all Jobs page modals in one place.
 *
 * @param {object} props Component props.
 * @returns {JSX.Element} Jobs page modals.
 */
function JobsPageModals({
  activeJob,
  isFiltersModalOpen,
  isLoginRequiredModalOpen,
  isWelcomeModalOpen,
  isResumeModalOpen,
  hasActiveFilters,
  loginContent,
  availableSkillOptions,
  selectedExperienceLevels,
  selectedWorkplaces,
  selectedRoleTypes,
  selectedSkills,
  setSelectedExperienceLevels,
  setSelectedWorkplaces,
  setSelectedRoleTypes,
  setSelectedSkills,
  visibleResumeFile,
  onCloseDetails,
  onCloseFilters,
  onClearAllFilters,
  onCloseLoginRequired,
  onGoToSignIn,
  onCloseWelcome,
  onOpenResumeFromWelcome,
  onCloseResumeModal,
  onResumeSaved,
}) {
  return (
    <>
      <CommonModal
        isOpen={isFiltersModalOpen}
        title="Filters"
        onClose={onCloseFilters}
        size="md"
        iconImage={BloombugAppIcon}
        iconAlt="EarlyBloom Bloombug icon"
      >
        <div className="jobs-filters jobs-filters--modal">
          <JobsFiltersPanel
            hasActiveFilters={hasActiveFilters}
            selectedExperienceLevels={selectedExperienceLevels}
            selectedWorkplaces={selectedWorkplaces}
            selectedRoleTypes={selectedRoleTypes}
            selectedSkills={selectedSkills}
            availableSkills={availableSkillOptions}
            setSelectedExperienceLevels={setSelectedExperienceLevels}
            setSelectedWorkplaces={setSelectedWorkplaces}
            setSelectedRoleTypes={setSelectedRoleTypes}
            setSelectedSkills={setSelectedSkills}
            onClearAll={onClearAllFilters}
          />
        </div>
      </CommonModal>

      <CommonModal
        isOpen={isLoginRequiredModalOpen}
        title="Sign in required"
        onClose={onCloseLoginRequired}
        size="md"
        iconImage={BloombugAppIcon}
        iconAlt="EarlyBloom Bloombug icon"
      >
        <div className="jobs-reasons-modal">
          <div className="jobs-reasons-modal__intro">
            <p className="jobs-reasons-modal__job-meta">
              {loginContent.eyebrow}
            </p>

            <h3 className="jobs-reasons-modal__job-title">
              {loginContent.title}
            </h3>

            <p className="jobs-results__text jobs-results__text--modal">
              {loginContent.body}
            </p>
          </div>

          <div className="jobs-inline-actions">
            <button
              type="button"
              className="button button--primary"
              onClick={onGoToSignIn}
            >
              Sign in
            </button>

            <button
              type="button"
              className="jobs-chip"
              onClick={onCloseLoginRequired}
            >
              Cancel
            </button>
          </div>
        </div>
      </CommonModal>

      <CommonModal
        isOpen={isWelcomeModalOpen}
        title="Welcome to EarlyBloom"
        onClose={onCloseWelcome}
        size="md"
        iconImage={BloombugAppIcon}
        iconAlt="EarlyBloom Bloombug icon"
      >
        <div className="jobs-reasons-modal">
          <div className="jobs-reasons-modal__intro">
            <p className="jobs-reasons-modal__job-meta">
              You’re in 🌱 Let’s get your setup started.
            </p>

            <h3 className="jobs-reasons-modal__job-title">
              Upload your resume to make your search feel more tailored.
            </h3>

            <p className="jobs-results__text jobs-results__text--modal">
              You can skip it for now, but adding your resume helps EarlyBloom
              organize your experience and shape the feed around you.
            </p>
          </div>

          <div className="jobs-inline-actions">
            <button
              type="button"
              className="button button--primary"
              onClick={onOpenResumeFromWelcome}
            >
              Upload resume
            </button>

            <button
              type="button"
              className="jobs-chip"
              onClick={onCloseWelcome}
            >
              Maybe later
            </button>
          </div>
        </div>
      </CommonModal>

      <JobDetailsModal
        job={activeJob}
        isOpen={Boolean(activeJob)}
        onClose={onCloseDetails}
      />

      <ResumeUploadModal
        isOpen={isResumeModalOpen}
        onClose={onCloseResumeModal}
        onResumeSaved={onResumeSaved}
        resumeFile={visibleResumeFile}
      />
    </>
  );
}

export default JobsPageModals;