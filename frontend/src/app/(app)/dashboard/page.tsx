"use client";

import {
  Activity,
  Bot,
  Code2,
  FileText,
  Gauge,
  MessageSquare,
  type LucideIcon,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress, Skeleton } from "@/components/ui/misc";
import { PageHeader } from "@/components/page-header";
import { useOverview } from "@/lib/hooks";
import { cn, scoreColor } from "@/lib/utils";

const DIMENSION_LABELS: Record<string, string> = {
  technical: "Technical",
  communication: "Communication",
  completeness: "Completeness",
  confidence: "Confidence",
};

export default function DashboardPage() {
  const { data, isLoading, isError } = useOverview();

  return (
    <>
      <PageHeader title="Dashboard" description="Your interview-readiness at a glance." />

      {isError && (
        <Card>
          <CardContent className="p-6 text-sm text-muted-foreground">
            Could not load your dashboard. Make sure the backend is running.
          </CardContent>
        </Card>
      )}

      {/* Readiness hero + stat grid */}
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Gauge className="h-4 w-4 text-primary" /> Overall readiness
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-16 w-32" />
            ) : (
              <>
                <div className={cn("text-5xl font-bold", scoreColor(data?.overall_readiness))}>
                  {data?.overall_readiness ?? "—"}
                  <span className="text-xl text-muted-foreground">/100</span>
                </div>
                <Progress className="mt-4" value={data?.overall_readiness ?? 0} />
                <p className="mt-2 text-xs text-muted-foreground">
                  Composite of resume, coding, behavioral, and interview signals.
                </p>
              </>
            )}
          </CardContent>
        </Card>

        <div className="grid grid-cols-2 gap-4 lg:col-span-2">
          <Stat icon={Bot} label="Interviews" value={data?.interviews.total} loading={isLoading} />
          <Stat icon={MessageSquare} label="Answers graded" value={data?.totals.answers_graded} loading={isLoading} />
          <Stat icon={Code2} label="Coding submissions" value={data?.coding.submissions} loading={isLoading} />
          <Stat icon={FileText} label="Resumes analyzed" value={data?.totals.resumes} loading={isLoading} />
        </div>
      </div>

      {/* Dimension breakdown + module stats */}
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-primary" /> Answer-quality breakdown
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {isLoading ? (
              <Skeleton className="h-24 w-full" />
            ) : Object.keys(data?.dimension_averages ?? {}).length === 0 ? (
              <p className="text-sm text-muted-foreground">
                Grade some interview answers to see your communication and technical breakdown.
              </p>
            ) : (
              Object.entries(data!.dimension_averages).map(([dim, score]) => (
                <div key={dim} className="space-y-1.5">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">{DIMENSION_LABELS[dim] ?? dim}</span>
                    <span className={cn("font-medium", scoreColor(score))}>{score}</span>
                  </div>
                  <Progress value={score} />
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Module snapshot</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <Row label="ATS — latest score" value={data?.ats.latest_score ?? "—"} loading={isLoading} />
            <Row label="ATS — best score" value={data?.ats.best_score ?? "—"} loading={isLoading} />
            <Row
              label="Coding acceptance rate"
              value={data ? `${Math.round((data.coding.acceptance_rate ?? 0) * 100)}%` : "—"}
              loading={isLoading}
            />
            <Row label="Coding best readiness" value={data?.coding.best_readiness ?? "—"} loading={isLoading} />
            <Row label="Interviews completed" value={data?.interviews.completed ?? "—"} loading={isLoading} />
          </CardContent>
        </Card>
      </div>
    </>
  );
}

function Stat({
  icon: Icon,
  label,
  value,
  loading,
}: {
  icon: LucideIcon;
  label: string;
  value: number | undefined;
  loading: boolean;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-5">
        <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary/10 text-primary">
          <Icon className="h-5 w-5" />
        </div>
        <div>
          {loading ? (
            <Skeleton className="h-7 w-10" />
          ) : (
            <div className="text-2xl font-semibold">{value ?? 0}</div>
          )}
          <div className="text-xs text-muted-foreground">{label}</div>
        </div>
      </CardContent>
    </Card>
  );
}

function Row({ label, value, loading }: { label: string; value: React.ReactNode; loading: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-muted-foreground">{label}</span>
      {loading ? <Skeleton className="h-4 w-10" /> : <span className="font-medium">{value}</span>}
    </div>
  );
}
