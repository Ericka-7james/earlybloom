import React, { useEffect, useMemo, useState } from "react";
import SeedPlantFrame from "../../assets/landing/petallo_01_seed_plant.png";
import SproutFrame from "../../assets/landing/petallo_02_sprout.png";
import GrowthSmallFrame from "../../assets/landing/petallo_03_growth_small.png";
import "../../styles/common/common-loading-modal.css";

const DEFAULT_FRAMES = [
  SeedPlantFrame,
  SproutFrame,
  GrowthSmallFrame,
];

const DEFAULT_INTERVAL_MS = 650;

function CommonLoadingModal({
  isOpen = false,
  message = "Loading...",
  label = "Page loading",
  frames = DEFAULT_FRAMES,
  intervalMs = DEFAULT_INTERVAL_MS,
}) {
  const safeFrames = useMemo(() => {
    return Array.isArray(frames) && frames.length > 0 ? frames : DEFAULT_FRAMES;
  }, [frames]);

  const [frameIndex, setFrameIndex] = useState(0);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return undefined;
    }

    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");

    function handleChange() {
      setPrefersReducedMotion(mediaQuery.matches);
    }

    handleChange();

    if (typeof mediaQuery.addEventListener === "function") {
      mediaQuery.addEventListener("change", handleChange);
      return () => mediaQuery.removeEventListener("change", handleChange);
    }

    mediaQuery.addListener(handleChange);
    return () => mediaQuery.removeListener(handleChange);
  }, []);

  useEffect(() => {
    if (!isOpen) {
      setFrameIndex(0);
      return undefined;
    }

    if (prefersReducedMotion || safeFrames.length <= 1) {
      setFrameIndex(0);
      return undefined;
    }

    const timerId = window.setInterval(() => {
      setFrameIndex((current) => (current + 1) % safeFrames.length);
    }, intervalMs);

    return () => window.clearInterval(timerId);
  }, [isOpen, prefersReducedMotion, safeFrames, intervalMs]);

  useEffect(() => {
    if (!isOpen || typeof document === "undefined") {
      return undefined;
    }

    const { body } = document;
    const previousOverflow = body.style.overflow;

    body.style.overflow = "hidden";

    return () => {
      body.style.overflow = previousOverflow;
    };
  }, [isOpen]);

  if (!isOpen) {
    return null;
  }

  const currentFrame = safeFrames[frameIndex] || safeFrames[0];

  return (
    <div
      className="common-loading-modal"
      role="presentation"
      aria-hidden="false"
    >
      <div className="common-loading-modal__backdrop" />
      <div
        className="common-loading-modal__panel"
        role="status"
        aria-live="polite"
        aria-label={label}
        aria-busy="true"
      >
        <div className="common-loading-modal__art-wrap">
          <img
            src={currentFrame}
            alt=""
            className="common-loading-modal__art"
            draggable="false"
          />
        </div>

        <div className="common-loading-modal__content">
          <p className="common-loading-modal__eyebrow">EarlyBloom</p>
          <h2 className="common-loading-modal__title">{message}</h2>
          <p className="common-loading-modal__caption">
            We’re getting everything into place.
          </p>
        </div>
      </div>
    </div>
  );
}

export default CommonLoadingModal;