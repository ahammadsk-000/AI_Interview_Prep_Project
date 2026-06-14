"use client";

import Link from "next/link";
import { useState } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/misc";
import { useLogin } from "@/lib/hooks";
import { apiErrorMessage } from "@/lib/api";

export default function LoginPage() {
  const login = useLogin();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  return (
    <form
      className="space-y-5"
      onSubmit={(e) => {
        e.preventDefault();
        login.mutate({ email, password });
      }}
    >
      <div className="space-y-1">
        <h2 className="text-2xl font-semibold">Welcome back</h2>
        <p className="text-sm text-muted-foreground">Sign in to continue your prep.</p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="email">Email</Label>
        <Input id="email" type="email" autoComplete="email" required value={email}
          onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
      </div>
      <div className="space-y-2">
        <Label htmlFor="password">Password</Label>
        <Input id="password" type="password" autoComplete="current-password" required
          value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
      </div>

      {login.isError && (
        <p className="text-sm text-destructive">{apiErrorMessage(login.error, "Invalid credentials.")}</p>
      )}

      <Button type="submit" className="w-full" disabled={login.isPending}>
        {login.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
        Sign in
      </Button>

      <p className="text-center text-sm text-muted-foreground">
        New here?{" "}
        <Link href="/register" className="font-medium text-primary hover:underline">
          Create an account
        </Link>
      </p>
    </form>
  );
}
