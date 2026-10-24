import { Link, NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../lib/auth";

const navIcon = {
  calendar: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <path d="M16 2v4M8 2v4M3 10h18" />
    </svg>
  ),
  browse: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
      <rect x="14" y="14" width="7" height="7" rx="1" />
    </svg>
  ),
  ask: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M21 11.5a8.4 8.4 0 0 1-1.1 4.2 8.5 8.5 0 0 1-7.4 4.3 8.4 8.4 0 0 1-4.2-1.1L3 21l1.1-5.3" />
    </svg>
  ),
};

function ThemeToggle() {
  const toggle = () => {
    const root = document.documentElement;
    const dark =
      root.getAttribute("data-theme") === "dark" ||
      (!root.getAttribute("data-theme") &&
        window.matchMedia("(prefers-color-scheme: dark)").matches);
    root.setAttribute("data-theme", dark ? "light" : "dark");
    localStorage.setItem("journal-theme", dark ? "light" : "dark");
  };
  return (
    <button type="button" className="theme-toggle" onClick={toggle}>
      Appearance
    </button>
  );
}

export function Layout() {
  const { signOut, apiReachable, authMode } = useAuth();

  return (
    <div className="app">
      {authMode === "authentik" && !apiReachable ? (
        <div className="api-banner" role="status">
          Cannot reach the journal API. On ellis-server run{" "}
          <code>sudo nixos-rebuild switch</code> after updating{" "}
          <code>modules/journal.nix</code> (API proxy must use LAN IP{" "}
          <code>192.168.1.54:8000</code>, not Tailscale).
        </div>
      ) : null}
      <aside className="sidebar">
        <div className="sidebar-brand">Journal</div>
        <NavLink className={({ isActive }) => (isActive ? "nav-item active" : "nav-item")} to="/">
          {navIcon.calendar}
          Calendar
        </NavLink>
        <NavLink
          className={({ isActive }) => (isActive ? "nav-item active" : "nav-item")}
          to="/browse"
        >
          {navIcon.browse}
          Browse
        </NavLink>
        <NavLink className={({ isActive }) => (isActive ? "nav-item active" : "nav-item")} to="/ask">
          {navIcon.ask}
          Ask
        </NavLink>
        <div className="sidebar-footer">
          <button type="button" className="btn btn-ghost" onClick={() => void signOut()}>
            Sign out
          </button>
          <ThemeToggle />
        </div>
      </aside>

      <div className="main">
        <Outlet />
      </div>

      <nav className="tab-bar">
        <NavLink className={({ isActive }) => (isActive ? "tab-item active" : "tab-item")} to="/">
          {navIcon.calendar}
          Calendar
        </NavLink>
        <NavLink
          className={({ isActive }) => (isActive ? "tab-item active" : "tab-item")}
          to="/browse"
        >
          {navIcon.browse}
          Browse
        </NavLink>
        <NavLink className={({ isActive }) => (isActive ? "tab-item active" : "tab-item")} to="/ask">
          {navIcon.ask}
          Ask
        </NavLink>
      </nav>
    </div>
  );
}

export function PageToolbar({
  title,
  action,
}: {
  title: string;
  action?: React.ReactNode;
}) {
  return (
    <header className="toolbar">
      <h1 className="large-title" style={{ margin: 0 }}>{title}</h1>
      <div className="toolbar-actions">{action}</div>
    </header>
  );
}

export function ScanLink() {
  return (
    <Link className="btn btn-primary" to="/review">
      Scan
    </Link>
  );
}
