"use client";

import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Building2, Loader2, Plus, UserPlus } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge, Label, Skeleton } from "@/components/ui/misc";
import { PageHeader } from "@/components/page-header";
import { api, apiErrorMessage } from "@/lib/api";
import { useOrgs } from "@/lib/hooks";
import type { MemberPublic, MentorDashboard, OrgPublic } from "@/lib/types";
import { cn, scoreColor } from "@/lib/utils";

const MANAGER_ROLES = ["owner", "admin", "mentor"];

export default function TeamsPage() {
  const { data: orgs, isLoading } = useOrgs();
  const qc = useQueryClient();
  const [selected, setSelected] = useState<OrgPublic | null>(null);

  useEffect(() => {
    if (orgs?.length && !selected) setSelected(orgs[0]);
  }, [orgs, selected]);

  return (
    <>
      <PageHeader title="Teams" description="Organizations, members, and the mentor readiness dashboard." />
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4">
          <CreateOrg onCreated={(o) => { qc.invalidateQueries({ queryKey: ["orgs"] }); setSelected(o); }} />
          <Card>
            <CardHeader>
              <CardTitle>Your organizations</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {isLoading ? (
                <Skeleton className="h-10 w-full" />
              ) : !orgs?.length ? (
                <p className="text-sm text-muted-foreground">No organizations yet.</p>
              ) : (
                orgs.map((o) => (
                  <button
                    key={o.id}
                    onClick={() => setSelected(o)}
                    className={cn(
                      "flex w-full items-center justify-between rounded-md border p-3 text-left transition-colors",
                      selected?.id === o.id ? "border-primary/50 bg-primary/5" : "border-border hover:bg-secondary"
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <Building2 className="h-4 w-4 text-muted-foreground" />
                      <div>
                        <div className="text-sm font-medium">{o.name}</div>
                        <div className="text-xs text-muted-foreground">{o.member_count} members</div>
                      </div>
                    </div>
                    <Badge variant="muted">{o.your_role}</Badge>
                  </button>
                ))
              )}
            </CardContent>
          </Card>
        </div>

        <div className="lg:col-span-2">
          {selected ? <OrgDetail org={selected} /> : (
            <Card>
              <CardContent className="p-10 text-center text-sm text-muted-foreground">
                Create or select an organization to manage members and view the mentor dashboard.
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </>
  );
}

function CreateOrg({ onCreated }: { onCreated: (o: OrgPublic) => void }) {
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function create() {
    setBusy(true);
    setError(null);
    try {
      const { data } = await api.post<OrgPublic>("/orgs", { name, slug });
      setName("");
      setSlug("");
      onCreated(data);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>New organization</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-2">
          <Label htmlFor="name">Name</Label>
          <Input id="name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Acme Inc" />
        </div>
        <div className="space-y-2">
          <Label htmlFor="slug">Slug</Label>
          <Input
            id="slug"
            value={slug}
            onChange={(e) => setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, "-"))}
            placeholder="acme"
          />
        </div>
        {error && <p className="text-sm text-destructive">{error}</p>}
        <Button onClick={create} disabled={busy || !name || !slug} className="w-full">
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
          Create
        </Button>
      </CardContent>
    </Card>
  );
}

function OrgDetail({ org }: { org: OrgPublic }) {
  const [members, setMembers] = useState<MemberPublic[]>([]);
  const [dashboard, setDashboard] = useState<MentorDashboard | null>(null);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("member");
  const [error, setError] = useState<string | null>(null);
  const canManage = MANAGER_ROLES.includes(org.your_role);

  async function load() {
    setError(null);
    try {
      const m = await api.get<MemberPublic[]>(`/orgs/${org.id}/members`);
      setMembers(m.data);
      if (canManage) {
        const d = await api.get<MentorDashboard>(`/orgs/${org.id}/dashboard`);
        setDashboard(d.data);
      }
    } catch (e) {
      setError(apiErrorMessage(e));
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [org.id]);

  async function addMember() {
    setError(null);
    try {
      await api.post(`/orgs/${org.id}/members`, { email, role });
      setEmail("");
      await load();
    } catch (e) {
      setError(apiErrorMessage(e));
    }
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>{org.name}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {["owner", "admin"].includes(org.your_role) && (
            <div className="flex flex-wrap items-end gap-2">
              <div className="flex-1 space-y-1">
                <Label htmlFor="email">Add member by email</Label>
                <Input id="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="teammate@example.com" />
              </div>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="h-10 rounded-md border border-input bg-background px-2 text-sm"
              >
                {["member", "mentor", "admin"].map((r) => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
              <Button onClick={addMember} disabled={!email}>
                <UserPlus className="h-4 w-4" /> Add
              </Button>
            </div>
          )}
          {error && <p className="text-sm text-destructive">{error}</p>}
          <div className="space-y-1">
            {members.map((m) => (
              <div key={m.user_id} className="flex items-center justify-between rounded-md border border-border p-2.5 text-sm">
                <span>{m.full_name || m.email}</span>
                <Badge variant="muted">{m.role}</Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {dashboard && (
        <Card>
          <CardHeader>
            <CardTitle>Mentor dashboard</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="text-sm text-muted-foreground">
              Team average readiness:{" "}
              <span className={cn("font-semibold", scoreColor(dashboard.average_readiness ?? undefined))}>
                {dashboard.average_readiness ?? "—"}
              </span>
            </div>
            {dashboard.members.map((m) => (
              <div key={m.user_id} className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">{m.email}</span>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-muted-foreground">
                    {m.interviews} interviews · {m.coding_submissions} subs
                  </span>
                  <span className={cn("font-medium", scoreColor(m.overall_readiness ?? undefined))}>
                    {m.overall_readiness ?? "—"}
                  </span>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
