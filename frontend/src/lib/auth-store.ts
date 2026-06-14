import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { TokenPair, UserPublic } from "./types";

interface AuthState {
  user: UserPublic | null;
  accessToken: string | null;
  refreshToken: string | null;
  hydrated: boolean;
  setAuth: (user: UserPublic, tokens: TokenPair) => void;
  setTokens: (tokens: TokenPair) => void;
  setUser: (user: UserPublic) => void;
  clear: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      hydrated: false,
      setAuth: (user, tokens) =>
        set({ user, accessToken: tokens.access_token, refreshToken: tokens.refresh_token }),
      setTokens: (tokens) =>
        set({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token }),
      setUser: (user) => set({ user }),
      clear: () => set({ user: null, accessToken: null, refreshToken: null }),
    }),
    {
      name: "prepforge-auth",
      onRehydrateStorage: () => (state) => {
        if (state) state.hydrated = true;
      },
    }
  )
);

// Non-hook accessors for the axios interceptors.
export const authTokens = {
  get access() {
    return useAuthStore.getState().accessToken;
  },
  get refresh() {
    return useAuthStore.getState().refreshToken;
  },
};
