import axios from "axios";
import { apiClient } from "./client";

export async function downloadWorkspaceExport(): Promise<void> {
  try {
    const response = await apiClient.get("/privacy/export", { responseType: "blob" });
    const url = window.URL.createObjectURL(new Blob([response.data], { type: "application/json" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "ai-life-assistant-export.json";
    link.click();
    window.URL.revokeObjectURL(url);
  } catch (error) {
    const detail = axios.isAxiosError(error) ? error.response?.data?.detail : undefined;
    throw new Error(typeof detail === "string" ? detail : "Unable to export your workspace data.");
  }
}
