import bloombugMarketingMascot from "../assets/bloombug/BloombugMarketingMascot.png";
import BloombugCareerGarden from "../assets/bloombug/BloombugCareerGarden.png";
import "../styles/components/learnmore.css";

/**
 * Renders the Learn More page for EarlyBloom.
 *
 * This page explains:
 * - who built EarlyBloom
 * - why it was created
 * - who it is for
 * - what kind of job-search experience it is trying to create
 *
 * @returns {JSX.Element} Learn More page content.
 */
function LearnMore() {
  return (
    <div className="learnmore-page">
      <section className="learnmore-hero container section-pad">
        <div className="learnmore-hero__content">
          <div className="eyebrow-pill">About EarlyBloom</div>

          <h1 className="learnmore-hero__title">
            Built for people trying to get a real start.
          </h1>

          <p className="learnmore-hero__description">
            EarlyBloom was created to make the job search feel less misleading,
            less cluttered, and more honest for entry-level and junior
            candidates.
          </p>
        </div>

        <div className="learnmore-hero__media">
          <div className="learnmore-hero-card">
            <img
              src={bloombugMarketingMascot}
              alt="Bloombug mascot representing EarlyBloom"
              className="learnmore-hero-card__image"
            />
          </div>
        </div>
      </section>

      <section className="container section-pad">
        <div className="learnmore-story">
          <article className="learnmore-panel">
            <p className="section-label">The creator</p>
            <h2 className="section-title">Why I built this</h2>
            <p className="section-copy">
              I built EarlyBloom because the entry-level job search can feel
              strange and discouraging. Too many listings look beginner-friendly
              on the surface, but once you open them up, they ask for years of
              experience, a long checklist of tools, or a level of confidence
              that does not really match the title.
            </p>
            <p className="section-copy">
              I wanted to build something that helps people search with more
              clarity. Not just another job board, but a place that tries to
              surface roles that feel more realistic, more explainable, and more
              useful for people still growing into their careers.
            </p>
          </article>

          <article className="learnmore-panel">
            <p className="section-label">The purpose</p>
            <h2 className="section-title">What EarlyBloom is for</h2>
            <p className="section-copy">
              EarlyBloom is for people who are early in their careers and tired
              of wasting time on listings that were never truly meant for them.
              It is meant to help users search smarter, notice hidden seniority
              signals, and spend more energy on roles that actually make sense.
            </p>
            <p className="section-copy">
              The long-term vision is to make job searching feel more grounded
              and more manageable through clearer matching, cleaner filters,
              better explanations, and tools that help people stay organized
              while they apply.
            </p>
          </article>
        </div>
      </section>

      <section className="container section-pad">
        <div className="learnmore-values">
          <div className="section-heading">
            <p className="section-label">What matters here</p>
            <h2 className="section-title">
              A softer, smarter job-search experience.
            </h2>
          </div>

          <div className="learnmore-grid">
            <article className="learnmore-card">
              <div className="learnmore-card__number">01</div>
              <h3 className="learnmore-card__title">Honest matching</h3>
              <p className="learnmore-card__copy">
                Roles should be scored with context, not just flashy keywords.
              </p>
            </article>

            <article className="learnmore-card">
              <div className="learnmore-card__number">02</div>
              <h3 className="learnmore-card__title">Less noise</h3>
              <p className="learnmore-card__copy">
                Users should not have to dig through a swamp of misleading
                “entry-level” roles.
              </p>
            </article>

            <article className="learnmore-card">
              <div className="learnmore-card__number">03</div>
              <h3 className="learnmore-card__title">Room to grow</h3>
              <p className="learnmore-card__copy">
                The platform is meant to support people while they are still
                learning, building, and figuring things out.
              </p>
            </article>
          </div>
        </div>
      </section>

      <section className="container section-pad">
        <div className="learnmore-callout">
          <div className="learnmore-callout__media">
            <img
              src={BloombugCareerGarden}
              alt="Bloombug in the EarlyBloom career garden"
              className="learnmore-callout__image"
            />
          </div>

          <div className="learnmore-callout__content">
            <p className="section-label">The bigger idea</p>
            <h2 className="section-title">
              EarlyBloom is meant to feel like a better starting point.
            </h2>
            <p className="section-copy">
              A job search can already be tiring. The point of EarlyBloom is to
              make that process feel more focused, more supportive, and a little
              less like guesswork.
            </p>
            <p className="section-copy">
              It is built for people trying to bloom into the right role, not
              pretend they are already five years ahead.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}

export default LearnMore;