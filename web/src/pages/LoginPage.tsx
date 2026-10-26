import { FormEvent, useState } from "react";
import { Navigate, useSearchParams } from "react-router-dom";
import { ApiError, oidcStartUrl } from "../lib/api";
import { setDevUserId, useAuth } from "../lib/auth";

export function LoginPage() {
  const {
    signIn,
    register,
    authenticated,
    loading,
    authMode,
    needsSetup,
    apiReachable,
    oidcEnabled,
    oidcDisplayName,
  } = useAuth();
  const [params] = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [devUserId, setDevUserIdInput] = useState("");
  const [error, setError] = useState<string | null>(params.get("error"));
  const [submitting, setSubmitting] = useState(false);

  if (loading) {
    return <p className="footnote" style={{ padding: 24 }}>Loading…</p>;
  }

  if (!loading && authenticated && authMode !== "authentik") {
    return <Navigate to="/" replace />;
  }

  if (authMode === "authentik") {
    return <Navigate to="/" replace />;
  }

  if (!apiReachable) {
    return (
      <div className="login-screen">
        <div className="login-card">
          <h1 className="large-title">Journal</h1>
          <p className="login-error">Cannot reach the journal API.</p>
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
      if (authMode === "local" && needsSetup) {
        await register(email, password, name);
      } else {
        await signIn(email, password);
      }
    } catch (err) {
      setError(err instanceof ApiError || err instanceof Error ? err.message : "Sign in failed");
    } finally {
      setSubmitting(false);
    }
  };

  const setup = authMode === "local" && needsSetup;

  return (
    <div className="login-screen">
      <div className="login-card">
        <h1 className="large-title">Journal</h1>
        <p className="footnote">
          {setup
            ? "Create the admin account. This is the only open signup."
            : authMode === "local"
              ? "Sign in with your email and password."
              : "Sign in with Supabase."}
        </p>
        <form className="login-form" onSubmit={(e) => void onSubmit(e)}>
          {setup ? (
            <label className="field">
              <span className="caption">Name</span>
              <input
                autoComplete="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </label>
          ) : null}
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
              autoComplete={setup ? "new-password" : "current-password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={setup ? 10 : undefined}
              required
            />
          </label>
          {error ? <p className="login-error">{error}</p> : null}
          <button className="btn btn-primary" type="submit" disabled={submitting}>
            {submitting ? "Please wait…" : setup ? "Create account" : "Sign in"}
          </button>
          {authMode === "local" && oidcEnabled ? (
            <a className="btn btn-ghost" href={oidcStartUrl()}>
              Sign in with {oidcDisplayName}
            </a>
          ) : null}
        </form>
      </div>
    </div>
  );
}
