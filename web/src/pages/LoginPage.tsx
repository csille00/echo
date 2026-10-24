import { FormEvent, useState } from "react";
import { Navigate } from "react-router-dom";
import { setDevUserId, useAuth } from "../lib/auth";

export function LoginPage() {
  const { signIn, authenticated, loading, authMode } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [devUserId, setDevUserIdInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!loading && authenticated) {
    return <Navigate to="/" replace />;
  }

  if (authMode === "authentik") {
    return (
      <div className="login-screen">
        <div className="login-card">
          <h1 className="large-title">Journal</h1>
          <p className="footnote">
            Sign in with Authentik at your journal hostname (e.g.{" "}
            <strong>journal.ellisfam.space</strong>). The browser session cookie is used for API
            requests; there is no separate app password.
          </p>
          <button
            className="btn btn-primary"
            type="button"
            onClick={() => {
              window.location.reload();
            }}
          >
            Continue with SSO
          </button>
          <p className="caption" style={{ marginTop: 16 }}>
            If you keep seeing this screen, open the app through the Authentik-protected URL or ask
            your admin to add the UI hostname to the same forward-auth application as the API.
          </p>
        </div>
      </div>
    );
  }

  if (authMode === "dev") {
    const onDevSubmit = (e: FormEvent) => {
      e.preventDefault();
      const id = devUserId.trim();
      if (!id) return;
      setDevUserId(id);
      window.location.href = "/";
    };
    return (
      <div className="login-screen">
        <div className="login-card">
          <h1 className="large-title">Journal</h1>
          <p className="footnote">
            Local dev: set <code>AUTH_BACKEND=dev_header</code> on the API and enter a user UUID.
          </p>
          <form className="login-form" onSubmit={onDevSubmit}>
            <label className="field">
              <span className="caption">User UUID</span>
              <input
                value={devUserId}
                onChange={(e) => setDevUserIdInput(e.target.value)}
                placeholder="00000000-0000-0000-0000-000000000001"
                required
              />
            </label>
            <button className="btn btn-primary" type="submit">Continue</button>
          </form>
        </div>
      </div>
    );
  }

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await signIn(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign in failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="login-screen">
      <div className="login-card">
        <h1 className="large-title">Journal</h1>
        <p className="footnote">Sign in with Supabase (legacy dev mode).</p>
        <form className="login-form" onSubmit={(e) => void onSubmit(e)}>
          <label className="field">
            <span className="caption">Email</span>
            <input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>
          <label className="field">
            <span className="caption">Password</span>
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>
          {error ? <p className="login-error">{error}</p> : null}
          <button className="btn btn-primary" type="submit" disabled={submitting}>
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
