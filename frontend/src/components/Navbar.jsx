import { Link, useNavigate } from "react-router-dom";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import BloombugAppIcon from "../assets/bloombug/BloombugAppIcon.png";
import BloomiIcon from "../assets/bloombug/bloombugFam/Bloomi.png";
import NibbletIcon from "../assets/bloombug/bloombugFam/Nibblet.png";
import PetalooIcon from "../assets/bloombug/bloombugFam/Petaloo.png";
import SprigletIcon from "../assets/bloombug/bloombugFam/Spriglet.png";
import { useAuth } from "../hooks/useAuth";
import {
  NAV_AUTH_LINKS,
  NAV_PRIMARY_ITEMS,
} from "./content/Navbar.content.mdx";
import NavIcon from "./navbar/NavIcon";
import NavLinks from "./navbar/NavLinks";
import ProfileMenu from "./navbar/ProfileMenu";
import "../styles/components/navbar.css";

const AVATAR_IMAGE_BY_ID = {
  petaloo: PetalooIcon,
  bloomi: BloomiIcon,
  nibblet: NibbletIcon,
  spriglet: SprigletIcon,
};

/**
 * Returns a concise label for the authenticated user.
 *
 * The header keeps account UI compact, so this helper prefers a short
 * first-name-like value and falls back safely if profile metadata is limited.
 *
 * @param {object | null} user - Current authenticated user.
 * @returns {string} Short user label.
 */
function getUserLabel(user) {
  if (!user) {
    return "Account";
  }

  const metadataName =
    user.user_metadata?.full_name ||
    user.user_metadata?.name ||
    user.user_metadata?.preferred_name ||
    user.profile?.display_name ||
    "";

  const emailPrefix = user.email?.split("@")[0] || "";
  const rawLabel = metadataName || emailPrefix || "Account";

  return rawLabel.trim().split(/\s+/)[0].slice(0, 16) || "Account";
}

/**
 * Resolves the signed-in user's chosen avatar id from available profile or
 * auth metadata and falls back safely to the default Bloombug.
 *
 * @param {object | null} user - Current authenticated user.
 * @returns {string} Normalized avatar id.
 */
function getUserAvatarId(user) {
  const rawAvatar =
    user?.profile?.avatar ||
    user?.user_metadata?.avatar ||
    user?.avatar ||
    "petaloo";

  const normalizedAvatar = String(rawAvatar).trim().toLowerCase();

  return AVATAR_IMAGE_BY_ID[normalizedAvatar] ? normalizedAvatar : "petaloo";
}

/**
 * Renders the shared EarlyBloom application navigation shell.
 *
 * Layout pattern:
 * - top utility header with brand at left and utility actions at right
 * - large centered secondary navigation on desktop
 * - fixed bottom navigation on mobile
 *
 * Auth behavior:
 * - signed-out users see Join and Sign in links
 * - signed-in users see their selected avatar instead of the generic profile icon
 * - clicking the avatar opens a dropdown with Profile and Sign out
 *
 * @returns {JSX.Element} Shared application navigation.
 */
function Navbar() {
  const navigate = useNavigate();
  const { user, loading, handleSignOut } = useAuth();

  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);
  const profileMenuRef = useRef(null);

  const userLabel = useMemo(() => getUserLabel(user), [user]);
  const userAvatarId = useMemo(() => getUserAvatarId(user), [user]);
  const userAvatarSrc = useMemo(
    () => AVATAR_IMAGE_BY_ID[userAvatarId],
    [userAvatarId]
  );

  /**
   * Sends the user to the jobs route from the compact utility header.
   */
  const handleSearchClick = useCallback(() => {
    navigate("/jobs");
  }, [navigate]);

  /**
   * Toggles the signed-in profile dropdown.
   */
  const handleProfileToggle = useCallback(() => {
    if (!user) {
      return;
    }

    setIsProfileMenuOpen((current) => !current);
  }, [user]);

  /**
   * Navigates to the profile page and closes the menu.
   */
  const handleProfileNavigate = useCallback(() => {
    setIsProfileMenuOpen(false);
    navigate("/profile");
  }, [navigate]);

  /**
   * Signs the user out and closes the menu.
   */
  const handleSignOutClick = useCallback(async () => {
    setIsProfileMenuOpen(false);
    await handleSignOut();
    navigate("/");
  }, [handleSignOut, navigate]);

  /**
   * Closes the profile menu when clicking outside or pressing Escape.
   */
  useEffect(() => {
    function handlePointerDown(event) {
      if (!profileMenuRef.current) {
        return;
      }

      if (profileMenuRef.current.contains(event.target)) {
        return;
      }

      setIsProfileMenuOpen(false);
    }

    function handleEscape(event) {
      if (event.key === "Escape") {
        setIsProfileMenuOpen(false);
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

  return (
    <>
      <header className="app-header">
        <div className="app-header__utility">
          <div className="container--product">
            <div className="app-header__utility-row">
              <Link to="/" className="app-brand" aria-label="EarlyBloom home">
                <img
                  src={BloombugAppIcon}
                  alt="EarlyBloom Bloombug icon"
                  className="app-brand__icon"
                />
                <span className="app-brand__name">EarlyBloom</span>
              </Link>

              <div className="app-header__utility-actions">
                <button
                  type="button"
                  className="app-header__icon-button"
                  onClick={handleSearchClick}
                  aria-label="Go to jobs search"
                  title="Search jobs"
                >
                  <NavIcon name="search" />
                </button>

                {user ? (
                  <ProfileMenu
                    isOpen={isProfileMenuOpen}
                    menuRef={profileMenuRef}
                    onToggle={handleProfileToggle}
                    onProfileClick={handleProfileNavigate}
                    onSignOutClick={handleSignOutClick}
                    title={userLabel}
                    avatarSrc={userAvatarSrc}
                    avatarAlt={`${userLabel} avatar`}
                  />
                ) : (
                  <div className="app-header__auth-links">
                    {NAV_AUTH_LINKS.map((item, index) => (
                      <div key={item.to} className="app-header__auth-link-group">
                        {index > 0 ? (
                          <span
                            className="app-header__auth-divider"
                            aria-hidden="true"
                          >
                            |
                          </span>
                        ) : null}

                        <Link to={item.to} className="app-header__auth-link">
                          {item.label === "Sign in" && loading
                            ? "Checking..."
                            : item.label}
                        </Link>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="app-header__section-nav" aria-hidden="false">
          <div className="container--product app-header__section-nav-inner">
            <NavLinks
              items={NAV_PRIMARY_ITEMS}
              navClassName="app-section-nav"
              itemClassName="app-section-nav__link"
              activeClassName="app-section-nav__link--active"
              ariaLabel="Primary navigation"
            />
          </div>
        </div>
      </header>

      <nav className="mobile-bottom-nav" aria-label="Mobile navigation">
        <NavLinks
          items={NAV_PRIMARY_ITEMS}
          navClassName="mobile-bottom-nav__row"
          itemClassName="mobile-bottom-nav__item"
          activeClassName="mobile-bottom-nav__item--active"
          labelClassName="mobile-bottom-nav__label"
          iconClassName="mobile-bottom-nav__icon"
          isMobile
        />
      </nav>
    </>
  );
}

export default Navbar;