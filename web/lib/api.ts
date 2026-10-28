import axios from "axios";

/**
 * Base URL for GDSS Local API (`gdss serve`).
 * Defaults to http://127.0.0.1:8787 per frontend roadmap contract.
 */
export const GDSS_API_BASE_URL =
  process.env.NEXT_PUBLIC_GDSS_API || "http://127.0.0.1:8787";

export const api = axios.create({
  baseURL: GDSS_API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 60000,
});

/** Generic API fetcher for TanStack Query keys */
export async function fetcher<T>(url: string): Promise<T> {
  const response = await api.get<T>(url);
  return response.data;
}
