import { NavLink } from "react-router-dom";
import NavIcon from "./NavIcon";

/**
 * Joins optional class names into a single string.
 *
 * @param {...string} classNames - Candidate class names.
 * @returns {string} Joined class name string.
 */
function joinClassNames(...classNames) {
  return classNames.filter(Boolean).join(" ");
}

/**
 * Renders a reusable set of navigation links.
 *
 * This component is shared between:
 * - the centered desktop navigation row
 * - the mobile bottom navigation row
 *
 * @param {object} props - Component props.
 * @param {Array<object>} props.items - Navigation item definitions.
 * @param {string} props.navClassName - Class name for the parent nav container.
 * @param {string} props.itemClassName - Base class name for each link.
 * @param {string} props.activeClassName - Active modifier class name.
 * @param {string} [props.ariaLabel] - Accessible label for the nav element.
 * @param {string} [props.labelClassName] - Label class name for mobile links.
 * @param {string} [props.iconClassName] - Icon wrapper class name for mobile links.
 * @param {boolean} [props.isMobile=false] - Whether to render icon + label layout.
 * @returns {JSX.Element} Navigation link set.
 */
function NavLinks({
  items,
  navClassName,
  itemClassName,
  activeClassName,
  ariaLabel,
  labelClassName,
  iconClassName,
  isMobile = false,
}) {
  return (
    <nav className={navClassName} aria-label={ariaLabel}>
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.to === "/"}
          className={({ isActive }) =>
            joinClassNames(itemClassName, isActive ? activeClassName : "")
          }
        >
          {isMobile ? (
            <>
              <span className={iconClassName} aria-hidden="true">
                <NavIcon name={item.icon} />
              </span>
              <span className={labelClassName}>{item.label}</span>
            </>
          ) : (
            item.label
          )}
        </NavLink>
      ))}
    </nav>
  );
}

export default NavLinks;