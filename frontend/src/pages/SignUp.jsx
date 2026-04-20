import React, { useMemo, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import "../styles/components/signup-page.css";
import { signUp } from "../lib/auth/authApi";
import PetalloMascot from "../assets/bloombug/bloombugFam/Petaloo.png";
import BloomiIcon from "../assets/bloombug/bloombugFam/Bloomi.png";
import NibbletIcon from "../assets/bloombug/bloombugFam/Nibblet.png";
import PetalooIcon from "../assets/bloombug/bloombugFam/Petaloo.png";
import SprigletIcon from "../assets/bloombug/bloombugFam/Spriglet.png";

const WELCOME_MODAL_PENDING_KEY = "earlybloom_welcome_modal_pending";

const PROFILE_ICON_OPTIONS = [
  {
    id: "petaloo",
    label: "Petaloo",
    image: PetalooIcon,
    isDefault: true,
  },
  {
    id: "bloomi",
    label: "Bloomi",
    image: BloomiIcon,
  },
  {
    id: "nibblet",
    label: "Nibblet",
    image: NibbletIcon,
  },
  {
    id: "spriglet",
    label: "Spriglet",
    image: SprigletIcon,
  },
];

function normalizeName(name) {
  return name.replace(/\s+/g, " ").trim();
}

function validateEmail(email) {
  const trimmedEmail = email.trim();

  if (!trimmedEmail) {
    return "Enter your email.";
  }

  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailPattern.test(trimmedEmail)) {
    return "Enter a valid email address.";
  }

  return "";
}

