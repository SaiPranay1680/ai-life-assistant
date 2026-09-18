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
  updateProfile as updateProfileRequest,
} from "@/services/api/auth.service";
import type { User } from "@/types";

type AuthContextValue = {
  user: User | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  resetPassword: (email: string, newPassword: string, confirmPassword: string) => Promise<string>;
  updateProfile: (name: string) => Promise<void>;
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
      logout();
      if (!window.location.pathname.startsWith("/login")) {
        window.location.replace("/login");
      }
      return;
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

  const login = useCallback(async (email: string, password: string) => {
    const nextUser = await loginRequest(email, password);
    setUser(nextUser);
  }, []);

  const register = useCallback(async (email: string, password: string) => {
    const nextUser = await registerRequest(email, password);
    setUser(nextUser);
  }, []);

  const resetPassword = useCallback(
    async (email: string, newPassword: string, confirmPassword: string) => {
      return resetPasswordRequest(email, newPassword, confirmPassword);
    },
    [],
  );

  const updateProfile = useCallback(async (name: string) => {
    const nextUser = await updateProfileRequest(name);
    setUser(nextUser);
  }, []);

  const value = useMemo(
    () => ({ user, ready, login, register, resetPassword, updateProfile, logout }),
    [user, ready, login, register, resetPassword, updateProfile, logout],
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
