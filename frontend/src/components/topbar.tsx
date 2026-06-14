"use client";

import { LogOut } from "lucide-react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { authTokens, useAuthStore } from "@/lib/auth-store";
import { initials } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/misc";
import { ThemeToggle } from "./theme-toggle";

export function Topbar() {
  const user = useAuthStore((s) => s.user);
  const clear = useAuthStore((s) => s.clear);
  const router = useRouter();

  async function logout() {
    try {
      if (authTokens.refresh) await api.post("/auth/logout", { refresh_token: authTokens.refresh });
    } catch {
      /* best-effort */
    }
    clear();
    router.replace("/login");
  }

  return (
    <header className="flex h-14 items-center justify-between border-b border-border px-5">
      <div className="text-sm text-muted-foreground">
        {user?.target_role ? `Preparing for ${user.target_role}` : "Welcome to PrepForge"}
      </div>
      <div className="flex items-center gap-3">
        {user?.plan && <Badge variant="muted">{user.plan} plan</Badge>}
        <ThemeToggle />
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/15 text-xs font-semibold text-primary">
            {initials(user?.full_name, user?.email)}
          </div>
          <Button variant="ghost" size="icon" onClick={logout} aria-label="Log out">
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </header>
  );
}
