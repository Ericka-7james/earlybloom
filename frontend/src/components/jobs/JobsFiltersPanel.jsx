import React, { useMemo, useState } from "react";
import {
  FILTER_GROUPS,
  toggleSelectedValue,
} from "../../lib/jobs/jobFilters";

function renderFilterChips(options, selectedValues, onToggle) {
  return (
    <div className="jobs-chip-list">
      {options.map((option) => {
        const isSelected = selectedValues.includes(option.value);

        return (
          <button
            key={option.value}
            type="button"
            className={`jobs-chip ${isSelected ? "jobs-chip--active" : ""}`}
            aria-pressed={isSelected}
            onClick={() => onToggle(option.value)}
          >
            <span className="jobs-chip__label">{option.label}</span>
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

function FilterSection({
  title,
  isOpen,
  onToggleOpen,
  children,
}) {
  return (
    <section
      className={`jobs-filter-group ${isOpen ? "jobs-filter-group--open" : ""}`}
    >
      <button
        type="button"
        className="jobs-filter-group__toggle"
        onClick={onToggleOpen}
        aria-expanded={isOpen}
      >
        <div className="jobs-filter-group__header">
          <h3 className="jobs-filter-group__title">{title}</h3>

          <div className="jobs-filter-group__header-meta">
            <span className="jobs-filter-group__chevron" aria-hidden="true">
              {isOpen ? "−" : "+"}
            </span>
          </div>
        </div>
      </button>

      {isOpen ? <div className="jobs-filter-group__body">{children}</div> : null}
    </section>
  );
}

function JobsFiltersPanel({
  hasActiveFilters,
  selectedExperienceLevels,
  selectedWorkplaces,
  selectedRoleTypes,
  setSelectedExperienceLevels,
  setSelectedWorkplaces,
  setSelectedRoleTypes,
  onClearAll,
}) {
  const [openSections, setOpenSections] = useState({
    experience: true,
    workplace: false,
    roleType: false,
  });

  const totalSelectedCount = useMemo(
    () =>
      selectedExperienceLevels.length +
      selectedWorkplaces.length +
      selectedRoleTypes.length,
    [selectedExperienceLevels, selectedWorkplaces, selectedRoleTypes]
  );

  function toggleSection(sectionKey) {
    setOpenSections((current) => ({
      ...current,
      [sectionKey]: !current[sectionKey],
    }));
  }

  return (
    <div className="jobs-filters-panel">
      <div className="jobs-filters__header">
        <div className="jobs-filters__title-row">
          <h2 className="jobs-results__title">Filters</h2>

          <div className="jobs-filters__header-actions">
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
        </div>

        <p className="jobs-filters__text">
          Entry-level and junior start selected by default so the feed stays
          early-career focused, but you can widen it whenever you want.
        </p>

        {totalSelectedCount > 0 ? (
          <p className="jobs-filters__summary">
            {totalSelectedCount} filter{totalSelectedCount === 1 ? "" : "s"} selected
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
                toggleSelectedValue(currentValues, value)
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
                toggleSelectedValue(currentValues, value)
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
                toggleSelectedValue(currentValues, value)
              )
          )}
        </FilterSection>
      </div>
    </div>
  );
}

export default JobsFiltersPanel;