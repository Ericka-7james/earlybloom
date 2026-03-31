import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import "../styles/components/auth.css";
import { signUp } from "../lib/auth/authApi";
import PetalloMascot from "../assets/bloombug/bloombugFam/Petaloo.png";

const WELCOME_MODAL_PENDING_KEY = "earlybloom_welcome_modal_pending";

/**
 * Validates password strength for the sign-up flow.
 *
 * @param {string} password Raw password value.
 * @returns {string} Validation message or empty string.
 */
function validatePassword(password) {
  if (password.length < 10) {
    return "Password must be at least 10 characters.";
  }

  if (!/[A-Z]/.test(password)) {
    return "Include at least one uppercase letter.";
  }

  if (!/[a-z]/.test(password)) {
    return "Include at least one lowercase letter.";
  }

  if (!/[0-9]/.test(password)) {
    return "Include at least one number.";
  }

  if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
    return "Include at least one special character.";
  }

  return "";
}

/**
 * Renders the sign-up page.
 *
 * @returns {JSX.Element} Sign-up page.
 */
function SignUp() {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    confirm: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  /**
   * Updates local form state.
   *
   * @param {React.ChangeEvent<HTMLInputElement>} event Input change event.
   * @returns {void}
   */
  function handleChange(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  /**
   * Submits the sign-up form.
   *
   * On success, queues the welcome modal and redirects to the jobs page.
   *
   * @param {React.FormEvent<HTMLFormElement>} event Form submit event.
   * @returns {Promise<void>}
   */
  async function handleSubmit(event) {
    event.preventDefault();
    setError("");

    if (!form.email.trim()) {
      setError("Enter your email.");
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

    setLoading(true);

    try {
      await signUp({
        email: form.email.trim(),
        password: form.password,
        displayName: form.name.trim(),
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
    <div className="auth-page auth-page--signup">
      <section className="container section-pad">
        <div className="auth-stage">
          <div className="section-card auth-side">
            <div className="auth-side__inner">
              <div className="eyebrow-pill">Meet Petallo</div>

              <h1 className="auth-side__title">
                Plant your account and grow your search with purpose.
              </h1>

              <p className="auth-side__copy">
                EarlyBloom started with entry-level and junior job seekers in
                mind, but your path might stretch across more than one level.
                Creating an account helps us remember your preferences, keep
                your resume close, and build a search experience that feels
                more grounded and inclusive.
              </p>

              <div className="auth-side__chips" aria-label="Account benefits">
                <span className="tag-chip">Saved preferences</span>
                <span className="tag-chip">Resume-ready flow</span>
                <span className="tag-chip">Inclusive by design</span>
              </div>
            </div>
          </div>

          <div className="section-card auth-form-card">
            <header className="auth-form-card__header">
              <div className="auth-form-card__header-copy">
                <h2 className="auth-form-card__title">Create account</h2>
                <p className="auth-form-card__text">
                  Save your resume, role preferences, and future search flow.
                </p>
              </div>

              <img
                src={PetalloMascot}
                alt="Petallo icon"
                className="auth-form-card__icon"
              />
            </header>

            <form className="auth-form" onSubmit={handleSubmit} noValidate>
              {error ? (
                <div
                  className="auth-form__message auth-form__message--error"
                  role="alert"
                >
                  {error}
                </div>
              ) : null}

              <div className="auth-form__grid">
                <div className="auth-form__field auth-form__field--full">
                  <label className="auth-form__label" htmlFor="name">
                    Name
                  </label>
                  <input
                    id="name"
                    className="auth-form__input"
                    name="name"
                    value={form.name}
                    onChange={handleChange}
                    autoComplete="name"
                    placeholder="Your name"
                  />
                </div>

                <div className="auth-form__field auth-form__field--full">
                  <label className="auth-form__label" htmlFor="email">
                    Email
                  </label>
                  <input
                    id="email"
                    className="auth-form__input"
                    name="email"
                    type="email"
                    value={form.email}
                    required
                    onChange={handleChange}
                    autoComplete="email"
                    inputMode="email"
                    placeholder="you@example.com"
                  />
                </div>

                <div className="auth-form__field">
                  <label className="auth-form__label" htmlFor="password">
                    Password
                  </label>
                  <input
                    id="password"
                    className="auth-form__input"
                    name="password"
                    type="password"
                    value={form.password}
                    required
                    onChange={handleChange}
                    autoComplete="new-password"
                    placeholder="Create a password"
                  />
                </div>

                <div className="auth-form__field">
                  <label className="auth-form__label" htmlFor="confirm">
                    Confirm password
                  </label>
                  <input
                    id="confirm"
                    className="auth-form__input"
                    name="confirm"
                    type="password"
                    value={form.confirm}
                    required
                    onChange={handleChange}
                    autoComplete="new-password"
                    placeholder="Re-enter password"
                  />
                </div>
              </div>

              <p className="auth-form__hint">
                Your password should be harder to crack than a stubborn walnut.
              </p>

              <ul
                className="auth-form__requirements"
                aria-label="Password requirements"
              >
                <li>At least 10 characters</li>
                <li>One uppercase letter and one lowercase letter</li>
                <li>One number and one special character</li>
              </ul>

              <div className="auth-form__actions">
                <button
                  className="button button--primary auth-form__submit"
                  disabled={loading}
                >
                  {loading ? "Creating..." : "Create account"}
                </button>
              </div>
            </form>

            <p className="auth-form-card__footer">
              Already have an account?{" "}
              <Link className="auth-form-card__footer-link" to="/sign-in">
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