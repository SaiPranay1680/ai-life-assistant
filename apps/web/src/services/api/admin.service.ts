import axios from "axios";
import { apiClient } from "./client";

export type AdminUser = {
  id: string;
  email: string;
  name: string | null;
  role: "user" | "admin";
  is_active: boolean;
  email_verified: boolean;
  created_at?: string | null;
  updated_at?: string | null;
  last_login_at?: string | null;
  profile?: {
    first_name?: string | null;
    last_name?: string | null;
    display_name?: string | null;
    avatar_url?: string | null;
    locale?: string | null;
    timezone?: string | null;
  } | null;
  workspace?: {
    id: string;
    name: string;
  } | null;
};

export type AdminTable = {
  table_name: string;
  row_count: number;
  total_size: string | null;
};

export type AdminStats = {
  database_connected: boolean;
  total_users: number;
  active_users: number;
  admin_users: number;
  regular_users: number;
  total_documents: number;
  documents_by_type: Record<string, number>;
  documents_by_status: Record<string, number>;
  total_actions: number;
  actions_by_status: Record<string, number>;
  actions_by_priority: Record<string, number>;
  total_reminders: number;
  tables: AdminTable[];
};

function apiError(error: unknown, fallback: string): Error {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return new Error(detail);
    if (Array.isArray(detail)) {
      return new Error(detail.map((item) => item.msg ?? JSON.stringify(item)).join(" "));
    }
  }
  return error instanceof Error ? error : new Error(fallback);
}

export async function getAdminStats(): Promise<AdminStats> {
  try {
    const { data } = await apiClient.get<AdminStats>("/admin/stats");
    return data;
  } catch (error) {
    throw apiError(error, "Unable to load admin stats.");
  }
}

export async function getAdminUsers(): Promise<AdminUser[]> {
  try {
    const { data } = await apiClient.get<AdminUser[]>("/admin/users");
    return data;
  } catch (error) {
    throw apiError(error, "Unable to load user list.");
  }
}

export async function updateAdminUser(
  userId: string,
  changes: {
    name?: string | null;
    email?: string | null;
    role?: "user" | "admin" | null;
    is_active?: boolean | null;
    email_verified?: boolean | null;
    password?: string | null;
  },
): Promise<AdminUser> {
  try {
    const { data } = await apiClient.patch<AdminUser>(`/admin/users/${userId}`, changes);
    return data;
  } catch (error) {
    throw apiError(error, "Unable to update user.");
  }
}

export async function deleteAdminUser(userId: string): Promise<void> {
  try {
    await apiClient.delete(`/admin/users/${userId}`);
  } catch (error) {
    throw apiError(error, "Unable to delete user.");
  }
}
