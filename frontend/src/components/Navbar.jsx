import { Link } from "react-router-dom";
import bloombugIcon from "../assets/bloombug/BloombugAppIcon.png";

/**
 * Renders the main navigation bar for EarlyBloom.
 *
 * This component is intentionally lightweight and mobile-first.
 * It includes:
 * - the brand icon
 * - the brand name
 * - placeholder navigation links for future pages
 *
 * On larger screens, the layout expands naturally while still
 * keeping a compact and approachable look.
 *
 * @returns {JSX.Element} The application navigation bar.
 */
function Navbar() {
  return (
    <header className="site-header">
      <nav className="navbar container" aria-label="Primary">
        <Link to="/" className="brand" aria-label="EarlyBloom home">
          <img
            src={bloombugIcon}
            alt="Bloombug EarlyBloom mascot icon"
            className="brand__icon"
          />
          <div className="brand__text">
            <span className="brand__title">EarlyBloom</span>
            <span className="brand__subtitle">Real roles for early careers</span>
          </div>
        </Link>

        <div className="nav-links" aria-label="Navigation links">
          <a href="#mission" className="nav-link">
            Mission
          </a>
          <a href="#how-it-works" className="nav-link">
            How It Works
          </a>
          <a href="#future-tools" className="nav-link">
            Tools
          </a>
        </div>
      </nav>
    </header>
  );
}

export default Navbar;