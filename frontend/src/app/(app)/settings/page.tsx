"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge, Label } from "@/components/ui/misc";
import { PageHeader } from "@/components/page-header";
import { useMe, useUpdateProfile } from "@/lib/hooks";

const LEVELS = ["fresher", "junior", "mid", "senior", "staff"];

export default function SettingsPage() {
  const { data: me } = useMe();
  const update = useUpdateProfile();
  const [fullName, setFullName] = useState("");
  const [targetRole, setTargetRole] = useState("");
  const [level, setLevel] = useState("");

  useEffect(() => {
    if (me) {
      setFullName(me.full_name ?? "");
      setTargetRole(me.target_role ?? "");
      setLevel(me.experience_level ?? "");
    }
  }, [me]);

  return (
    <>
      <PageHeader title="Settings" description="Manage your profile and preferences." />
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Profile</CardTitle>
          </CardHeader>
          <CardContent>
            <form
              className="space-y-4"
              onSubmit={(e) => {
                e.preventDefault();
                update.mutate({
                  full_name: fullName,
                  target_role: targetRole,
                  experience_level: level || undefined,
                });
              }}
            >
              <div className="space-y-2">
                <Label htmlFor="full_name">Full name</Label>
                <Input id="full_name" value={fullName} onChange={(e) => setFullName(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="target_role">Target role</Label>
                <Input id="target_role" value={targetRole} onChange={(e) => setTargetRole(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="level">Experience level</Label>
                <select
                  id="level"
                  value={level}
                  onChange={(e) => setLevel(e.target.value)}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <option value="">Not set</option>
                  {LEVELS.map((l) => (
                    <option key={l} value={l}>
                      {l}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex items-center gap-3">
                <Button type="submit" disabled={update.isPending}>
                  {update.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                  Save changes
                </Button>
                {update.isSuccess && <span className="text-sm text-success">Saved.</span>}
              </div>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Account</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Email</span>
              <span className="font-medium">{me?.email}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Plan</span>
              <Badge variant="muted">{me?.plan ?? "—"}</Badge>
            </div>
            <div className="flex flex-wrap justify-between gap-2">
              <span className="text-muted-foreground">Roles</span>
              <div className="flex flex-wrap gap-1">
                {me?.roles.map((r) => (
                  <Badge key={r}>{r}</Badge>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
