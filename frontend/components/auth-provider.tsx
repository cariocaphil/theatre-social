"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { fetchCurrentUser, loginUser, logoutUser, registerUser, type AuthUser } from "@/lib/auth";

const PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

type AuthActionResult = { ok: true } | { ok: false; error: string };

interface AuthContextValue {
  status: AuthStatus;
  user: AuthUser | null;
  login: (email: string, password: string) => Promise<AuthActionResult>;
  register: (username: string, email: string, password: string) => Promise<AuthActionResult>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/**
 * Lightweight authentication state, restored on mount via `GET /auth/me`
 * (the backend session is always the source of truth -- nothing is
 * persisted independently in localStorage). Deliberately a plain Context
 * provider rather than a state-management library: this is the only
 * cross-page state the app needs.
 */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    let isMounted = true;

    fetchCurrentUser(PUBLIC_API_URL).then((result) => {
      if (!isMounted) return;
      if (result.ok) {
        setUser(result.data);
        setStatus("authenticated");
      } else {
        setUser(null);
        setStatus("unauthenticated");
      }
    });

    return () => {
      isMounted = false;
    };
  }, []);

  const login = useCallback(async (email: string, password: string): Promise<AuthActionResult> => {
    const result = await loginUser(PUBLIC_API_URL, { email, password });
    if (!result.ok) {
      return { ok: false, error: result.error };
    }
    setUser(result.data);
    setStatus("authenticated");
    return { ok: true };
  }, []);

  const register = useCallback(
    async (username: string, email: string, password: string): Promise<AuthActionResult> => {
      const result = await registerUser(PUBLIC_API_URL, { username, email, password });
      if (!result.ok) {
        return { ok: false, error: result.error };
      }
      setUser(result.data);
      setStatus("authenticated");
      return { ok: true };
    },
    [],
  );

  const logout = useCallback(async () => {
    await logoutUser(PUBLIC_API_URL);
    setUser(null);
    setStatus("unauthenticated");
  }, []);

  return (
    <AuthContext.Provider value={{ status, user, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === null) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
