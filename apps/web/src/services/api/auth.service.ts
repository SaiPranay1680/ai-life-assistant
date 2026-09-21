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

type AuthUser = User & { workspace: Workspace; email_verified?: boolean };

type AuthResponse = {
  access_token: string;
  token_type: string;
  user: AuthUser;
};

type MessageResponse = {
  message: string;
  expires_in_seconds?: number | null;
  cooldown_seconds?: number | null;
};

type VerifyResetOtpResponse = {
  message: string;
  reset_token: string;
};

type ResetPasswordResponse = {
  message: string;
};

type MeResponse = AuthUser;

function toUser(user: AuthUser): User {
  return {
    id: user.id,
    name: user.name,
    email: user.email,
    role: user.role === "admin" ? "admin" : "user",
    emailVerified: Boolean(user.email_verified),
  };
}

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
  const user = toUser(response.user);
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
      username: name,
    });
    return persistSession(data);
  } catch (error) {
    throw apiError(error);
  }
}

export async function requestPasswordReset(email: string): Promise<MessageResponse> {
  try {
    const { data } = await apiClient.post<MessageResponse>("/auth/forgot-password", { email });
    return data;
  } catch (error) {
    throw apiError(error, "Unable to send a password reset code.");
  }
}

export async function verifyResetOtp(email: string, otp: string): Promise<VerifyResetOtpResponse> {
  try {
    const { data } = await apiClient.post<VerifyResetOtpResponse>("/auth/verify-reset-otp", { email, otp });
    return data;
  } catch (error) {
    throw apiError(error, "Unable to verify that code.");
  }
}

export async function resetPassword(resetToken: string, newPassword: string, confirmPassword: string): Promise<string> {
  try {
    const { data } = await apiClient.post<ResetPasswordResponse>("/auth/reset-password", {
      reset_token: resetToken,
      new_password: newPassword,
      confirm_password: confirmPassword,
    });
    return data.message;
  } catch (error) {
    throw apiError(error, "Unable to reset password.");
  }
}

export async function sendVerificationOtp(): Promise<MessageResponse> {
  try {
    const { data } = await apiClient.post<MessageResponse>("/auth/send-verification-otp");
    return data;
  } catch (error) {
    throw apiError(error, "Unable to send a verification code.");
  }
}

export async function verifyAccount(email: string, otp: string): Promise<MessageResponse> {
  try {
    const { data } = await apiClient.post<MessageResponse>("/auth/verify-account", { email, otp });
    return data;
  } catch (error) {
    throw apiError(error, "Unable to verify that code.");
  }
}

export async function getMe(): Promise<User> {
  try {
    const { data } = await apiClient.get<MeResponse>("/me");
    const user = toUser(data);
    window.localStorage.setItem(AUTH_KEY, JSON.stringify(user));
    return user;
  } catch (error) {
    throw apiError(error, "Unable to load your account.");
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
    const parsed = JSON.parse(raw) as User;
    return {
      ...parsed,
      role: parsed.role === "admin" ? "admin" : "user",
    };
  } catch {
    return null;
  }
}