function getPasswordChecks(password) {
  return {
    length: password.length >= 12,
    uppercase: /[A-Z]/.test(password),
    lowercase: /[a-z]/.test(password),
    number: /[0-9]/.test(password),
    special: /[!@#$%^&*(),.?":{}|<>_\-[\]/+=~`';]/.test(password),
  };
}

function getPasswordStrength(checks) {
  const passedChecks = Object.values(checks).filter(Boolean).length;

  if (passedChecks <= 2) {
    return { label: "Weak", tone: "weak" };
  }

  if (passedChecks <= 4) {
    return { label: "Good", tone: "good" };
  }

  return { label: "Strong", tone: "strong" };
}

function validatePassword(password) {
  const checks = getPasswordChecks(password);

  if (!checks.length) {
    return "Password must be at least 12 characters.";
  }

  if (!checks.uppercase) {
    return "Include at least one uppercase letter.";
  }

  if (!checks.lowercase) {
    return "Include at least one lowercase letter.";
  }

  if (!checks.number) {
    return "Include at least one number.";
  }

  if (!checks.special) {
    return "Include at least one special character.";
  }

  return "";
}

/**
 * Renders the sign-up page.
 *
 * Features:
 * - responsive two-column layout
 * - stronger password validation
 * - duplicate-submit protection
 * - honeypot bot trap
 * - local profile icon selection with a default option
 *
 * @returns {JSX.Element} Sign-up page.
 */
function SignUp() {
  const navigate = useNavigate();

  const defaultIcon =
    PROFILE_ICON_OPTIONS.find((icon) => icon.isDefault)?.id ||
    PROFILE_ICON_OPTIONS[0].id;

  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    confirm: "",
    profileIcon: defaultIcon,
    website: "",
  });

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [acceptedTerms, setAcceptedTerms] = useState(false);

  const passwordChecks = useMemo(
    () => getPasswordChecks(form.password),
    [form.password]
  );

  const passwordStrength = useMemo(
    () => getPasswordStrength(passwordChecks),
    [passwordChecks]
  );

  function handleChange(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  function handleProfileIconSelect(iconId) {
    setForm((current) => ({
      ...current,
      profileIcon: iconId,
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();

    if (loading) {
      return;
    }

    setError("");

    if (form.website.trim()) {
      setError("Unable to complete sign up.");
      return;
    }

    const cleanedName = normalizeName(form.name);
    const cleanedEmail = form.email.trim().toLowerCase();

    if (!cleanedName) {
      setError("Enter your name.");
      return;
    }

    if (cleanedName.length < 2) {
      setError("Name must be at least 2 characters.");
      return;
    }

    if (cleanedName.length > 80) {
      setError("Name must be 80 characters or less.");
      return;
    }

    const emailError = validateEmail(cleanedEmail);
    if (emailError) {
      setError(emailError);
      return;
    }

    const passwordError = validatePassword(form.password);
    if (passwordError) {
      setError(passwordError);
      return;
    }

    if (form.password !== form.confirm) {
      setError("Passwords do not match.");
      return;
    }

    if (!acceptedTerms) {
      setError("Please agree before creating your account.");
      return;
    }

    setLoading(true);

    try {
      await signUp({
        email: cleanedEmail,
        password: form.password,
        displayName: cleanedName,
        profileIcon: form.profileIcon,
      });

      window.sessionStorage.setItem(WELCOME_MODAL_PENDING_KEY, "true");
      navigate("/jobs");
    } catch (submitError) {
      setError(submitError.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="signup-page">
      <section className="container section-pad">
        <div className="signup-layout">
          <aside className="section-card signup-side signup-side--glass">
            <div className="signup-side__inner">
              <div className="eyebrow-pill">Meet the Bloombug crew</div>

              <h1 className="signup-side__title">
                Create your account and start your search with a steadier front
                door.
              </h1>

              <p className="signup-side__copy">
                Pick a profile icon, secure your account, and keep your EarlyBloom
                preferences ready. This layout is built to stay smooth on mobile,
                clear on desktop, and stable as your user base keeps growing.
              </p>

              <div className="signup-side__chips" aria-label="Sign-up benefits">
                <span className="tag-chip">Custom profile icon</span>
                <span className="tag-chip">Secure sign-up flow</span>
                <span className="tag-chip">Responsive layout</span>
              </div>

              <div className="signup-side__feature-grid">
                <div className="info-panel info-panel--soft">
                  <h2 className="card-title">Built for scale</h2>
                  <p className="card-copy">
                    Lightweight UI, guarded submits, and clean validation keep the
                    page fast and calm under heavier traffic.
                  </p>
                </div>

                <div className="info-panel info-panel--soft">
                  <h2 className="card-title">Safer by default</h2>
                  <p className="card-copy">
                    Stronger password requirements and bot-noise reduction add a
                    little armor to the front gate.
                  </p>
                </div>
              </div>
            </div>
          </aside>

          <div className="section-card signup-card signup-card--strong">
            <header className="signup-card__header">
              <div className="signup-card__header-copy">
                <h2 className="signup-card__title">Create account</h2>
                <p className="signup-card__text">
                  Save your profile, resume flow, and preferences in one place.
                </p>
              </div>

              <img
                src={PetalloMascot}
                alt="Petallo icon"
                className="signup-card__icon"
              />
            </header>

            <form className="signup-form" onSubmit={handleSubmit} noValidate>
              {error ? (
                <div
                  className="signup-form__message signup-form__message--error"
                  role="alert"
                >
                  {error}
                </div>
              ) : null}

              <div className="signup-form__field signup-form__field--honeypot">
                <label htmlFor="website">Website</label>
                <input
                  id="website"
                  name="website"
                  value={form.website}
                  onChange={handleChange}
                  autoComplete="off"
                  tabIndex={-1}
                />
              </div>

              <div className="signup-form__grid">
                <div className="signup-form__field signup-form__field--full">
                  <label className="signup-form__label" htmlFor="name">
                    Name
                  </label>
                  <input
                    id="name"
                    className="signup-form__input"
                    name="name"
                    value={form.name}
                    onChange={handleChange}
                    autoComplete="name"
                    placeholder="Your name"
                    maxLength={80}
                    required
                  />
                </div>

                <div className="signup-form__field signup-form__field--full">
                  <label className="signup-form__label" htmlFor="email">
                    Email
                  </label>
                  <input
                    id="email"
                    className="signup-form__input"
                    name="email"
                    type="email"
                    value={form.email}
                    required
                    onChange={handleChange}
                    autoComplete="email"
                    inputMode="email"
                    spellCheck="false"
                    placeholder="you@example.com"
                    maxLength={254}
                  />
                </div>

                <div className="signup-form__field">
                  <label className="signup-form__label" htmlFor="password">
                    Password
                  </label>
                  <input
                    id="password"
                    className="signup-form__input"
                    name="password"
                    type="password"
                    value={form.password}
                    required
                    onChange={handleChange}
                    autoComplete="new-password"
                    placeholder="Create a password"
                    maxLength={128}
                  />
                </div>

                <div className="signup-form__field">
                  <label className="signup-form__label" htmlFor="confirm">
                    Confirm password
                  </label>
                  <input
                    id="confirm"
                    className="signup-form__input"
                    name="confirm"
                    type="password"
                    value={form.confirm}
                    required
                    onChange={handleChange}
                    autoComplete="new-password"
                    placeholder="Re-enter password"
                    maxLength={128}
                  />
                </div>
              </div>

              <section
                className="signup-avatar-picker"
                aria-labelledby="signup-avatar-picker-title"
              >
                <div className="signup-avatar-picker__header">
                  <h3
                    id="signup-avatar-picker-title"
                    className="signup-avatar-picker__title"
                  >
                    Choose your profile icon
                  </h3>
                  <p className="signup-avatar-picker__copy">
                    Petaloo starts as the default, but users can pick any Bloombug
                    friend they want.
                  </p>
                </div>

                <div
                  className="signup-avatar-picker__grid"
                  role="radiogroup"
                  aria-label="Profile icon options"
                >
                  {PROFILE_ICON_OPTIONS.map((icon) => {
                    const isSelected = form.profileIcon === icon.id;

                    return (
                      <button
                        key={icon.id}
                        type="button"
                        role="radio"
                        aria-checked={isSelected}
                        aria-label={icon.label}
                        className={`signup-avatar-option ${
                          isSelected ? "signup-avatar-option--selected" : ""
                        }`}
                        onClick={() => handleProfileIconSelect(icon.id)}
                      >
                        <span className="signup-avatar-option__image-wrap">
                          <img
                            src={icon.image}
                            alt=""
                            className="signup-avatar-option__image"
                            loading="lazy"
                          />
                        </span>

                        <span className="signup-avatar-option__label">
                          {icon.label}
                        </span>

                        {icon.isDefault ? (
                          <span className="signup-avatar-option__meta">
                            Default
                          </span>
                        ) : (
                          <span className="signup-avatar-option__meta">
                            Select
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              </section>

              <section
                className="signup-password-panel"
                aria-labelledby="signup-password-title"
              >
                <div className="signup-password-panel__header">
                  <div>
                    <h3
                      id="signup-password-title"
                      className="signup-password-panel__title"
                    >
                      Password strength
                    </h3>
                    <p className="signup-password-panel__copy">
                      Aim for something tougher than a locked greenhouse in a storm.
                    </p>
                  </div>

                  <span
                    className={`signup-password-strength signup-password-strength--${passwordStrength.tone}`}
                    aria-live="polite"
                  >
                    {passwordStrength.label}
                  </span>
                </div>

                <ul
                  className="signup-password-checklist"
                  aria-label="Password requirements"
                >
                  <li
                    className={`signup-password-checklist__item ${
                      passwordChecks.length
                        ? "signup-password-checklist__item--pass"
                        : ""
                    }`}
                  >
                    At least 12 characters
                  </li>
                  <li
                    className={`signup-password-checklist__item ${
                      passwordChecks.uppercase
                        ? "signup-password-checklist__item--pass"
                        : ""
                    }`}
                  >
                    One uppercase letter
                  </li>
                  <li
                    className={`signup-password-checklist__item ${
                      passwordChecks.lowercase
                        ? "signup-password-checklist__item--pass"
                        : ""
                    }`}
                  >
                    One lowercase letter
                  </li>
                  <li
                    className={`signup-password-checklist__item ${
                      passwordChecks.number
                        ? "signup-password-checklist__item--pass"
                        : ""
                    }`}
                  >
                    One number
                  </li>
                  <li
                    className={`signup-password-checklist__item ${
                      passwordChecks.special
                        ? "signup-password-checklist__item--pass"
                        : ""
                    }`}
                  >
                    One special character
                  </li>
                </ul>
              </section>

              <label className="signup-consent">
                <input
                  className="signup-consent__input"
                  type="checkbox"
                  checked={acceptedTerms}
                  onChange={(event) => setAcceptedTerms(event.target.checked)}
                />
                <span className="signup-consent__text">
                  I understand my account details will be used to personalize my
                  EarlyBloom experience.
                </span>
              </label>

              <div className="signup-form__actions">
                <button
                  className="button button--primary signup-form__submit"
                  disabled={loading}
                >
                  {loading ? "Creating..." : "Create account"}
                </button>
              </div>
            </form>

            <p className="signup-card__footer">
              Already have an account?{" "}
              <Link className="signup-card__footer-link" to="/sign-in">
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}

export default SignUp;