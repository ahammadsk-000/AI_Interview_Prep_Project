"use client";

import { useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { TrendingDown, TrendingUp } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge, Skeleton } from "@/components/ui/misc";
import { cn, scoreColor } from "@/lib/utils";
import { PageHeader } from "@/components/page-header";
import { useHistory, useTrend } from "@/lib/hooks";

const METRICS = [
  { key: "readiness", label: "Readiness" },
  { key: "ats", label: "ATS score" },
  { key: "coding", label: "Coding" },
  { key: "communication", label: "Communication" },
  { key: "technical", label: "Technical" },
];

export default function AnalyticsPage() {
  const [metric, setMetric] = useState("readiness");
  const { data, isLoading } = useTrend(metric);

  const dir = data?.summary.direction;

  return (
    <>
      <PageHeader title="Analytics" description="Track your performance trends over time." />

      <div className="mb-4 flex flex-wrap gap-2">
        {METRICS.map((m) => (
          <button
            key={m.key}
            onClick={() => setMetric(m.key)}
            className={cn(
              "rounded-full px-3 py-1.5 text-sm font-medium transition-colors",
              metric === m.key
                ? "bg-primary text-primary-foreground"
                : "bg-secondary text-muted-foreground hover:text-foreground"
            )}
          >
            {m.label}
          </button>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-4">
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>{METRICS.find((m) => m.key === metric)?.label} over time</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-64 w-full" />
            ) : !data?.points.length ? (
              <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
                No data yet — complete activity to populate this trend.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={256}>
                <LineChart data={data.points} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="period" stroke="hsl(var(--muted-foreground))" fontSize={11} />
                  <YAxis domain={[0, 100]} stroke="hsl(var(--muted-foreground))" fontSize={11} />
                  <Tooltip
                    contentStyle={{
                      background: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke="hsl(var(--primary))"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Summary</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <SummaryRow label="Data points" value={data?.summary.count ?? 0} />
            <SummaryRow label="Average" value={data?.summary.average ?? "—"} />
            <SummaryRow label="Best" value={data?.summary.maximum ?? "—"} />
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Trend</span>
              <span
                className={cn(
                  "flex items-center gap-1 font-medium",
                  dir === "up" ? "text-success" : dir === "down" ? "text-destructive" : ""
                )}
              >
                {dir === "up" && <TrendingUp className="h-4 w-4" />}
                {dir === "down" && <TrendingDown className="h-4 w-4" />}
                {data ? `${data.summary.delta > 0 ? "+" : ""}${data.summary.delta}` : "—"}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="mt-4">
        <InterviewHistory />
      </div>
    </>
  );
}

function InterviewHistory() {
  const { data, isLoading } = useHistory("interview");
  return (
    <Card>
      <CardHeader>
        <CardTitle>Interview history</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {isLoading ? (
          <Skeleton className="h-16 w-full" />
        ) : !data?.length ? (
          <p className="text-sm text-muted-foreground">No interviews yet — start one in the Interview Room.</p>
        ) : (
          data.map((h, i) => (
            <div key={i} className="flex items-center justify-between rounded-md border border-border p-3 text-sm">
              <div className="flex items-center gap-3">
                <Badge variant={h.status === "completed" ? "success" : "muted"}>{h.status ?? "—"}</Badge>
                <span className="capitalize">{h.label}</span>
              </div>
              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                <span>{new Date(h.occurred_at).toLocaleDateString()}</span>
                {h.score != null && (
                  <span className={cn("font-medium", scoreColor(h.score))}>{Math.round(h.score)}/100</span>
                )}
              </div>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}

function SummaryRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
