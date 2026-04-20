// src/pages/Home.jsx
import { Link } from "react-router-dom";
import bloombugMarketingMascot from "../assets/bloombug/BloombugMarketingMascot.png";
import BloombugCareerGarden from "../assets/bloombug/BloombugCareerGarden.png";

/**
 * Renders the EarlyBloom landing page.
 *
 * This version keeps the page aligned with the page-scoped home.css styles
 * and preserves the existing route destinations and content intent.
 *
 * @returns {JSX.Element} EarlyBloom home page.
 */
function Home() {
  return (
    <div className="app-page home-page">
      <section className="container--product section-pad home-hero-section">
        <div className="home-hero-shell">
          <div className="home-hero-shell__content">
            <div className="eyebrow-pill home-hero-shell__eyebrow">
              Real roles for early careers
            </div>

            <div className="home-hero-shell__copy">
              <h1 className="home-hero-shell__title">
                Find the roles you can actually grow into.
              </h1>

              <p className="home-hero-shell__description">
                EarlyBloom is tailored for people trying to break into or grow
                within the tech field, including software engineering, IT, UX,
                data, and related paths. It is built to make the job search feel
                clearer, more realistic, and easier to manage.
              </p>
            </div>

            <div className="home-hero-shell__actions">
              <Link to="/jobs" className="button button--primary">
                Start Exploring
              </Link>

              <Link to="/learn-more" className="button button--secondary">
                Learn More
              </Link>
            </div>

            <div
              className="home-hero-shell__chips"
              aria-label="Product highlights"
            >
              <span className="tag-chip">Fit scoring</span>
              <span className="tag-chip">Early-career filtering</span>
              <span className="tag-chip">Application tracking</span>
            </div>
          </div>

          <div className="home-hero-shell__aside">
            <div className="home-hero-preview">
              <div className="home-hero-preview__top">
                <p className="home-hero-preview__label">Product view</p>
                <p className="home-hero-preview__eyebrow">
                  Built to feel more like a career tool than a crowded board
                </p>
              </div>

              <div className="home-hero-preview__media-card">
                <img
                  src={bloombugMarketingMascot}
                  alt="Bloombug mascot holding a small seedling"
                  className="home-hero-preview__image"
                />
              </div>

              <div className="home-hero-preview__stats">
                <article className="compact-stat-card home-compact-stat-card">
                  <p className="compact-stat-card__label">Search clarity</p>
                  <p className="compact-stat-card__value">Cleaner</p>
                  <p className="compact-stat-card__meta">
                    Focus on roles that feel more realistic for early careers
                  </p>
                </article>

                <article className="compact-stat-card home-compact-stat-card">
                  <p className="compact-stat-card__label">Role review</p>
                  <p className="compact-stat-card__value">Smarter</p>
                  <p className="compact-stat-card__meta">
                    Surface stronger fits and call out watchouts sooner
                  </p>
                </article>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="container--product section-pad">
        <div className="home-value-strip">
          <div className="home-value-strip__content">
            <p className="section-label">Mission</p>
            <h2 className="section-title">
              Early-career tech roles should feel easier to find.
            </h2>
            <p className="section-copy">
              Too many job boards overwhelm people in the tech field with roles
              that look entry-level on the surface but ask for far more than
              they should. EarlyBloom is designed to surface more realistic
              opportunities and make the search feel less chaotic.
            </p>
          </div>

          <div className="home-value-strip__meta">
            <div className="home-metric-pill">
              <span className="home-metric-pill__title">Product feel</span>
              <span className="home-metric-pill__value">
                Search-first, not clutter-first
              </span>
            </div>

            <div className="home-metric-pill">
              <span className="home-metric-pill__title">Focus</span>
              <span className="home-metric-pill__value">
                Tech paths with clearer fit
              </span>
            </div>
          </div>
        </div>
      </section>

      <section
        id="how-it-works"
        className="container--product section-pad home-section"
      >
        <div className="home-section-heading">
          <p className="section-label">How it works</p>
          <h2 className="section-title">
            A simpler path through the job search.
          </h2>
          <p className="section-copy">
            The product keeps the flow practical: understand the candidate,
            evaluate the listing, and make it easier to stay organized after the
            click.
          </p>
        </div>

        <div className="feature-grid home-feature-grid">
          <article className="feature-card home-feature-card">
            <div className="feature-card__number">01</div>
            <h3 className="feature-card__title">Read the resume</h3>
            <p className="feature-card__copy">
              Parse experience, skills, and tools to better understand role fit.
            </p>
          </article>

          <article className="feature-card home-feature-card">
            <div className="feature-card__number">02</div>
            <h3 className="feature-card__title">Score the listings</h3>
            <p className="feature-card__copy">
              Highlight roles that better match early-career candidates and flag
              listings with misleading expectations.
            </p>
          </article>

          <article className="feature-card home-feature-card">
            <div className="feature-card__number">03</div>
            <h3 className="feature-card__title">Track progress</h3>
            <p className="feature-card__copy">
              Save roles, manage applications, and keep your search organized in
              one place.
            </p>
          </article>
        </div>
      </section>

      <section className="container--product section-pad home-section">
        <div className="home-capability-grid">
          <article className="app-card app-card--compact">
            <div className="app-card__header">
              <p className="section-label">Why it helps</p>
              <h3 className="card-title">Less noise, better signals</h3>
            </div>

            <div className="app-card__content">
              <p className="card-copy">
                EarlyBloom is aimed at reducing the friction that comes from
                misleading role titles, inflated requirements, and scattered
                search workflows.
              </p>
            </div>
          </article>

          <article className="app-card app-card--compact">
            <div className="app-card__header">
              <p className="section-label">Built for use</p>
              <h3 className="card-title">A product shell, not a splash page</h3>
            </div>

            <div className="app-card__content">
              <p className="card-copy">
                The landing page now feels like the same system as Jobs, with
                cleaner surfaces, stronger hierarchy, and product-style content
                blocks instead of generic marketing sections.
              </p>
            </div>
          </article>

          <article className="app-card app-card--compact">
            <div className="app-card__header">
              <p className="section-label">Career flow</p>
              <h3 className="card-title">Search, review, track</h3>
            </div>

            <div className="app-card__content">
              <p className="card-copy">
                The core experience stays centered on helping someone identify
                stronger-fit roles, understand them faster, and keep momentum in
                the application process.
              </p>
            </div>
          </article>
        </div>
      </section>

      <section id="future-tools" className="container--product section-pad">
        <div className="home-callout-card">
          <div className="home-callout-card__media">
            <div className="home-callout-card__image-shell">
              <img
                src={BloombugCareerGarden}
                alt="Bloombug user interface mascot illustration"
                className="callout-card__image"
              />
            </div>
          </div>

          <div className="home-callout-card__content">
            <p className="section-label">What is coming next</p>
            <h2 className="section-title">
              Built for tech careers now, with room to grow over time.
            </h2>
            <p className="section-copy">
              EarlyBloom is currently focused on helping people navigate the
              tech field more clearly, especially in early-career spaces. Over
              time, it can grow into a broader toolkit with more support,
              features, and pathways if that becomes useful.
            </p>

            <ul className="soft-list" aria-label="Upcoming features">
              <li>Job search with fit labels and filters</li>
              <li>Resume upload and skill extraction</li>
              <li>Application tracker with status updates</li>
            </ul>

            <div className="home-callout-card__actions">
              <Link to="/jobs" className="button button--primary">
                Explore jobs
              </Link>

              <Link to="/sign-up" className="button button--secondary">
                Create account
              </Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

export default Home;