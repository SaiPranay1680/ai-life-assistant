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
  getStoredUser,
  login as loginRequest,
  logout as logoutRequest,
  register as registerRequest,
} from "@/services/api/auth.service";
import type { User } from "@/types";

type AuthContextValue = {
  user: User | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const stored = getStoredUser();
    const id = window.setTimeout(() => {
      setUser(stored);
      setReady(true);
    }, 0);
    return () => window.clearTimeout(id);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const nextUser = await loginRequest(email, password);
    setUser(nextUser);
  }, []);

  const register = useCallback(async (email: string, password: string) => {
    const nextUser = await registerRequest(email, password);
    setUser(nextUser);
  }, []);

  const logout = useCallback(() => {
    logoutRequest();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, ready, login, register, logout }),
    [user, ready, login, register, logout],
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
