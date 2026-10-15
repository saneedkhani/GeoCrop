import { create } from "zustand";

type User = { id: string; username: string; email: string; role: string };

type AuthState = {
  token: string | null;
  user: User | null;
  signIn: (token: string, user: User) => void;
  signOut: () => void;
};

const KEY = "geocrop.auth";

function load(): Pick<AuthState, "token" | "user"> {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) return JSON.parse(raw);
  } catch {
    /* storage unavailable */
  }
  return { token: null, user: null };
}

export const useAuth = create<AuthState>((set) => ({
  ...load(),
  signIn: (token, user) => {
    try {
      localStorage.setItem(KEY, JSON.stringify({ token, user }));
    } catch {
      /* ignore */
    }
    set({ token, user });
  },
  signOut: () => {
    try {
      localStorage.removeItem(KEY);
    } catch {
      /* ignore */
    }
    set({ token: null, user: null });
  },
}));
