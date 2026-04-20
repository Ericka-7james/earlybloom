import NavIcon from "./NavIcon";

/**
 * Renders the signed-in profile menu trigger and dropdown.
 *
 * The trigger now uses the user's selected avatar image instead of the
 * generic profile icon. If no avatar image is available, it safely falls
 * back to the legacy profile icon.
 *
 * @param {object} props - Component props.
 * @param {boolean} props.isOpen - Whether the menu is visible.
 * @param {React.RefObject<HTMLElement>} props.menuRef - Ref for outside click handling.
 * @param {Function} props.onToggle - Toggle handler for the menu button.
 * @param {Function} props.onProfileClick - Handler for navigating to profile.
 * @param {Function} props.onSignOutClick - Handler for signing out.
 * @param {string} props.title - Accessible title text for the trigger.
 * @param {string} [props.avatarSrc] - User avatar image source.
 * @param {string} [props.avatarAlt] - User avatar alt text.
 * @returns {JSX.Element} Profile menu UI.
 */
function ProfileMenu({
  isOpen,
  menuRef,
  onToggle,
  onProfileClick,
  onSignOutClick,
  title,
  avatarSrc,
  avatarAlt,
}) {
  return (
    <div className="app-header__profile-menu" ref={menuRef}>
      <button
        type="button"
        className="app-header__icon-button app-header__avatar-button"
        onClick={onToggle}
        aria-label="Open profile menu"
        aria-expanded={isOpen}
        aria-haspopup="menu"
        title={title}
      >
        {avatarSrc ? (
          <img
            src={avatarSrc}
            alt={avatarAlt || `${title} avatar`}
            className="app-header__avatar-image"
            loading="lazy"
          />
        ) : (
          <NavIcon name="profile" />
        )}
      </button>

      {isOpen ? (
        <div className="app-profile-dropdown" role="menu">
          <div className="app-profile-dropdown__header">
            <span className="app-profile-dropdown__name">{title}</span>
          </div>

          <button
            type="button"
            className="app-profile-dropdown__item"
            onClick={onProfileClick}
            role="menuitem"
          >
            Profile
          </button>

          <button
            type="button"
            className="app-profile-dropdown__item"
            onClick={onSignOutClick}
            role="menuitem"
          >
            Sign out
          </button>
        </div>
      ) : null}
    </div>
  );
}

export default ProfileMenu;