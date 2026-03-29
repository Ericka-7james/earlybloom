import React, { useMemo } from "react";
import JobCard from "../components/jobs/JobCard.jsx";
import "../styles/components/jobs.css";

/**
 * Temporary mock data for the Jobs page.
 *
 * This shape is intentionally close to what a future API response could look like
 * so the page can transition to backend data with minimal refactoring.
 *
 * @type {Array<{
 *   id: string,
 *   title: string,
 *   company: string,
 *   location: string,
 *   workplaceType: "Remote" | "Onsite" | "Hybrid",
 *   roleType: "Frontend" | "Backend" | "Full Stack" | "Data" | "Product",
 *   description: string,
 *   fitTag: "Real Junior" | "Stretch Role" | "Too Senior",
 *   matchScore: number
 * }>}
 */
const MOCK_JOBS = [
  {
    id: "eb-job-001",
    title: "Junior Frontend Engineer",
    company: "Bloomline",
    location: "Atlanta, GA",
    workplaceType: "Hybrid",
    roleType: "Frontend",
    description:
      "Build accessible user interfaces, support design system updates, and collaborate with product and backend teams on customer-facing features.",
    fitTag: "Real Junior",
    matchScore: 91,
  },
  {
    id: "eb-job-002",
    title: "Software Engineer I",
    company: "North Harbor",
    location: "Remote",
    workplaceType: "Remote",
    roleType: "Full Stack",
    description:
      "Contribute to internal tools and platform features, ship well-tested code, and grow across both frontend and backend workstreams.",
    fitTag: "Real Junior",
    matchScore: 87,
  },
  {
    id: "eb-job-003",
    title: "Associate Backend Developer",
    company: "KiteStack",
    location: "Austin, TX",
    workplaceType: "Onsite",
    roleType: "Backend",
    description:
      "Help maintain APIs, write service integrations, and support platform reliability with strong mentorship from senior engineers.",
    fitTag: "Stretch Role",
    matchScore: 76,
  },
  {
    id: "eb-job-004",
    title: "Frontend Engineer",
    company: "PetalGrid",
    location: "New York, NY",
    workplaceType: "Hybrid",
    roleType: "Frontend",
    description:
      "Own polished UI work across core product surfaces, improve component consistency, and partner with design on new experiences.",
    fitTag: "Stretch Role",
    matchScore: 72,
  },
  {
    id: "eb-job-005",
    title: "Senior React Engineer",
    company: "Riverpath Labs",
    location: "Remote",
    workplaceType: "Remote",
    roleType: "Frontend",
    description:
      "Lead architecture decisions, define frontend standards, and mentor cross-functional engineering teams across large-scale initiatives.",
    fitTag: "Too Senior",
    matchScore: 43,
  },
  {
    id: "eb-job-006",
    title: "Data Analyst, Early Career",
    company: "Larkspur Health",
    location: "Chicago, IL",
    workplaceType: "Hybrid",
    roleType: "Data",
    description:
      "Turn hiring and product metrics into useful dashboards, support reporting workflows, and collaborate on data quality improvements.",
    fitTag: "Real Junior",
    matchScore: 84,
  },
];

/**
 * Defines the currently available filter groups.
 *
 * The UI is intentionally present but non-functional for now.
 * Keeping the structure separate makes it easier to attach state and query params later.
 */
const FILTER_GROUPS = {
  workplace: ["Remote", "Onsite", "Hybrid"],
  roleType: ["Frontend", "Backend", "Full Stack", "Data", "Product"],
};

/**
 * Renders the jobs discovery page.
 *
 * This page is structured to support future API integration with minimal churn:
 * - swap MOCK_JOBS for fetched data
 * - replace static filter controls with controlled inputs
 * - connect list state to query params or API request params
 *
 * @returns {JSX.Element} Jobs page UI.
 */
function Jobs() {
  /**
   * Memoizes the current dataset.
   *
   * This placeholder pattern makes it easy to later swap in transformed API data
   * without changing the rendering structure below.
   */
  const jobs = useMemo(() => MOCK_JOBS, []);

  return (
    <main className="jobs-page">
      <section className="section-pad">
        <div className="container">
          <div className="jobs-hero section-card">
            <div className="jobs-hero__content">
              <span className="eyebrow-pill">EarlyBloom Jobs</span>
              <h1 className="jobs-hero__title">
                Find roles that actually fit where you are.
              </h1>
              <p className="jobs-hero__text">
                We highlight realistic entry-level and junior opportunities so you
                can spend less time decoding vague listings and more time applying
                where it makes sense.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="section-pad jobs-section">
        <div className="container jobs-layout">
          <aside className="jobs-filters section-card" aria-label="Job filters">
            <div className="jobs-filters__header">
              <h2 className="jobs-results__title">Filters</h2>
              <p className="jobs-filters__text">
                UI only for now. Wiring can be added later without reshaping the page.
              </p>
            </div>

            <div className="jobs-filter-group">
              <h3 className="jobs-filter-group__title">Workplace</h3>
              <div className="jobs-chip-list">
                {FILTER_GROUPS.workplace.map((option) => (
                  <button
                    key={option}
                    type="button"
                    className="jobs-chip"
                    aria-pressed="false"
                  >
                    {option}
                  </button>
                ))}
              </div>
            </div>

            <div className="jobs-filter-group">
              <h3 className="jobs-filter-group__title">Role Type</h3>
              <div className="jobs-chip-list">
                {FILTER_GROUPS.roleType.map((option) => (
                  <button
                    key={option}
                    type="button"
                    className="jobs-chip"
                    aria-pressed="false"
                  >
                    {option}
                  </button>
                ))}
              </div>
            </div>
          </aside>

          <div className="jobs-results">
            <div className="jobs-results__header">
              <div>
                <h2 className="jobs-results__title">Open roles</h2>
                <p className="jobs-results__text">
                  {jobs.length} sample roles for layout and interaction development.
                </p>
              </div>
            </div>

            <div className="jobs-list">
              {jobs.map((job) => (
                <JobCard key={job.id} job={job} />
              ))}
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}

export default Jobs;