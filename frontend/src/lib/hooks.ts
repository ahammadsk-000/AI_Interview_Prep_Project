"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { api } from "./api";
import { useAuthStore } from "./auth-store";
import type {
  AuthResponse,
  ChallengeSummary,
  DashboardOverview,
  HistoryItem,
  OrgPublic,
  ResumePublic,
  TrendResponse,
  UserPublic,
} from "./types";

// ── Auth ────────────────────────────────────────────────────────────
export function useLogin() {
  const setAuth = useAuthStore((s) => s.setAuth);
  const router = useRouter();
  return useMutation({
    mutationFn: async (body: { email: string; password: string }) => {
      const { data } = await api.post<AuthResponse>("/auth/login", body);
      return data;
    },
    onSuccess: (data) => {
      setAuth(data.user, data.tokens);
      router.push("/dashboard");
    },
  });
}

export function useRegister() {
  const setAuth = useAuthStore((s) => s.setAuth);
  const router = useRouter();
  return useMutation({
    mutationFn: async (body: {
      email: string;
      password: string;
      full_name?: string;
      target_role?: string;
    }) => {
      const { data } = await api.post<AuthResponse>("/auth/register", body);
      return data;
    },
    onSuccess: (data) => {
      setAuth(data.user, data.tokens);
      router.push("/dashboard");
    },
  });
}

export function useMe() {
  const setUser = useAuthStore((s) => s.setUser);
  return useQuery({
    queryKey: ["me"],
    queryFn: async () => {
      const { data } = await api.get<UserPublic>("/users/me");
      setUser(data);
      return data;
    },
  });
}

export function useUpdateProfile() {
  const qc = useQueryClient();
  const setUser = useAuthStore((s) => s.setUser);
  return useMutation({
    mutationFn: async (body: Partial<Pick<UserPublic, "full_name" | "target_role" | "experience_level">>) => {
      const { data } = await api.patch<UserPublic>("/users/me", body);
      return data;
    },
    onSuccess: (data) => {
      setUser(data);
      qc.invalidateQueries({ queryKey: ["me"] });
    },
  });
}

// ── Analytics ───────────────────────────────────────────────────────
export function useOverview() {
  return useQuery({
    queryKey: ["analytics", "overview"],
    queryFn: async () => {
      const { data } = await api.get<DashboardOverview>("/analytics/overview");
      return data;
    },
  });
}

export function useTrend(metric: string, bucket = "day") {
  return useQuery({
    queryKey: ["analytics", "trend", metric, bucket],
    queryFn: async () => {
      const { data } = await api.get<TrendResponse>(`/analytics/trends?metric=${metric}&bucket=${bucket}`);
      return data;
    },
  });
}

// ── Resume / Coding (used by their pages) ───────────────────────────
export function useResumes() {
  return useQuery({
    queryKey: ["resumes"],
    queryFn: async () => {
      const { data } = await api.get<ResumePublic[]>("/resumes");
      return data;
    },
  });
}

export function useChallenges() {
  return useQuery({
    queryKey: ["challenges"],
    queryFn: async () => {
      const { data } = await api.get<ChallengeSummary[]>("/coding/challenges");
      return data;
    },
  });
}

export function useOrgs() {
  return useQuery({
    queryKey: ["orgs"],
    queryFn: async () => {
      const { data } = await api.get<OrgPublic[]>("/orgs");
      return data;
    },
  });
}

export function useHistory(kind: string) {
  return useQuery({
    queryKey: ["history", kind],
    queryFn: async () => {
      const { data } = await api.get<HistoryItem[]>(`/analytics/history?kind=${kind}`);
      return data;
    },
  });
}
