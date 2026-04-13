import { Link, useNavigate } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import BloombugAppIcon from "../assets/bloombug/BloombugAppIcon.png";
import { useAuth } from "../hooks/useAuth";
import "../styles/components/navbar.css";

/**
 * Renders the shared site navigation.
 *
 * Session-aware:
 * - Shows tracker only for signed-in users
 * - Shows sign in for guests and sign out for signed-in users
 * - Uses desktop links above 768px
 * - Uses a compact overflow menu at 768px and below
 *
 * @returns {JSX.Element} Top navigation bar.
 */
function Navbar() {
  const navigate = useNavigate();
  const { user, loading, handleSignOut } = useAuth();

  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const menuRef = useRef(null);

  async function onSignOut() {
    await handleSignOut();
    setIsMenuOpen(false);
    navigate("/");
  }

  function closeMenu() {
    setIsMenuOpen(false);
  }

  function toggleMenu() {
    setIsMenuOpen((current) => !current);
  }

  function handleMobileNavClick() {
    closeMenu();
  }

  useEffect(() => {
    function handlePointerDown(event) {
      if (!menuRef.current || menuRef.current.contains(event.target)) {
        return;
      }

      closeMenu();
    }

    function handleEscape(event) {
      if (event.key === "Escape") {
        closeMenu();
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("touchstart", handlePointerDown);
    document.addEventListener("keydown", handleEscape);

    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("touchstart", handlePointerDown);
      document.removeEventListener("keydown", handleEscape);
    };
  }, []);

  function renderDesktopLinks() {
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
          <Link to="/" className="nav-link">
            Home
          </Link>

          <Link to="/jobs" className="nav-link">
            Jobs
          </Link>

          <Link to="/tracker" className="nav-link">
            Tracker
          </Link>

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
        <Link to="/" className="nav-link">
          Home
        </Link>

        <Link to="/jobs" className="nav-link">
          Jobs
        </Link>

        <Link to="/learn-more" className="nav-link">
          Learn More
        </Link>

        <Link to="/sign-in" className="nav-link">
          Sign in
        </Link>
      </>
    );
  }

  function renderMobileMenuItems() {
    if (loading) {
      return (
        <div className="nav-menu__item-wrap">
          <span className="nav-menu__item nav-menu__item--muted">
            Loading...
          </span>
        </div>
      );
    }

    if (user) {
      return (
        <>
          <Link to="/" className="nav-menu__item" onClick={handleMobileNavClick}>
            Home
          </Link>

          <Link
            to="/jobs"
            className="nav-menu__item"
            onClick={handleMobileNavClick}
          >
            Jobs
          </Link>

          <Link
            to="/tracker"
            className="nav-menu__item"
            onClick={handleMobileNavClick}
          >
            Tracker
          </Link>

          <button
            type="button"
            className="nav-menu__item nav-menu__item--button"
            onClick={onSignOut}
          >
            Sign out
          </button>
        </>
      );
    }

    return (
      <>
        <Link to="/" className="nav-menu__item" onClick={handleMobileNavClick}>
          Home
        </Link>

        <Link
          to="/jobs"
          className="nav-menu__item"
          onClick={handleMobileNavClick}
        >
          Jobs
        </Link>

        <Link
          to="/learn-more"
          className="nav-menu__item"
          onClick={handleMobileNavClick}
        >
          Learn More
        </Link>

        <Link
          to="/sign-in"
          className="nav-menu__item"
          onClick={handleMobileNavClick}
        >
          Sign in
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

        <nav
          className="nav-links nav-links--desktop"
          aria-label="Primary navigation"
        >
          {renderDesktopLinks()}
        </nav>

        <div className="nav-menu" ref={menuRef}>
          <button
            type="button"
            className="nav-menu__trigger"
            onClick={toggleMenu}
            aria-label="Open navigation menu"
            aria-expanded={isMenuOpen}
            aria-haspopup="menu"
          >
            <span className="nav-menu__dots" aria-hidden="true">
              ⋮
            </span>
          </button>

          {isMenuOpen ? (
            <div className="nav-menu__dropdown" role="menu">
              {renderMobileMenuItems()}
            </div>
          ) : null}
        </div>
      </div>
    </header>
  );
}

export default Navbar;