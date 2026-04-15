import { Link } from "react-router-dom";
import bloombugMarketingMascot from "../assets/bloombug/BloombugMarketingMascot.png";
import BloombugCareerGarden from "../assets/bloombug/BloombugCareerGarden.png";

/**
 * Renders the EarlyBloom landing page.
 *
 * This page is designed mobile-first and acts as the first impression
 * for the product. It introduces the mission, shows the mascot, and
 * gives structure that future product pages can visually follow.
 *
 * @returns {JSX.Element} The home page content.
 */
function Home() {
  return (
    <div className="home-page">
      <section className="hero container section-pad">
        <div className="hero__content">
          <div className="eyebrow-pill">
            Mobile-first job matching for people building careers in tech
          </div>

          <h1 className="hero__title">
            Find the roles you can actually grow into.
          </h1>

          <p className="hero__description">
            EarlyBloom is tailored for people trying to break into or grow
            within the tech field, including software engineering, IT, UX, data,
            and related paths. It is built to make the job search feel clearer,
            more realistic, and easier to manage.
          </p>

          <div className="hero__actions">
            <Link to="/jobs" className="button button--primary">
              Start Exploring
            </Link>

            <Link to="/learn-more" className="button button--secondary">
              Learn More
            </Link>
          </div>

          <div className="hero__tags" aria-label="Product highlights">
            <span className="tag-chip">Fit scoring</span>
            <span className="tag-chip">Early-career filtering</span>
            <span className="tag-chip">Application tracking</span>
          </div>
        </div>

        <div className="hero__media">
          <div className="hero-card">
            <img
              src={bloombugMarketingMascot}
              alt="Bloombug mascot holding a small seedling"
              className="hero-card__image"
            />
          </div>
        </div>
      </section>

      <section id="mission" className="container section-pad">
        <div className="section-card">
          <p className="section-label">Mission</p>
          <h2 className="section-title">
            Early-career tech roles should feel easier to find.
          </h2>
          <p className="section-copy">
            Too many job boards overwhelm people in the tech field with roles
            that look entry-level on the surface but ask for far more than they
            should. EarlyBloom is designed to surface more realistic
            opportunities and make the search feel less chaotic.
          </p>
        </div>
      </section>

      <section id="how-it-works" className="container section-pad">
        <div className="section-heading">
          <p className="section-label">How it works</p>
          <h2 className="section-title">A simpler path through the job search.</h2>
        </div>

        <div className="feature-grid">
          <article className="feature-card">
            <div className="feature-card__number">01</div>
            <h3 className="feature-card__title">Read the resume</h3>
            <p className="feature-card__copy">
              Parse experience, skills, and tools to better understand role fit.
            </p>
          </article>

          <article className="feature-card">
            <div className="feature-card__number">02</div>
            <h3 className="feature-card__title">Score the listings</h3>
            <p className="feature-card__copy">
              Highlight roles that better match early-career candidates and flag
              listings with misleading expectations.
            </p>
          </article>

          <article className="feature-card">
            <div className="feature-card__number">03</div>
            <h3 className="feature-card__title">Track progress</h3>
            <p className="feature-card__copy">
              Save roles, manage applications, and keep your search organized in
              one place.
            </p>
          </article>
        </div>
      </section>

      <section id="future-tools" className="container section-pad">
        <div className="callout-card">
          <div className="callout-card__media">
            <img
              src={BloombugCareerGarden}
              alt="Bloombug user interface mascot illustration"
              className="callout-card__image"
            />
          </div>

          <div className="callout-card__content">
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
          </div>
        </div>
      </section>
    </div>
  );
}

export default Home;