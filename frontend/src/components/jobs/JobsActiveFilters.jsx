import React from "react";

function JobsActiveFilters({
  hasActiveFilters,
  isUsingDefaultExperiencePreset,
  selectedWorkplaces,
  selectedRoleTypes,
  activeFilterTags,
  onClearAll,
  onRemoveTag,
}) {
  if (!hasActiveFilters) {
    return (
      <div className="jobs-active-filters jobs-active-filters--empty">
        <p className="jobs-results__text">Showing all roles.</p>
      </div>
    );
  }

  const isDefaultOnly =
    isUsingDefaultExperiencePreset &&
    selectedWorkplaces.length === 0 &&
    selectedRoleTypes.length === 0;

  return (
    <div className="jobs-active-filters">
      <div className="jobs-active-filters__top">
        <div>
          <p className="jobs-active-filters__label">Active filters</p>
          <p className="jobs-active-filters__text">
            {isDefaultOnly
              ? "Entry-level and Junior are currently selected."
              : `${activeFilterTags.length} filter${
                  activeFilterTags.length === 1 ? "" : "s"
                } applied.`}
          </p>
        </div>

        <button
          type="button"
          className="jobs-chip jobs-chip--muted"
          onClick={onClearAll}
        >
          Clear filters
        </button>
      </div>

      <div className="jobs-active-filters__list">
        {activeFilterTags.map((tag) => (
          <button
            key={`${tag.type}-${tag.value}`}
            type="button"
            className="jobs-active-filter-tag"
            onClick={() => onRemoveTag(tag)}
            aria-label={`Remove ${tag.group} filter ${tag.label}`}
          >
            <span className="jobs-active-filter-tag__group">{tag.group}</span>
            <span className="jobs-active-filter-tag__value">{tag.label}</span>
            <span className="jobs-active-filter-tag__remove" aria-hidden="true">
              ×
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

export default JobsActiveFilters;