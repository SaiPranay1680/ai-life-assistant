import axios from "axios";

export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
  timeout: 15000,
});

apiClient.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = window.localStorage.getItem("ala-token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (typeof window !== "undefined" && axios.isAxiosError(error) && error.response?.status === 401) {
      const url = String(error.config?.url ?? "");
      const isAuthForm =
        url.includes("/auth/login") ||
        url.includes("/auth/register") ||
        url.includes("/auth/forgot-password") ||
        url.includes("/auth/verify-reset-otp") ||
        url.includes("/auth/reset-password");
      if (!isAuthForm) {
        window.localStorage.removeItem("ala-auth-user");
        window.localStorage.removeItem("ala-token");
        window.localStorage.removeItem("ala-workspace-id");
        if (!window.location.pathname.startsWith("/login")) {
          window.location.replace("/login");
        }
      }
    }
    return Promise.reject(error);
  },
);
