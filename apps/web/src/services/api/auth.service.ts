import dashboard from "@/data/dashboard.json";
import type { User } from "@/types";
import { isValidEmail, wait } from "@/utils";

const AUTH_KEY = "ala-auth-user";
const TOKEN_KEY = "ala-token";

export async function login(email: string, password: string): Promise<User> {
  await wait(700);
  if (!isValidEmail(email)) {
    throw new Error("Enter a valid email address.");
  }
  if (password.trim().length < 6) {
    throw new Error("Password must be at least 6 characters.");
  }

  const user: User = {
    ...dashboard.user,
    email: email.trim(),
  };
  window.localStorage.setItem(AUTH_KEY, JSON.stringify(user));
  window.localStorage.setItem(TOKEN_KEY, "mock-session-token");
  return user;
}

export function logout() {
  window.localStorage.removeItem(AUTH_KEY);
  window.localStorage.removeItem(TOKEN_KEY);
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
