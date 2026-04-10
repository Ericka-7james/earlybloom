import React from "react";
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
  return (
    <>
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
          Entry-level and junior start selected by default right now so the
          feed stays early-career focused, but you can widen it whenever you
          want.
        </p>
      </div>

      <div className="jobs-filter-group">
        <div className="jobs-filter-group__header">
          <h3 className="jobs-filter-group__title">Experience level</h3>
          {selectedExperienceLevels.length > 0 ? (
            <span className="jobs-filter-group__count">
              {selectedExperienceLevels.length} selected
            </span>
          ) : null}
        </div>

        {renderFilterChips(
          FILTER_GROUPS.experienceLevel,
          selectedExperienceLevels,
          (value) =>
            setSelectedExperienceLevels((currentValues) =>
              toggleSelectedValue(currentValues, value)
            )
        )}
      </div>

      <div className="jobs-filter-group">
        <div className="jobs-filter-group__header">
          <h3 className="jobs-filter-group__title">Workplace</h3>
          {selectedWorkplaces.length > 0 ? (
            <span className="jobs-filter-group__count">
              {selectedWorkplaces.length} selected
            </span>
          ) : null}
        </div>

        {renderFilterChips(
          FILTER_GROUPS.workplace,
          selectedWorkplaces,
          (value) =>
            setSelectedWorkplaces((currentValues) =>
              toggleSelectedValue(currentValues, value)
            )
        )}
      </div>

      <div className="jobs-filter-group">
        <div className="jobs-filter-group__header">
          <h3 className="jobs-filter-group__title">Role type</h3>
          {selectedRoleTypes.length > 0 ? (
            <span className="jobs-filter-group__count">
              {selectedRoleTypes.length} selected
            </span>
          ) : null}
        </div>

        {renderFilterChips(
          FILTER_GROUPS.roleType,
          selectedRoleTypes,
          (value) =>
            setSelectedRoleTypes((currentValues) =>
              toggleSelectedValue(currentValues, value)
            )
        )}
      </div>
    </>
  );
}

export default JobsFiltersPanel;