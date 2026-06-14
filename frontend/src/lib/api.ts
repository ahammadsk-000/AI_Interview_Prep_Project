import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import { authTokens, useAuthStore } from "./auth-store";
import type { ApiError, TokenPair } from "./types";

// All requests go to /api/v1 — proxied to the backend by next.config.mjs rewrites.
export const api = axios.create({
  baseURL: "/api/v1",
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = authTokens.access;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshing: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refresh = authTokens.refresh;
  if (!refresh) return null;
  try {
    const { data } = await axios.post<TokenPair>("/api/v1/auth/refresh", {
      refresh_token: refresh,
    });
    useAuthStore.getState().setTokens(data);
    return data.access_token;
  } catch {
    useAuthStore.getState().clear();
    return null;
  }
}

api.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retried?: boolean };
    if (error.response?.status === 401 && original && !original._retried && authTokens.refresh) {
      original._retried = true;
      refreshing = refreshing ?? refreshAccessToken();
      const newToken = await refreshing;
      refreshing = null;
      if (newToken) {
        original.headers.Authorization = `Bearer ${newToken}`;
        return api(original);
      }
    }
    return Promise.reject(error);
  }
);

/** Extracts a human-readable message from an Axios error response. */
export function apiErrorMessage(err: unknown, fallback = "Something went wrong."): string {
  const axiosErr = err as AxiosError<ApiError>;
  return axiosErr?.response?.data?.error?.message ?? fallback;
}
