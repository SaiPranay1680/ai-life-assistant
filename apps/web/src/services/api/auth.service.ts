import axios from "axios";
import type { User } from "@/types";
import { apiClient } from "./client";

const AUTH_KEY = "ala-auth-user";
const TOKEN_KEY = "ala-token";
const WORKSPACE_KEY = "ala-workspace-id";

type Workspace = {
  id: string;
  name: string;
};

type AuthUser = User & { workspace: Workspace };

type AuthResponse = {
  access_token: string;
  token_type: string;
  user: AuthUser;
};

type ResetPasswordResponse = {
  message: string;
};

function apiError(error: unknown, fallback = "Unable to sign in."): Error {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return new Error(detail);
    if (Array.isArray(detail)) {
      return new Error(detail.map((item) => item.msg ?? JSON.stringify(item)).join(" "));
    }
  }
  return error instanceof Error ? error : new Error(fallback);
}

function persistSession(response: AuthResponse): User {
  const user: User = {
    id: response.user.id,
    name: response.user.name,
    email: response.user.email,
  };
  window.localStorage.setItem(AUTH_KEY, JSON.stringify(user));
  window.localStorage.setItem(TOKEN_KEY, response.access_token);
  window.localStorage.setItem(WORKSPACE_KEY, response.user.workspace.id);
  return user;
}

function decodeTokenPayload(token: string): { exp?: number } | null {
  try {
    const parts = token.split(".");
    if (parts.length < 2) return null;
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
    return JSON.parse(window.atob(padded)) as { exp?: number };
  } catch {
    return null;
  }
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function isSessionExpired(token?: string | null): boolean {
  const value = token === undefined ? getAccessToken() : token;
  if (!value) return true;
  const payload = decodeTokenPayload(value);
  if (!payload?.exp) return true;
  return payload.exp * 1000 <= Date.now();
}

export function getSessionExpiresAtMs(): number | null {
  const token = getAccessToken();
  if (!token) return null;
  const payload = decodeTokenPayload(token);
  if (!payload?.exp) return null;
  return payload.exp * 1000;
}

export async function login(email: string, password: string): Promise<User> {
  try {
    const { data } = await apiClient.post<AuthResponse>("/auth/login", { email, password });
    return persistSession(data);
  } catch (error) {
    throw apiError(error);
  }
}

export async function register(email: string, password: string, name?: string): Promise<User> {
  try {
    const { data } = await apiClient.post<AuthResponse>("/auth/register", {
      email,
      password,
      name,
    });
    return persistSession(data);
  } catch (error) {
    throw apiError(error);
  }
}

export async function resetPassword(
  email: string,
  newPassword: string,
  confirmPassword: string,
): Promise<string> {
  try {
    const { data } = await apiClient.post<ResetPasswordResponse>("/auth/reset-password", {
      email,
      new_password: newPassword,
      confirm_password: confirmPassword,
    });
    return data.message;
  } catch (error) {
    throw apiError(error, "Unable to reset password.");
  }
}

export function logout() {
  window.localStorage.removeItem(AUTH_KEY);
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(WORKSPACE_KEY);
}

export function getStoredUser(): User | null {
  if (typeof window === "undefined") return null;
  if (isSessionExpired()) {
    logout();
    return null;
  }
  const raw = window.localStorage.getItem(AUTH_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as User;
  } catch {
    return null;
  }
}
