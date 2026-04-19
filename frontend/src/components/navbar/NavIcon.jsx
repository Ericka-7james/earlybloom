/**
 * Renders a lightweight inline SVG navigation icon.
 *
 * Local icons keep the app shell self-contained and avoid introducing
 * an additional icon dependency for a small navigation surface.
 *
 * @param {object} props - Component props.
 * @param {string} props.name - Icon name.
 * @returns {JSX.Element | null} SVG icon.
 */
function NavIcon({ name }) {
  switch (name) {
    case "home":
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true" className="nav-icon">
          <path
            d="M4 10.5L12 4l8 6.5V20a1 1 0 0 1-1 1h-4.5v-6h-5v6H5a1 1 0 0 1-1-1v-9.5Z"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );
    case "jobs":
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true" className="nav-icon">
          <path
            d="M9 7V5.8A1.8 1.8 0 0 1 10.8 4h2.4A1.8 1.8 0 0 1 15 5.8V7"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <rect
            x="3"
            y="7"
            width="18"
            height="13"
            rx="2.2"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
          />
          <path
            d="M3 12.5h18"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
        </svg>
      );
    case "tracker":
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true" className="nav-icon">
          <path
            d="M6 5.5h12"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
          <path
            d="M6 12h7"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
          <path
            d="M6 18.5h9"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
          <circle
            cx="17.5"
            cy="12"
            r="1.5"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
          />
        </svg>
      );
    case "learn":
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true" className="nav-icon">
          <path
            d="M6 6.5A2.5 2.5 0 0 1 8.5 4H19v14.5A1.5 1.5 0 0 0 17.5 17H8.5A2.5 2.5 0 0 0 6 19.5V6.5Z"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinejoin="round"
          />
          <path
            d="M8.5 7.5h6.5"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
          <path
            d="M8.5 11h7.5"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
        </svg>
      );
    case "search":
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true" className="nav-icon">
          <circle
            cx="11"
            cy="11"
            r="5.8"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
          />
          <path
            d="M16 16l3.8 3.8"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
        </svg>
      );
    case "profile":
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true" className="nav-icon">
          <circle
            cx="12"
            cy="8"
            r="3.2"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
          />
          <path
            d="M5 19.5a7 7 0 0 1 14 0"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
        </svg>
      );
    default:
      return null;
  }
}

export default NavIcon;