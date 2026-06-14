"use client";

import Link from "next/link";
import { useState } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/misc";
import { useRegister } from "@/lib/hooks";
import { apiErrorMessage } from "@/lib/api";

export default function RegisterPage() {
  const register = useRegister();
  const [form, setForm] = useState({ email: "", password: "", full_name: "", target_role: "" });
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  return (
    <form
      className="space-y-5"
      onSubmit={(e) => {
        e.preventDefault();
        register.mutate(form);
      }}
    >
      <div className="space-y-1">
        <h2 className="text-2xl font-semibold">Create your account</h2>
        <p className="text-sm text-muted-foreground">Start preparing in minutes.</p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="full_name">Full name</Label>
        <Input id="full_name" value={form.full_name} onChange={set("full_name")} placeholder="Ada Lovelace" />
      </div>
      <div className="space-y-2">
        <Label htmlFor="target_role">Target role</Label>
        <Input id="target_role" value={form.target_role} onChange={set("target_role")}
          placeholder="GenAI Engineer" />
      </div>
      <div className="space-y-2">
        <Label htmlFor="email">Email</Label>
        <Input id="email" type="email" required value={form.email} onChange={set("email")}
          placeholder="you@example.com" />
      </div>
      <div className="space-y-2">
        <Label htmlFor="password">Password</Label>
        <Input id="password" type="password" required minLength={8} value={form.password}
          onChange={set("password")} placeholder="At least 8 characters" />
      </div>

      {register.isError && (
        <p className="text-sm text-destructive">{apiErrorMessage(register.error)}</p>
      )}

      <Button type="submit" className="w-full" disabled={register.isPending}>
        {register.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
        Create account
      </Button>

      <p className="text-center text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link href="/login" className="font-medium text-primary hover:underline">
          Sign in
        </Link>
      </p>
    </form>
  );
}
