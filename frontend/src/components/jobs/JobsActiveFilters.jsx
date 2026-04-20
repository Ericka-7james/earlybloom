import React from "react";

/**
 * Renders a removable active filter pill.
 *
 * @param {object} props Component props.
 * @param {{type:string,value:string,group:string,label:string}} props.tag Filter tag.
 * @param {(tag:object)=>void} props.onRemoveTag Remove callback.
 * @returns {JSX.Element} Active filter pill.
 */
function ActiveFilterPill({ tag, onRemoveTag }) {
  return (
    <button
      type="button"
      className="jobs-active-filter-pill"
      onClick={() => onRemoveTag(tag)}
      aria-label={`Remove ${tag.group} filter ${tag.label}`}
    >
      <span className="jobs-active-filter-pill__group">{tag.group}</span>
      <span className="jobs-active-filter-pill__value">{tag.label}</span>
      <span className="jobs-active-filter-pill__remove" aria-hidden="true">
        ×
      </span>
    </button>
  );
}

/**
 * Active filters summary row.
 *
 * @param {object} props Component props.
 * @returns {JSX.Element} Active filters UI.
 */
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
        <div className="jobs-active-filters__top">
          <div>
            <p className="jobs-active-filters__label">Current view</p>
            <p className="jobs-active-filters__text">
              Showing all roles in the default early-career view.
            </p>
          </div>
        </div>
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
        <div className="jobs-active-filters__copy">
          <p className="jobs-active-filters__label">Active filters</p>
          <p className="jobs-active-filters__text">
            {isDefaultOnly
              ? "Entry-level and junior are currently selected."
              : `${activeFilterTags.length} filter${
                  activeFilterTags.length === 1 ? "" : "s"
                } shaping this feed.`}
          </p>
        </div>

        <button
          type="button"
          className="jobs-active-filters__clear"
          onClick={onClearAll}
        >
          Clear all
        </button>
      </div>

      <div className="jobs-active-filters__list">
        {activeFilterTags.map((tag) => (
          <ActiveFilterPill
            key={`${tag.type}-${tag.value}`}
            tag={tag}
            onRemoveTag={onRemoveTag}
          />
        ))}
      </div>
    </div>
  );
}

export default JobsActiveFilters;