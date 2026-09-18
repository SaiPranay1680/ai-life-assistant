"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  getSessionExpiresAtMs,
  getStoredUser,
  isSessionExpired,
  login as loginRequest,
  logout as logoutRequest,
  register as registerRequest,
  resetPassword as resetPasswordRequest,
} from "@/services/api/auth.service";
import type { User } from "@/types";

type AuthContextValue = {
  user: User | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (email: string, password: string, name?: string) => Promise<User>;
  resetPassword: (email: string, newPassword: string, confirmPassword: string) => Promise<string>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  const logout = useCallback(() => {
    logoutRequest();
    setUser(null);
  }, []);

  useEffect(() => {
    const stored = getStoredUser();
    const id = window.setTimeout(() => {
      setUser(stored);
      setReady(true);
    }, 0);
    return () => window.clearTimeout(id);
  }, []);

  useEffect(() => {
    if (!user) return;

    const expireAt = getSessionExpiresAtMs();
    if (expireAt === null || isSessionExpired()) {
      const id = window.setTimeout(() => {
        logout();
        if (!window.location.pathname.startsWith("/login")) {
          window.location.replace("/login");
        }
      }, 0);
      return () => window.clearTimeout(id);
    }

    const delay = Math.max(expireAt - Date.now(), 0);
    const timer = window.setTimeout(() => {
      logout();
      if (!window.location.pathname.startsWith("/login")) {
        window.location.replace("/login");
      }
    }, delay);

    return () => window.clearTimeout(timer);
  }, [user, logout]);

  const login = useCallback(async (email: string, password: string): Promise<User> => {
    const nextUser = await loginRequest(email, password);
    setUser(nextUser);
    return nextUser;
  }, []);

  const register = useCallback(async (email: string, password: string, name?: string): Promise<User> => {
    const nextUser = await registerRequest(email, password, name);
    setUser(nextUser);
    return nextUser;
  }, []);

  const resetPassword = useCallback(
    async (email: string, newPassword: string, confirmPassword: string) => {
      return resetPasswordRequest(email, newPassword, confirmPassword);
    },
    [],
  );

  const value = useMemo(
    () => ({ user, ready, login, register, resetPassword, logout }),
    [user, ready, login, register, resetPassword, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
