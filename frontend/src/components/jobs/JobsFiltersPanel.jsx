// src/components/jobs/JobsFiltersPanel.jsx
import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  FILTER_GROUPS,
  toggleSelectedValue,
} from "../../lib/jobs/jobFilters";
import { getLocationSuggestions } from "../../lib/jobs/locationSuggestions";

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
 * - location search with local autocomplete
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
  locationQuery = "",
  selectedExperienceLevels = [],
  selectedWorkplaces = [],
  selectedRoleTypes = [],
  selectedSkills = [],
  availableSkills = [],
  setLocationQuery,
  setSelectedExperienceLevels,
  setSelectedWorkplaces,
  setSelectedRoleTypes,
  setSelectedSkills,
  onClearAll,
}) {
  const [openSections, setOpenSections] = useState({
    location: true,
    experience: true,
    workplace: false,
    roleType: false,
    skills: false,
  });
  const [showAllSkills, setShowAllSkills] = useState(false);
  const [isSuggestionsOpen, setIsSuggestionsOpen] = useState(false);
  const [activeSuggestionIndex, setActiveSuggestionIndex] = useState(-1);

  const locationFieldRef = useRef(null);

  const safeAvailableSkills = useMemo(() => {
    return Array.isArray(availableSkills) ? availableSkills.filter(Boolean) : [];
  }, [availableSkills]);

  const totalSelectedCount = useMemo(() => {
    const hasLocation = String(locationQuery || "").trim() ? 1 : 0;

    return (
      hasLocation +
      selectedExperienceLevels.length +
      selectedWorkplaces.length +
      selectedRoleTypes.length +
      selectedSkills.length
    );
  }, [
    locationQuery,
    selectedExperienceLevels,
    selectedWorkplaces,
    selectedRoleTypes,
    selectedSkills,
  ]);

  const visibleSkillOptions = useMemo(() => {
    return showAllSkills ? safeAvailableSkills : safeAvailableSkills.slice(0, 10);
  }, [safeAvailableSkills, showAllSkills]);

  const locationSuggestions = useMemo(() => {
    return getLocationSuggestions(locationQuery, 6);
  }, [locationQuery]);

  const safeActiveSuggestionIndex =
    activeSuggestionIndex >= 0 &&
    activeSuggestionIndex < locationSuggestions.length
      ? activeSuggestionIndex
      : -1;

  useEffect(() => {
    function handlePointerDown(event) {
      if (!locationFieldRef.current) {
        return;
      }

      if (!locationFieldRef.current.contains(event.target)) {
        setIsSuggestionsOpen(false);
        setActiveSuggestionIndex(-1);
      }
    }

    document.addEventListener("mousedown", handlePointerDown);

    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
    };
  }, []);

  function toggleSection(sectionKey) {
    setOpenSections((current) => ({
      ...current,
      [sectionKey]: !current[sectionKey],
    }));
  }

  function getNextSelectedValues(currentValues, value) {
    return toggleSelectedValue(
      Array.isArray(currentValues) ? currentValues : [],
      value
    );
  }

  function toggleSkills(value) {
    if (typeof setSelectedSkills !== "function") {
      return;
    }

    setSelectedSkills((currentValues) =>
      getNextSelectedValues(currentValues, value)
    );
  }

  function handleLocationInputChange(event) {
    if (typeof setLocationQuery !== "function") {
      return;
    }

    setLocationQuery(event.target.value);
    setIsSuggestionsOpen(true);
    setActiveSuggestionIndex(-1);
  }

  function handleSuggestionSelect(suggestionValue) {
    if (typeof setLocationQuery !== "function") {
      return;
    }

    setLocationQuery(suggestionValue);
    setIsSuggestionsOpen(false);
    setActiveSuggestionIndex(-1);
  }

  function handleLocationKeyDown(event) {
    if (!locationSuggestions.length) {
      if (event.key === "Escape") {
        setIsSuggestionsOpen(false);
        setActiveSuggestionIndex(-1);
      }
      return;
    }

    if (event.key === "ArrowDown") {
      event.preventDefault();
      setIsSuggestionsOpen(true);
      setActiveSuggestionIndex((current) => {
        const normalizedCurrent =
          current >= 0 && current < locationSuggestions.length ? current : -1;

        return normalizedCurrent >= locationSuggestions.length - 1
          ? 0
          : normalizedCurrent + 1;
      });
    }

    if (event.key === "ArrowUp") {
      event.preventDefault();
      setIsSuggestionsOpen(true);
      setActiveSuggestionIndex((current) => {
        const normalizedCurrent =
          current >= 0 && current < locationSuggestions.length ? current : -1;

        return normalizedCurrent <= 0
          ? locationSuggestions.length - 1
          : normalizedCurrent - 1;
      });
    }

    if (
      event.key === "Enter" &&
      isSuggestionsOpen &&
      safeActiveSuggestionIndex >= 0
    ) {
      event.preventDefault();
      handleSuggestionSelect(
        locationSuggestions[safeActiveSuggestionIndex].value
      );
    }

    if (event.key === "Escape") {
      setIsSuggestionsOpen(false);
      setActiveSuggestionIndex(-1);
    }
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
          title="Location"
          description="Search by city, state, region, or workplace style."
          isOpen={openSections.location}
          onToggleOpen={() => toggleSection("location")}
        >
          <div
            className="jobs-filters-panel__location-search"
            ref={locationFieldRef}
          >
            <label
              className="jobs-filters-panel__field-label"
              htmlFor="jobs-location-query"
            >
              Location
            </label>

            <div className="jobs-filters-panel__autocomplete">
              <input
                id="jobs-location-query"
                type="text"
                className="jobs-filters-panel__input"
                value={locationQuery}
                onChange={handleLocationInputChange}
                onFocus={() => setIsSuggestionsOpen(true)}
                onKeyDown={handleLocationKeyDown}
                placeholder="Atlanta, Georgia, New York, NY, remote..."
                autoComplete="off"
                aria-autocomplete="list"
                aria-expanded={isSuggestionsOpen && locationSuggestions.length > 0}
                aria-controls="jobs-location-suggestions"
              />

              {isSuggestionsOpen && locationSuggestions.length > 0 ? (
                <div
                  id="jobs-location-suggestions"
                  className="jobs-filters-panel__suggestions"
                  role="listbox"
                  aria-label="Location suggestions"
                >
                  {locationSuggestions.map((suggestion, index) => {
                    const isActive = index === safeActiveSuggestionIndex;

                    return (
                      <button
                        key={`${suggestion.type}-${suggestion.label}`}
                        type="button"
                        className={`jobs-filters-panel__suggestion ${
                          isActive
                            ? "jobs-filters-panel__suggestion--active"
                            : ""
                        }`}
                        onMouseDown={(event) => {
                          event.preventDefault();
                          handleSuggestionSelect(suggestion.value);
                        }}
                        role="option"
                        aria-selected={isActive}
                      >
                        <span className="jobs-filters-panel__suggestion-label">
                          {suggestion.label}
                        </span>
                        <span className="jobs-filters-panel__suggestion-type">
                          {suggestion.type}
                        </span>
                      </button>
                    );
                  })}
                </div>
              ) : null}
            </div>

            <p className="jobs-filters-panel__field-help">
              Flexible matching works with city, state, remote, hybrid, and
              similar normalized location text.
            </p>
          </div>
        </FilterSection>

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