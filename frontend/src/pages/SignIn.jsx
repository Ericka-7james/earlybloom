import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import "../styles/components/auth.css";
import { getSession, signIn } from "../lib/auth/authApi";
import { notifyAuthChanged } from "../hooks/useAuth";
import PetalloMascot from "../assets/bloombug/bloombugFam/Petaloo.png";

const WELCOME_MODAL_PENDING_KEY = "earlybloom_welcome_modal_pending";

function SignIn() {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    email: "",
    password: "",
  });

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function handleChange(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      await signIn({
        email: form.email.trim(),
        password: form.password,
      });

      const session = await getSession();

      if (!session?.authenticated || !session?.user) {
        throw new Error("Sign in succeeded, but the session could not be confirmed.");
      }

      notifyAuthChanged();
      window.sessionStorage.setItem(WELCOME_MODAL_PENDING_KEY, "true");
      navigate("/jobs");
    } catch (submitError) {
      setError(submitError.message || "Login failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page auth-page--signin">
      <section className="container section-pad">
        <div className="auth-stage">
          <div className="section-card auth-side">
            <div className="auth-side__inner">
              <div className="eyebrow-pill">Welcome back</div>

              <h1 className="auth-side__title">
                Step back in and keep your search growing.
              </h1>

              <p className="auth-side__copy">
                Sign in to revisit saved roles, continue your search, and pick
                up right where you left off.
              </p>

              <div className="auth-side__chips" aria-label="Sign-in benefits">
                <span className="tag-chip">Saved roles</span>
                <span className="tag-chip">Resume access</span>
                <span className="tag-chip">Faster apply flow</span>
              </div>
            </div>
          </div>

          <div className="section-card auth-form-card">
            <header className="auth-form-card__header">
              <div className="auth-form-card__header-copy">
                <h2 className="auth-form-card__title">Sign in</h2>
                <p className="auth-form-card__text">
                  Access your saved progress and continue your search.
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

                <div className="auth-form__field auth-form__field--full">
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
                    autoComplete="current-password"
                    placeholder="Enter your password"
                  />
                </div>
              </div>

              <div className="auth-form__actions">
                <button
                  className="button button--primary auth-form__submit"
                  disabled={loading}
                >
                  {loading ? "Signing in..." : "Sign in"}
                </button>
              </div>
            </form>

            <p className="auth-form-card__footer">
              No account yet?{" "}
              <Link className="auth-form-card__footer-link" to="/sign-up">
                Create one
              </Link>
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}

export default SignIn;