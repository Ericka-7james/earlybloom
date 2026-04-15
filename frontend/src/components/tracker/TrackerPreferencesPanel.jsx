import React, { useMemo, useState } from "react";
import {
  FILTER_GROUPS,
  toggleSelectedValue,
} from "../../lib/jobs/jobFilters";

const LOCATION_OPTIONS = [
  { value: "remote", label: "Remote" },
  { value: "atlanta", label: "Atlanta" },
  { value: "georgia", label: "Georgia" },
  { value: "united states", label: "United States" },
];

function renderPreferenceChips(
  options,
  selectedValues,
  onToggle,
  listClassName = ""
) {
  return (
    <div className={`tracker-chip-list ${listClassName}`.trim()}>
      {options.map((option) => {
        const isSelected = selectedValues.includes(option.value);

        return (
          <button
            key={option.value}
            type="button"
            className={`chip-button tracker-chip ${
              isSelected ? "tracker-chip--active" : ""
            }`}
            aria-pressed={isSelected}
            onClick={() => onToggle(option.value)}
          >
            <span>{option.label}</span>
            {isSelected ? (
              <span className="tracker-chip__check" aria-hidden="true">
                ✓
              </span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}

function PreferenceSection({
  title,
  isOpen,
  onToggleOpen,
  sectionKey,
  children,
}) {
  return (
    <section
      className={`tracker-filter-group tracker-filter-group--${sectionKey} ${
        isOpen ? "tracker-filter-group--open" : ""
      }`}
    >
      <button
        type="button"
        className="tracker-filter-group__toggle"
        onClick={onToggleOpen}
        aria-expanded={isOpen}
      >
        <div className="tracker-filter-group__header">
          <h3 className="tracker-filter-group__title">{title}</h3>

          <div className="tracker-filter-group__header-meta">
            <span className="tracker-filter-group__chevron" aria-hidden="true">
              {isOpen ? "−" : "+"}
            </span>
          </div>
        </div>
      </button>

      {isOpen ? (
        <div className="tracker-filter-group__body">{children}</div>
      ) : null}
    </section>
  );
}

function TrackerPreferencesPanel({
  preferencesDraft,
  setPreferencesDraft,
  isSavingPreferences,
  onSavePreferences,
  onResetPreferences,
}) {
  const [openSections, setOpenSections] = useState({
    levels: true,
    workplace: false,
    roleType: false,
    location: false,
  });

  const totalSelectedCount = useMemo(() => {
    return (
      (preferencesDraft.desired_levels?.length || 0) +
      (preferencesDraft.preferred_workplace_types?.length || 0) +
      (preferencesDraft.preferred_role_types?.length || 0) +
      (preferencesDraft.preferred_locations?.length || 0) +
      (preferencesDraft.is_lgbt_friendly_only ? 1 : 0)
    );
  }, [preferencesDraft]);

  function toggleSection(sectionKey) {
    setOpenSections((current) => ({
      ...current,
      [sectionKey]: !current[sectionKey],
    }));
  }

  function togglePreferenceValue(field, value) {
    setPreferencesDraft((current) => ({
      ...current,
      [field]: toggleSelectedValue(current[field] || [], value),
    }));
  }

  return (
    <div className="app-panel-card tracker-preferences-panel">
      <div className="tracker-preferences-panel__header">
        <div className="tracker-preferences-panel__title-row">
          <div>
            <p className="section-label">Preferences</p>
            <h2 className="card-title">Your default search setup</h2>
          </div>

          <div className="tracker-preferences-panel__actions">
            <button
              type="button"
              className="chip-button tracker-chip tracker-chip--muted"
              onClick={onResetPreferences}
            >
              Reset
            </button>
          </div>
        </div>

        <p className="card-copy">
          These set your steady default search shape. Jobs page filters can still
          drift around freely without rewriting this setup.
        </p>

        {totalSelectedCount > 0 ? (
          <p className="card-meta">
            {totalSelectedCount} preference
            {totalSelectedCount === 1 ? "" : "s"} selected
          </p>
        ) : null}
      </div>

      <PreferenceSection
        sectionKey="levels"
        title="Experience level"
        isOpen={openSections.levels}
        onToggleOpen={() => toggleSection("levels")}
      >
        {renderPreferenceChips(
          FILTER_GROUPS.experienceLevel,
          preferencesDraft.desired_levels || [],
          (value) => togglePreferenceValue("desired_levels", value)
        )}
      </PreferenceSection>

      <PreferenceSection
        sectionKey="workplace"
        title="Workplace"
        isOpen={openSections.workplace}
        onToggleOpen={() => toggleSection("workplace")}
      >
        {renderPreferenceChips(
          FILTER_GROUPS.workplace,
          preferencesDraft.preferred_workplace_types || [],
          (value) => togglePreferenceValue("preferred_workplace_types", value)
        )}
      </PreferenceSection>

      <PreferenceSection
        sectionKey="role-type"
        title="Role type"
        isOpen={openSections.roleType}
        onToggleOpen={() => toggleSection("roleType")}
      >
        {renderPreferenceChips(
          FILTER_GROUPS.roleType,
          preferencesDraft.preferred_role_types || [],
          (value) => togglePreferenceValue("preferred_role_types", value),
          "tracker-chip-list--scrollable"
        )}
      </PreferenceSection>

      <PreferenceSection
        sectionKey="location"
        title="Location"
        isOpen={openSections.location}
        onToggleOpen={() => toggleSection("location")}
      >
        {renderPreferenceChips(
          LOCATION_OPTIONS,
          preferencesDraft.preferred_locations || [],
          (value) => togglePreferenceValue("preferred_locations", value)
        )}
      </PreferenceSection>

      <div className="tracker-preferences-panel__toggle-row">
        <button
          type="button"
          className={`chip-button tracker-chip tracker-chip--toggle ${
            preferencesDraft.is_lgbt_friendly_only
              ? "tracker-chip--active"
              : ""
          }`}
          aria-pressed={preferencesDraft.is_lgbt_friendly_only}
          onClick={() =>
            setPreferencesDraft((current) => ({
              ...current,
              is_lgbt_friendly_only: !current.is_lgbt_friendly_only,
            }))
          }
        >
          <span>LGBTQ-friendly only</span>
          {preferencesDraft.is_lgbt_friendly_only ? (
            <span className="tracker-chip__check" aria-hidden="true">
              ✓
            </span>
          ) : null}
        </button>
      </div>

      <div className="tracker-preferences-panel__footer">
        <button
          type="button"
          className="button button--primary"
          onClick={onSavePreferences}
          disabled={isSavingPreferences}
        >
          {isSavingPreferences ? "Saving..." : "Save preferences"}
        </button>
      </div>
    </div>
  );
}

export default TrackerPreferencesPanel;