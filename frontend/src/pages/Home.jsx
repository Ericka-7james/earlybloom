import bloombugMarketingMascot from "../assets/bloombug/BloombugMarketingMascot.png";
import BloombugCareerGarden from "../assets/bloombug/BloombugCareerGarden.png";

/**
 * Renders the EarlyBloom landing page.
 *
 * This page is designed mobile-first and acts as the first impression
 * for the product. It introduces the mission, shows the mascot, and
 * gives structure that future product pages can visually follow.
 *
 * Sections included:
 * - hero banner
 * - mission and value proposition
 * - simple "how it works" overview
 * - future tools preview
 *
 * @returns {JSX.Element} The home page content.
 */
function Home() {
  return (
    <div className="home-page">
      <section className="hero container section-pad">
        <div className="hero__content">
          <div className="eyebrow-pill">
            Mobile-first job matching for early careers
          </div>

          <h1 className="hero__title">
            Find the roles you can actually grow into.
          </h1>

          <p className="hero__description">
            EarlyBloom helps entry-level and junior candidates cut through fake
            “entry-level” listings, focus on realistic opportunities, and build
            a cleaner job search strategy with less noise.
          </p>

          <div className="hero__actions">
            <button type="button" className="button button--primary">
              Start Exploring
            </button>

            <button type="button" className="button button--secondary">
              See the Mission
            </button>
          </div>

          <div className="hero__tags" aria-label="Product highlights">
            <span className="tag-chip">Real fit scoring</span>
            <span className="tag-chip">Junior-friendly filtering</span>
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
          <h2 className="section-title">Entry-level should mean entry-level.</h2>
          <p className="section-copy">
            Too many job boards flood early-career candidates with listings that
            say “junior” but ask for senior-level expectations. EarlyBloom is
            built to filter the weeds, surface realistic matches, and make the
            search feel less chaotic.
          </p>
        </div>
      </section>

      <section id="how-it-works" className="container section-pad">
        <div className="section-heading">
          <p className="section-label">How it works</p>
          <h2 className="section-title">A simpler path through the job mess.</h2>
        </div>

        <div className="feature-grid">
          <article className="feature-card">
            <div className="feature-card__number">01</div>
            <h3 className="feature-card__title">Read the resume</h3>
            <p className="feature-card__copy">
              Parse resume details to understand skills, experience, and role
              fit.
            </p>
          </article>

          <article className="feature-card">
            <div className="feature-card__number">02</div>
            <h3 className="feature-card__title">Score the listings</h3>
            <p className="feature-card__copy">
              Flag hidden seniority signals and prioritize roles that actually
              match.
            </p>
          </article>

          <article className="feature-card">
            <div className="feature-card__number">03</div>
            <h3 className="feature-card__title">Track progress</h3>
            <p className="feature-card__copy">
              Save roles, manage applications, and keep your job search
              organized.
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
            <h2 className="section-title">A growing toolkit for job seekers.</h2>
            <p className="section-copy">
              Upcoming pages will include a jobs explorer, a resume upload flow,
              and an application tracker built to help users search smarter.
            </p>

            <ul className="soft-list" aria-label="Upcoming features">
              <li>Jobs page with fit labels and filters</li>
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