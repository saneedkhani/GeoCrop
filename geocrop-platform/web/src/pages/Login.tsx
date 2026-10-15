import { useState, type FormEvent } from "react";
import { Link, Navigate } from "react-router-dom";
import { post } from "../api/client";
import { useAuth } from "../store/auth";

export default function Login({ mode }: { mode: "login" | "signup" }) {
  const { token, signIn } = useAuth();
  const [form, setForm] = useState({ username: "", email: "", password: "", confirm_password: "" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (token) return <Navigate to="/dashboard" replace />;
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [k]: e.target.value });

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const res = mode === "login"
        ? await post<{ token: string; user: any }>("/auth/login", { username: form.username, password: form.password })
        : await post<{ token: string; user: any }>("/auth/signup", form);
      signIn(res.token, res.user);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <div className="card auth-card">
        <div>
          <h1>{mode === "login" ? "Welcome back" : "Create your account"}</h1>
          <p className="muted">{mode === "login" ? "Log in to your GeoCrop workspace." : "Start mapping your fields with GeoCrop."}</p>
        </div>
        <form onSubmit={submit} className="form">
          <label>
            {mode === "login" ? "Username or email" : "Username"}
            <input id="username" className="input" value={form.username} onChange={set("username")} autoComplete="username" />
          </label>
          {mode === "signup" && (
            <label>Email<input id="email" className="input" type="email" value={form.email} onChange={set("email")} autoComplete="email" /></label>
          )}
          <label>
            Password
            <input id="password" className="input" type="password" value={form.password} onChange={set("password")}
              autoComplete={mode === "login" ? "current-password" : "new-password"} />
          </label>
          {mode === "signup" && (
            <label>Confirm password<input id="confirm" className="input" type="password" value={form.confirm_password} onChange={set("confirm_password")} autoComplete="new-password" /></label>
          )}
          {error && <div className="alert error">{error}</div>}
          <button className="btn-primary btn-block" disabled={busy}>
            {busy ? "Please wait…" : mode === "login" ? "Log in" : "Create account"}
          </button>
        </form>
        <p className="auth-switch">
          {mode === "login" ? <>New to GeoCrop? <Link to="/signup">Create an account</Link></> : <>Already have an account? <Link to="/login">Log in</Link></>}
        </p>
      </div>
    </div>
  );
}
