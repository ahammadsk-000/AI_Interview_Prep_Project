"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/auth-store";

export default function Home() {
  const router = useRouter();
  const accessToken = useAuthStore((s) => s.accessToken);
  const hydrated = useAuthStore((s) => s.hydrated);

  useEffect(() => {
    if (!hydrated) return;
    router.replace(accessToken ? "/dashboard" : "/login");
  }, [accessToken, hydrated, router]);

  return (
    <div className="flex min-h-screen items-center justify-center text-muted-foreground">
      Loading PrepForge…
    </div>
  );
}
