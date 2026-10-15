import { useEffect, useState, type ReactNode } from "react";
import { Link, Navigate, NavLink, Outlet, useLocation } from "react-router-dom";
import { AUTH_REQUIRED } from "../config";
import { useAuth } from "../store/auth";

export function RequireAuth({ children }: { children: ReactNode }) {
  const token = useAuth((s) => s.token);
  return token || !AUTH_REQUIRED ? <>{children}</> : <Navigate to="/login" replace />;
}

const NAV = [
  { to: "/", label: "Home", end: true },
  { to: "/dashboard", label: "Dashboard" },
  { to: "/map", label: "Live Map" },
  { to: "/analyze", label: "Analyze Imagery" },
  { to: "/models", label: "Models" },
];

export default function SiteLayout() {
  const { user, signOut } = useAuth();
  const [open, setOpen] = useState(false);
  const { pathname, hash } = useLocation();

  useEffect(() => setOpen(false), [pathname]);
  useEffect(() => {
    if (hash) document.getElementById(hash.slice(1))?.scrollIntoView();
    else window.scrollTo(0, 0);
  }, [pathname, hash]);

  return (
    <div className="site">
      <header className="site-header">
        <div className="header-inner">
          <Link to="/" className="brand">GeoCrop</Link>
          <nav className="primary-nav" aria-label="Main">
            {NAV.map((n) => (
              <NavLink key={n.to} to={n.to} end={n.end}>{n.label}</NavLink>
            ))}
            <Link to="/#about" className="secondary">About Us</Link>
          </nav>
          <div className="header-actions">
            {user ? (
              <>
                <span className="user-chip" title={user.username}>{user.username.slice(0, 1).toUpperCase()}</span>
                <button className="btn-ghost btn-sm" onClick={signOut}>Log out</button>
              </>
            ) : (
              <>
                <Link to="/login" className="btn-ghost btn-sm">Log in</Link>
                <Link to="/signup" className="btn-primary btn-sm">Get Started</Link>
              </>
            )}
          </div>
          <button className={`nav-toggle ${open ? "open" : ""}`} aria-label="Toggle menu" aria-expanded={open}
            onClick={() => setOpen(!open)}>
            <span /><span /><span />
          </button>
        </div>
        <nav className={`mobile-nav ${open ? "open" : ""}`} aria-label="Mobile">
          {NAV.map((n) => <Link key={n.to} to={n.to}>{n.label}</Link>)}
          <Link to="/#about">About Us</Link>
          <Link to="/status">System Status</Link>
          {user ? <a href="#" onClick={(e) => { e.preventDefault(); signOut(); }}>Log out</a>
            : <><Link to="/login">Log in</Link><Link to="/signup">Get Started</Link></>}
        </nav>
      </header>

      <main className="site-main">
        <Outlet />
      </main>

      <footer className="site-footer">
        <div className="footer-inner">
          <div className="footer-grid">
            <div className="footer-col">
              <Link to="/" className="brand">GeoCrop</Link>
              <p className="footer-desc">Actionable satellite-based crop intelligence and field mapping for modern agriculture.</p>
            </div>
            <div className="footer-col">
              <h4>Platform</h4>
              <Link to="/dashboard">Analytics Dashboard</Link>
              <Link to="/map">Interactive Live Map</Link>
              <Link to="/analyze">Analyze Imagery</Link>
              <Link to="/models">Models</Link>
              <Link to="/status">System Status</Link>
            </div>
            <div className="footer-col">
              <h4>Company</h4>
              <Link to="/#about">About Us</Link>
              <Link to="/#section-crops">Crop Coverage</Link>
              <Link to="/signup">Get Started</Link>
            </div>
          </div>
          <div className="footer-bottom">
            <span>&copy; {new Date().getFullYear()} GeoCrop. All rights reserved.</span>
            <span>Built on Sentinel-2 imagery and USDA Cropland Data Layer</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
