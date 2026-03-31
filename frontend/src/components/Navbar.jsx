import { Link } from "react-router-dom";
import BloombugAppIcon from "../assets/bloombug/BloombugAppIcon.png";

/**
 * Renders the shared site navigation.
 *
 * @returns {JSX.Element} Top navigation bar.
 */
function Navbar() {
  return (
    <header className="site-header">
      <div className="container navbar">
        <Link to="/" className="brand" aria-label="EarlyBloom home">
          <img
            src={BloombugAppIcon}
            alt="EarlyBloom Bloombug icon"
            className="brand__icon"
          />
          <div className="brand__text">
            <span className="brand__title">EarlyBloom</span>
            <span className="brand__subtitle">Grow into the right role</span>
          </div>
        </Link>

        <nav className="nav-links" aria-label="Primary navigation">
          <Link to="/" className="nav-link">
            Home
          </Link>
          <Link to="/jobs" className="nav-link">
            Jobs
          </Link>
          <Link to="/sign-in" className="nav-link">
            Sign in
          </Link>
          <Link to="/sign-up" className="nav-link">
            Sign up
          </Link>
        </nav>
      </div>
    </header>
  );
}

export default Navbar;