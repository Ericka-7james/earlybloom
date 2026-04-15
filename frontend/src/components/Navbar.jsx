import { Link, NavLink, useNavigate } from "react-router-dom";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import BloombugAppIcon from "../assets/bloombug/BloombugAppIcon.png";
import { useAuth } from "../hooks/useAuth";
import "../styles/components/navbar.css";

/**
 * Renders the shared application navigation.
 *
 * Public routes stay available even while auth is resolving.
 *
 * @returns {JSX.Element} Top navigation bar.
 */
function Navbar() {
  const navigate = useNavigate();
  const { user, loading, handleSignOut } = useAuth();

  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const menuRef = useRef(null);

  const closeMenu = useCallback(() => {
    setIsMenuOpen(false);
  }, []);

  const toggleMenu = useCallback(() => {
    setIsMenuOpen((current) => !current);
  }, []);

  const onSignOut = useCallback(async () => {
    await handleSignOut();
    setIsMenuOpen(false);
    navigate("/");
  }, [handleSignOut, navigate]);

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
  }, [closeMenu]);

  const desktopLinks = useMemo(() => {
    const publicLinks = [
      { type: "link", to: "/", label: "Home" },
      { type: "link", to: "/jobs", label: "Jobs" },
      { type: "link", to: "/learn-more", label: "Learn More" },
    ];

    if (user) {
      return [
        { type: "link", to: "/", label: "Home" },
        { type: "link", to: "/jobs", label: "Jobs" },
        { type: "link", to: "/tracker", label: "Tracker" },
        { type: "link", to: "/profile", label: "Profile" },
        { type: "button", label: "Sign out", onClick: onSignOut },
      ];
    }

    return [
      ...publicLinks,
      {
        type: "link",
        to: "/sign-in",
        label: loading ? "Checking sign in..." : "Sign in",
        accent: true,
      },
    ];
  }, [loading, onSignOut, user]);

  const mobileLinks = useMemo(() => {
    const publicLinks = [
      { type: "link", to: "/", label: "Home" },
      { type: "link", to: "/jobs", label: "Jobs" },
      { type: "link", to: "/learn-more", label: "Learn More" },
    ];

    if (user) {
      return [
        { type: "link", to: "/", label: "Home" },
        { type: "link", to: "/jobs", label: "Jobs" },
        { type: "link", to: "/tracker", label: "Tracker" },
        { type: "link", to: "/profile", label: "Profile" },
        { type: "button", label: "Sign out", onClick: onSignOut, danger: true },
      ];
    }

    return [
      ...publicLinks,
      {
        type: "link",
        to: "/sign-in",
        label: loading ? "Checking sign in..." : "Sign in",
        accent: true,
      },
    ];
  }, [loading, onSignOut, user]);

  function renderDesktopItem(item) {
    const itemKey = item.key || `${item.type}-${item.label}`;

    if (item.type === "button") {
      return (
        <button
          key={itemKey}
          type="button"
          className="nav-link nav-link--button"
          onClick={item.onClick}
        >
          {item.label}
        </button>
      );
    }

    if (item.disabled) {
      return (
        <span
          key={itemKey}
          className="nav-link nav-link--muted"
          aria-disabled="true"
          title="Coming soon"
        >
          {item.label}
        </span>
      );
    }

    return (
      <NavLink
        key={itemKey}
        to={item.to}
        end={item.to === "/"}
        className={({ isActive }) =>
          [
            "nav-link",
            isActive ? "nav-link--active" : "",
            item.accent ? "nav-link--accent" : "",
          ]
            .filter(Boolean)
            .join(" ")
        }
      >
        {item.label}
      </NavLink>
    );
  }

  function renderMobileItem(item) {
    const itemKey = item.key || `${item.type}-${item.label}`;

    if (item.type === "button") {
      return (
        <button
          key={itemKey}
          type="button"
          className={[
            "nav-menu__item",
            "nav-menu__item--button",
            item.danger ? "nav-menu__item--danger" : "",
          ]
            .filter(Boolean)
            .join(" ")}
          onClick={item.onClick}
        >
          {item.label}
        </button>
      );
    }

    if (item.disabled) {
      return (
        <span
          key={itemKey}
          className="nav-menu__item nav-menu__item--muted"
          aria-disabled="true"
          title="Coming soon"
        >
          {item.label}
        </span>
      );
    }

    return (
      <NavLink
        key={itemKey}
        to={item.to}
        end={item.to === "/"}
        className={({ isActive }) =>
          [
            "nav-menu__item",
            isActive ? "nav-menu__item--active" : "",
            item.accent ? "nav-menu__item--accent" : "",
          ]
            .filter(Boolean)
            .join(" ")
        }
        onClick={closeMenu}
      >
        {item.label}
      </NavLink>
    );
  }

  return (
    <header className="site-header">
      <div className="site-header__inner container--product">
        <div className="navbar">
          <Link to="/" className="brand" aria-label="EarlyBloom home">
            <img
              src={BloombugAppIcon}
              alt="EarlyBloom Bloombug icon"
              className="brand__icon"
            />

            <div className="brand__text">
              <span className="brand__title">EarlyBloom</span>
              <span className="brand__subtitle">
                Real roles for early careers
              </span>
            </div>
          </Link>

          <nav className="nav-links" aria-label="Primary navigation">
            {desktopLinks.map(renderDesktopItem)}
          </nav>

          <div className="nav-menu" ref={menuRef}>
            <button
              type="button"
              className="nav-menu__trigger"
              onClick={toggleMenu}
              aria-label={isMenuOpen ? "Close navigation menu" : "Open navigation menu"}
              aria-expanded={isMenuOpen}
              aria-haspopup="menu"
            >
              <span className="nav-menu__dots" aria-hidden="true">
                ⋮
              </span>
            </button>

            {isMenuOpen ? (
              <div className="nav-menu__dropdown" role="menu">
                <div className="nav-menu__panel">
                  {mobileLinks.map(renderMobileItem)}
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </header>
  );
}

export default Navbar;