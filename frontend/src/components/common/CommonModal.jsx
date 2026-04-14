import React, { useEffect, useId } from "react";
import "../../styles/common/common-modal.css";

/**
 * Renders a reusable modal dialog with an overlay.
 *
 * This component is intentionally presentation-focused and reusable across
 * product surfaces such as tracker preferences, resume upload, profile editing,
 * and job details.
 *
 * @param {{
 *   isOpen: boolean,
 *   title: string,
 *   onClose: () => void,
 *   children: React.ReactNode,
 *   size?: "sm" | "md" | "lg",
 *   iconImage?: string | null,
 *   iconAlt?: string
 * }} props
 * @returns {JSX.Element | null} Modal UI.
 */
function CommonModal({
  isOpen,
  title,
  onClose,
  children,
  size = "md",
  iconImage = null,
  iconAlt = "",
}) {
  const titleId = useId();

  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }

    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    /**
     * Handles Escape key closing behavior.
     *
     * @param {KeyboardEvent} event Keyboard event.
     */
    function handleKeyDown(event) {
      if (event.key === "Escape") {
        onClose();
      }
    }

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = originalOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) {
    return null;
  }

  return (
    <div
      className="common-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
    >
      <button
        type="button"
        className="common-modal__overlay"
        aria-label="Close modal"
        onClick={onClose}
      />

      <div className={`common-modal__panel common-modal__panel--${size}`}>
        <div className="common-modal__header">
          <div className="common-modal__title-wrap">
            {iconImage ? (
              <img
                src={iconImage}
                alt={iconAlt}
                className="common-modal__icon-image"
              />
            ) : null}

            <h2 id={titleId} className="common-modal__title">
              {title}
            </h2>
          </div>

          <button
            type="button"
            className="common-modal__close"
            aria-label="Close modal"
            onClick={onClose}
          >
            ×
          </button>
        </div>

        <div className="common-modal__body">{children}</div>
      </div>
    </div>
  );
}

export default CommonModal;