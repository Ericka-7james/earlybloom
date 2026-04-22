import React from "react";
import JobDetailsModal from "./JobDetailsModal.jsx";
import ResumeUploadModal from "./ResumeUploadModal.jsx";
import JobsFiltersPanel from "./JobsFiltersPanel.jsx";
import CommonModal from "../common/CommonModal.jsx";
import BloombugAppIcon from "../../assets/bloombug/BloombugAppIcon.png";

/**
 * Returns a safe array.
 *
 * @param {unknown} value Potential array.
 * @returns {Array<unknown>} Safe array.
 */
function toSafeArray(value) {
  return Array.isArray(value) ? value : [];
}

/**
 * Returns safe login-required content.
 *
 * @param {unknown} value Potential login content object.
 * @returns {{eyebrow: string, title: string, body: string}} Safe modal copy.
 */
function toSafeLoginContent(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return {
      eyebrow: "Sign in to continue.",
      title: "Sign in required",
      body: "Please sign in to use this feature.",
    };
  }

  return {
    eyebrow:
      typeof value.eyebrow === "string" && value.eyebrow.trim()
        ? value.eyebrow
        : "Sign in to continue.",
    title:
      typeof value.title === "string" && value.title.trim()
        ? value.title
        : "Sign in required",
    body:
      typeof value.body === "string" && value.body.trim()
        ? value.body
        : "Please sign in to use this feature.",
  };
}

/**
 * Renders all Jobs page modals in one place.
 *
 * @param {object} props Component props.
 * @returns {JSX.Element} Jobs page modals.
 */
function JobsPageModals({
  activeJob = null,
  isFiltersModalOpen = false,
  isLoginRequiredModalOpen = false,
  isWelcomeModalOpen = false,
  isResumeModalOpen = false,
  hasActiveFilters = false,
  loginContent = null,
  availableSkillOptions = [],
  selectedExperienceLevels = [],
  selectedWorkplaces = [],
  selectedRoleTypes = [],
  selectedSkills = [],
  setSelectedExperienceLevels,
  setSelectedWorkplaces,
  setSelectedRoleTypes,
  setSelectedSkills,
  visibleResumeFile = null,
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
  const safeLoginContent = toSafeLoginContent(loginContent);
  const safeAvailableSkillOptions = toSafeArray(availableSkillOptions);
  const safeSelectedExperienceLevels = toSafeArray(selectedExperienceLevels);
  const safeSelectedWorkplaces = toSafeArray(selectedWorkplaces);
  const safeSelectedRoleTypes = toSafeArray(selectedRoleTypes);
  const safeSelectedSkills = toSafeArray(selectedSkills);

  return (
    <>
      <CommonModal
        isOpen={Boolean(isFiltersModalOpen)}
        title="Filters"
        onClose={onCloseFilters}
        size="md"
        iconImage={BloombugAppIcon}
        iconAlt="EarlyBloom Bloombug icon"
      >
        <div className="jobs-filters jobs-filters--modal">
          <JobsFiltersPanel
            hasActiveFilters={Boolean(hasActiveFilters)}
            selectedExperienceLevels={safeSelectedExperienceLevels}
            selectedWorkplaces={safeSelectedWorkplaces}
            selectedRoleTypes={safeSelectedRoleTypes}
            selectedSkills={safeSelectedSkills}
            availableSkills={safeAvailableSkillOptions}
            setSelectedExperienceLevels={setSelectedExperienceLevels}
            setSelectedWorkplaces={setSelectedWorkplaces}
            setSelectedRoleTypes={setSelectedRoleTypes}
            setSelectedSkills={setSelectedSkills}
            onClearAll={onClearAllFilters}
          />
        </div>
      </CommonModal>

      <CommonModal
        isOpen={Boolean(isLoginRequiredModalOpen)}
        title="Sign in required"
        onClose={onCloseLoginRequired}
        size="md"
        iconImage={BloombugAppIcon}
        iconAlt="EarlyBloom Bloombug icon"
      >
        <div className="jobs-reasons-modal">
          <div className="jobs-reasons-modal__intro">
            <p className="jobs-reasons-modal__job-meta">
              {safeLoginContent.eyebrow}
            </p>

            <h3 className="jobs-reasons-modal__job-title">
              {safeLoginContent.title}
            </h3>

            <p className="jobs-results__text jobs-results__text--modal">
              {safeLoginContent.body}
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
        isOpen={Boolean(isWelcomeModalOpen)}
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
        isOpen={Boolean(isResumeModalOpen)}
        onClose={onCloseResumeModal}
        onResumeSaved={onResumeSaved}
        resumeFile={visibleResumeFile}
      />
    </>
  );
}

export default JobsPageModals;