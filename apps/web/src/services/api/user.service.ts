import { apiClient } from "./client";

export type UserItem = {
  id: string;
  email: string;
  name: string | null;
  role: string;
  is_active: boolean;
  email_verified: boolean;
  created_at?: string | null;
  updated_at?: string | null;
  last_login_at?: string | null;
  profile?: any;
  workspace?: { id: string; name: string } | null;
};

export async function getUsers(): Promise<UserItem[]> {
  const { data } = await apiClient.get<UserItem[]>('/users');
  return data;
}
