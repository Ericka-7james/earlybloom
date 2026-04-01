import { Link, useNavigate } from "react-router-dom";
import BloombugAppIcon from "../assets/bloombug/BloombugAppIcon.png";
import { useAuth } from "../hooks/useAuth";

/**
 * Renders the shared site navigation.
 *
 * Now session-aware:
 * - Shows auth actions based on login state
 * - Uses backend session (secure cookies)
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

          {loading ? null : user ? (
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
          ) : (
            <>
              <Link to="/sign-in" className="nav-link">
                Sign in
              </Link>
              <Link to="/sign-up" className="nav-link">
                Sign up
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}

export default Navbar;