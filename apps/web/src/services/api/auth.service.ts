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

function apiError(error: unknown): Error {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return new Error(detail);
    if (Array.isArray(detail)) {
      return new Error(detail.map((item) => item.msg ?? JSON.stringify(item)).join(" "));
    }
  }
  return error instanceof Error ? error : new Error("Unable to sign in.");
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

export function logout() {
  window.localStorage.removeItem(AUTH_KEY);
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(WORKSPACE_KEY);
}

export function getStoredUser(): User | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(AUTH_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as User;
  } catch {
    return null;
  }
}
