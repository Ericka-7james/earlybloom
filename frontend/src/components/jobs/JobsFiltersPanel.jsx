import React, { useMemo, useState } from "react";
import {
  FILTER_GROUPS,
  toggleSelectedValue,
} from "../../lib/jobs/jobFilters";

/**
 * Renders a shared selectable chip list.
 *
 * @param {Array<{label:string,value:string,count?:number,source?:string}>} options
 * @param {string[]} selectedValues
 * @param {(value:string)=>void} onToggle
 * @returns {JSX.Element | null} Chip list.
 */
function renderFilterChips(options, selectedValues, onToggle) {
  const safeOptions = Array.isArray(options) ? options : [];
  const safeSelectedValues = Array.isArray(selectedValues) ? selectedValues : [];

  if (safeOptions.length === 0) {
    return null;
  }

  return (
    <div className="jobs-chip-list">
      {safeOptions.map((option) => {
        const isSelected = safeSelectedValues.includes(option.value);

        return (
          <button
            key={option.value}
            type="button"
            className={`jobs-chip ${isSelected ? "jobs-chip--active" : ""}`}
            aria-pressed={isSelected}
            onClick={() => onToggle(option.value)}
          >
            <span className="jobs-chip__label">{option.label}</span>

            {typeof option.count === "number" && option.count > 0 ? (
              <span className="jobs-chip__meta" aria-hidden="true">
                {option.count}
              </span>
            ) : null}

            {isSelected ? (
              <span className="jobs-chip__check" aria-hidden="true">
                ✓
              </span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}

/**
 * Shared collapsible filter section.
 *
 * @param {{
 * title:string,
 * isOpen:boolean,
 * onToggleOpen:()=>void,
 * children:React.ReactNode
 * }} props
 * @returns {JSX.Element} Filter section.
 */
function FilterSection({ title, isOpen, onToggleOpen, children }) {
  return (
    <section
      className={`jobs-filter-group ${
        isOpen ? "jobs-filter-group--open" : ""
      }`}
    >
      <button
        type="button"
        className="jobs-filter-group__toggle"
        onClick={onToggleOpen}
        aria-expanded={isOpen}
      >
        <div className="jobs-filter-group__header">
          <h3 className="jobs-filter-group__title">{title}</h3>

          <span className="jobs-filter-group__chevron" aria-hidden="true">
            {isOpen ? "−" : "+"}
          </span>
        </div>
      </button>

      {isOpen ? (
        <div className="jobs-filter-group__body">{children}</div>
      ) : null}
    </section>
  );
}

/**
 * Jobs filter sidebar / modal panel.
 *
 * Includes:
 * - experience level
 * - workplace
 * - role type
 * - skill filters
 *
 * Skills are personalized from:
 * 1. user resume skills
 * 2. current jobs dataset skills
 *
 * @param {object} props Component props.
 * @returns {JSX.Element} Filters panel.
 */
function JobsFiltersPanel({
  hasActiveFilters,
  selectedExperienceLevels = [],
  selectedWorkplaces = [],
  selectedRoleTypes = [],
  selectedSkills = [],
  availableSkills = [],
  setSelectedExperienceLevels,
  setSelectedWorkplaces,
  setSelectedRoleTypes,
  setSelectedSkills,
  onClearAll,
}) {
  const [openSections, setOpenSections] = useState({
    experience: true,
    workplace: false,
    roleType: false,
    skills: false,
  });

  const [showAllSkills, setShowAllSkills] = useState(false);

  const safeAvailableSkills = useMemo(() => {
    return Array.isArray(availableSkills) ? availableSkills.filter(Boolean) : [];
  }, [availableSkills]);

  const totalSelectedCount = useMemo(() => {
    return (
      selectedExperienceLevels.length +
      selectedWorkplaces.length +
      selectedRoleTypes.length +
      selectedSkills.length
    );
  }, [
    selectedExperienceLevels,
    selectedWorkplaces,
    selectedRoleTypes,
    selectedSkills,
  ]);

  const visibleSkillOptions = useMemo(() => {
    return showAllSkills ? safeAvailableSkills : safeAvailableSkills.slice(0, 10);
  }, [safeAvailableSkills, showAllSkills]);

  /**
   * Toggles a filter section open state.
   *
   * @param {string} sectionKey Section key.
   * @returns {void}
   */
  function toggleSection(sectionKey) {
    setOpenSections((current) => ({
      ...current,
      [sectionKey]: !current[sectionKey],
    }));
  }

  /**
   * Toggles a selected skill.
   *
   * @param {string} value Skill value.
   * @returns {void}
   */
  function toggleSkills(value) {
    if (typeof setSelectedSkills !== "function") {
      return;
    }

    setSelectedSkills((currentValues) =>
      toggleSelectedValue(
        Array.isArray(currentValues) ? currentValues : [],
        value
      )
    );
  }

  return (
    <div className="jobs-filters-panel">
      <div className="jobs-filters__header">
        <div className="jobs-filters__title-row">
          <h2 className="jobs-results__title">Filters</h2>

          {hasActiveFilters ? (
            <button
              type="button"
              className="jobs-chip jobs-chip--muted"
              onClick={onClearAll}
            >
              Clear all
            </button>
          ) : null}
        </div>

        <p className="jobs-filters__text">
          Entry-level and junior roles start selected by default so the feed
          stays early-career focused.
        </p>

        {totalSelectedCount > 0 ? (
          <p className="jobs-filters__summary">
            {totalSelectedCount} filter
            {totalSelectedCount === 1 ? "" : "s"} selected
          </p>
        ) : null}
      </div>

      <div className="jobs-filters-panel__groups">
        <FilterSection
          title="Experience level"
          isOpen={openSections.experience}
          onToggleOpen={() => toggleSection("experience")}
        >
          {renderFilterChips(
            FILTER_GROUPS.experienceLevel,
            selectedExperienceLevels,
            (value) =>
              setSelectedExperienceLevels((currentValues) =>
                toggleSelectedValue(
                  Array.isArray(currentValues) ? currentValues : [],
                  value
                )
              )
          )}
        </FilterSection>

        <FilterSection
          title="Workplace"
          isOpen={openSections.workplace}
          onToggleOpen={() => toggleSection("workplace")}
        >
          {renderFilterChips(
            FILTER_GROUPS.workplace,
            selectedWorkplaces,
            (value) =>
              setSelectedWorkplaces((currentValues) =>
                toggleSelectedValue(
                  Array.isArray(currentValues) ? currentValues : [],
                  value
                )
              )
          )}
        </FilterSection>

        <FilterSection
          title="Role type"
          isOpen={openSections.roleType}
          onToggleOpen={() => toggleSection("roleType")}
        >
          {renderFilterChips(
            FILTER_GROUPS.roleType,
            selectedRoleTypes,
            (value) =>
              setSelectedRoleTypes((currentValues) =>
                toggleSelectedValue(
                  Array.isArray(currentValues) ? currentValues : [],
                  value
                )
              )
          )}
        </FilterSection>

        <FilterSection
          title="Skills"
          isOpen={openSections.skills}
          onToggleOpen={() => toggleSection("skills")}
        >
          {safeAvailableSkills.length > 0 ? (
            <div className="jobs-filters__skills">
              <p className="jobs-filters__text jobs-filters__skills-text">
                Personalized from your resume and current results.
              </p>

              {renderFilterChips(
                visibleSkillOptions,
                selectedSkills,
                toggleSkills
              )}

              {safeAvailableSkills.length > 10 ? (
                <div className="jobs-filters__skills-actions">
                  <button
                    type="button"
                    className="jobs-chip jobs-chip--muted"
                    onClick={() => setShowAllSkills((current) => !current)}
                  >
                    {showAllSkills ? "Show less" : "Show more"}
                  </button>
                </div>
              ) : null}
            </div>
          ) : (
            <p className="jobs-filters__text">
              Skill filters appear once resume skills or job-result skills are
              available.
            </p>
          )}
        </FilterSection>
      </div>
    </div>
  );
}

export default JobsFiltersPanel;