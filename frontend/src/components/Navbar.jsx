import { Link, useNavigate } from "react-router-dom";
import BloombugAppIcon from "../assets/bloombug/BloombugAppIcon.png";
import { useAuth } from "../hooks/useAuth";
import "../styles/components/navbar.css";

/**
 * Renders the shared site navigation.
 *
 * Session-aware:
 * - Shows auth actions based on login state
 * - Keeps auth area stable while session is loading
 *
 * @returns {JSX.Element} Top navigation bar.
 */
function Navbar() {
  const navigate = useNavigate();
  const { user, loading, handleSignOut } = useAuth();

  async function onSignOut() {
    await handleSignOut();
    navigate("/");
  }

  function renderAuthSection() {
    if (loading) {
      return (
        <div className="nav-auth-placeholder" aria-hidden="true">
          <span className="nav-link nav-link--muted">Loading...</span>
        </div>
      );
    }

    if (user) {
      return (
        <>
          <span
            className="nav-link nav-link--muted nav-link--email"
            title={user.email}
          >
            {user.email}
          </span>

          <button
            type="button"
            className="nav-link nav-link--button"
            onClick={onSignOut}
          >
            Sign out
          </button>
        </>
      );
    }

    return (
      <>
        <Link to="/sign-in" className="nav-link">
          Sign in
        </Link>

        <Link to="/learn-more" className="nav-link">
          Learn More
        </Link>
      </>
    );
  }

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

          {renderAuthSection()}
        </nav>
      </div>
    </header>
  );
}

export default Navbar;