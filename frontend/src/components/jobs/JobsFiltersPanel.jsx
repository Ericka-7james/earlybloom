import React, { useMemo, useState } from "react";
import {
  FILTER_GROUPS,
  toggleSelectedValue,
} from "../../lib/jobs/jobFilters";

/**
 * Renders a selectable chip button for a single filter option.
 *
 * @param {object} props Component props.
 * @param {{label:string,value:string,count?:number}} props.option Filter option.
 * @param {boolean} props.isSelected Whether the option is selected.
 * @param {() => void} props.onToggle Toggle callback.
 * @returns {JSX.Element} Filter chip.
 */
function FilterChip({ option, isSelected, onToggle }) {
  return (
    <button
      type="button"
      className={`jobs-filter-chip ${isSelected ? "jobs-filter-chip--active" : ""}`}
      aria-pressed={isSelected}
      onClick={onToggle}
    >
      <span className="jobs-filter-chip__label">{option.label}</span>

      {typeof option.count === "number" && option.count > 0 ? (
        <span className="jobs-filter-chip__count" aria-hidden="true">
          {option.count}
        </span>
      ) : null}

      {isSelected ? (
        <span className="jobs-filter-chip__check" aria-hidden="true">
          ✓
        </span>
      ) : null}
    </button>
  );
}

/**
 * Renders a reusable list of filter chips.
 *
 * @param {object} props Component props.
 * @param {Array<{label:string,value:string,count?:number}>} props.options Filter options.
 * @param {string[]} props.selectedValues Selected option values.
 * @param {(value:string)=>void} props.onToggle Toggle callback.
 * @returns {JSX.Element | null} Chip list.
 */
function FilterChipList({ options, selectedValues, onToggle }) {
  const safeOptions = Array.isArray(options) ? options : [];
  const safeSelectedValues = Array.isArray(selectedValues) ? selectedValues : [];

  if (safeOptions.length === 0) {
    return null;
  }

  return (
    <div className="jobs-filter-chip-list">
      {safeOptions.map((option) => {
        const isSelected = safeSelectedValues.includes(option.value);

        return (
          <FilterChip
            key={option.value}
            option={option}
            isSelected={isSelected}
            onToggle={() => onToggle(option.value)}
          />
        );
      })}
    </div>
  );
}

/**
 * Renders a collapsible filter group.
 *
 * @param {object} props Component props.
 * @param {string} props.title Group title.
 * @param {string} [props.description] Optional helper copy.
 * @param {boolean} props.isOpen Whether the section is open.
 * @param {() => void} props.onToggleOpen Toggle callback.
 * @param {React.ReactNode} props.children Section body.
 * @returns {JSX.Element} Filter group.
 */
function FilterSection({
  title,
  description,
  isOpen,
  onToggleOpen,
  children,
}) {
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
        <div className="jobs-filter-group__heading">
          <div className="jobs-filter-group__heading-copy">
            <h3 className="jobs-filter-group__title">{title}</h3>

            {description ? (
              <p className="jobs-filter-group__description">{description}</p>
            ) : null}
          </div>

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
 * Jobs filter sidebar and modal panel.
 *
 * Includes:
 * - experience level
 * - workplace
 * - role type
 * - skills
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
   * Toggles whether a section is open.
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
   * Toggles a value inside a selected array.
   *
   * @param {string[]} currentValues Current values.
   * @param {string} value Option value.
   * @returns {string[]} Next selected values.
   */
  function getNextSelectedValues(currentValues, value) {
    return toggleSelectedValue(
      Array.isArray(currentValues) ? currentValues : [],
      value
    );
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

    setSelectedSkills((currentValues) => getNextSelectedValues(currentValues, value));
  }

  return (
    <div className="jobs-filters-panel">
      <div className="jobs-filters-panel__top">
        <div className="jobs-filters-panel__title-block">
          <p className="jobs-filters-panel__eyebrow">Refine results</p>
          <h2 className="jobs-filters-panel__title">Filters</h2>
          <p className="jobs-filters-panel__text">
            Narrow the feed without losing the early-career focus.
          </p>
        </div>

        {hasActiveFilters ? (
          <button
            type="button"
            className="jobs-filters-panel__clear"
            onClick={onClearAll}
          >
            Clear all
          </button>
        ) : null}
      </div>

      <div className="jobs-filters-panel__summary-card">
        <p className="jobs-filters-panel__summary-label">Current setup</p>
        <p className="jobs-filters-panel__summary-value">
          {totalSelectedCount > 0
            ? `${totalSelectedCount} filter${totalSelectedCount === 1 ? "" : "s"} selected`
            : "Default early-career view"}
        </p>
        <p className="jobs-filters-panel__summary-text">
          Entry-level and junior roles stay emphasized by default.
        </p>
      </div>

      <div className="jobs-filters-panel__groups">
        <FilterSection
          title="Experience level"
          description="Start with early-career ranges."
          isOpen={openSections.experience}
          onToggleOpen={() => toggleSection("experience")}
        >
          <FilterChipList
            options={FILTER_GROUPS.experienceLevel}
            selectedValues={selectedExperienceLevels}
            onToggle={(value) =>
              setSelectedExperienceLevels((currentValues) =>
                getNextSelectedValues(currentValues, value)
              )
            }
          />
        </FilterSection>

        <FilterSection
          title="Workplace"
          description="Remote, hybrid, or on-site."
          isOpen={openSections.workplace}
          onToggleOpen={() => toggleSection("workplace")}
        >
          <FilterChipList
            options={FILTER_GROUPS.workplace}
            selectedValues={selectedWorkplaces}
            onToggle={(value) =>
              setSelectedWorkplaces((currentValues) =>
                getNextSelectedValues(currentValues, value)
              )
            }
          />
        </FilterSection>

        <FilterSection
          title="Role type"
          description="Focus the feed by function."
          isOpen={openSections.roleType}
          onToggleOpen={() => toggleSection("roleType")}
        >
          <FilterChipList
            options={FILTER_GROUPS.roleType}
            selectedValues={selectedRoleTypes}
            onToggle={(value) =>
              setSelectedRoleTypes((currentValues) =>
                getNextSelectedValues(currentValues, value)
              )
            }
          />
        </FilterSection>

        <FilterSection
          title="Skills"
          description="Personalized from your resume and current results."
          isOpen={openSections.skills}
          onToggleOpen={() => toggleSection("skills")}
        >
          {safeAvailableSkills.length > 0 ? (
            <div className="jobs-filters-panel__skills">
              <FilterChipList
                options={visibleSkillOptions}
                selectedValues={selectedSkills}
                onToggle={toggleSkills}
              />

              {safeAvailableSkills.length > 10 ? (
                <div className="jobs-filters-panel__skills-actions">
                  <button
                    type="button"
                    className="jobs-filters-panel__secondary-action"
                    onClick={() => setShowAllSkills((current) => !current)}
                  >
                    {showAllSkills ? "Show less" : "Show more"}
                  </button>
                </div>
              ) : null}
            </div>
          ) : (
            <div className="jobs-filters-panel__empty-state">
              Skill filters will appear once resume skills or result skills are
              available.
            </div>
          )}
        </FilterSection>
      </div>
    </div>
  );
}

export default JobsFiltersPanel;