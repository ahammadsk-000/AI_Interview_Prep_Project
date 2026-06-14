"use client";

import { useEffect, useState } from "react";
import { Loader2, Sparkles, Wand2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge, Label, Progress, Skeleton } from "@/components/ui/misc";
import { PageHeader } from "@/components/page-header";
import { api, apiErrorMessage } from "@/lib/api";
import { useResumes } from "@/lib/hooks";
import type { AtsReport, OptimizeResponse } from "@/lib/types";
import { cn, scoreColor } from "@/lib/utils";

export default function AtsPage() {
  const { data: resumes, isLoading } = useResumes();
  const [resumeId, setResumeId] = useState("");
  const [jd, setJd] = useState("");
  const [report, setReport] = useState<AtsReport | null>(null);
  const [optimized, setOptimized] = useState<OptimizeResponse | null>(null);
  const [busy, setBusy] = useState<"analyze" | "optimize" | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (resumes?.length && !resumeId) setResumeId(resumes[0].id);
  }, [resumes, resumeId]);

  async function analyze() {
    if (!resumeId) return;
    setBusy("analyze");
    setError(null);
    setOptimized(null);
    try {
      const { data } = await api.post<AtsReport>(`/resumes/${resumeId}/analyze`, { jd_text: jd });
      setReport(data);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setBusy(null);
    }
  }

  async function optimize() {
    if (!resumeId) return;
    setBusy("optimize");
    setError(null);
    try {
      const { data } = await api.post<OptimizeResponse>("/ats/optimize", {
        resume_id: resumeId,
        jd_text: jd,
      });
      setOptimized(data);
      setReport(data.report);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <PageHeader title="ATS Optimizer" description="Match your résumé to a job description and close keyword gaps." />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Job description</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="resume">Résumé</Label>
              {isLoading ? (
                <Skeleton className="h-10 w-full" />
              ) : !resumes?.length ? (
                <p className="text-sm text-muted-foreground">Upload a résumé first in the Resume Analyzer.</p>
              ) : (
                <select
                  id="resume"
                  value={resumeId}
                  onChange={(e) => setResumeId(e.target.value)}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                >
                  {resumes.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.filename}
                    </option>
                  ))}
                </select>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="jd">Paste the job description</Label>
              <textarea
                id="jd"
                value={jd}
                onChange={(e) => setJd(e.target.value)}
                rows={10}
                placeholder="We're looking for a GenAI Engineer skilled in Python, LangChain, Kubernetes…"
                className="w-full resize-none rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <div className="flex gap-2">
              <Button onClick={analyze} disabled={!resumeId || !!busy} variant="outline">
                {busy === "analyze" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                Analyze
              </Button>
              <Button onClick={optimize} disabled={!resumeId || jd.length < 20 || !!busy}>
                {busy === "optimize" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Wand2 className="h-4 w-4" />}
                Optimize résumé
              </Button>
            </div>
          </CardContent>
        </Card>

        <div className="space-y-4">
          {report && (
            <Card>
              <CardHeader>
                <CardTitle>ATS report</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <ScoreRow label="ATS compatibility" value={report.ats_score} />
                <ScoreRow label="Recruiter score" value={report.recruiter_score} />
                <ScoreRow label="Technical" value={report.tech_score} />
                <ScoreRow label="Communication" value={report.comm_score} />

                {report.missing_keywords.length > 0 && (
                  <div>
                    <div className="mb-2 text-sm font-medium">Missing keywords</div>
                    <div className="flex flex-wrap gap-1">
                      {report.missing_keywords.map((k) => (
                        <Badge key={k} variant="warning">
                          {k}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
                {report.suggestions.length > 0 && (
                  <ul className="space-y-1 text-sm text-muted-foreground">
                    {report.suggestions.map((s, i) => (
                      <li key={i}>• {s}</li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          )}

          {optimized && (
            <Card>
              <CardHeader>
                <CardTitle>Optimized résumé</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="max-h-72 overflow-y-auto whitespace-pre-wrap rounded-md bg-secondary p-3 text-xs">
                  {optimized.improved_resume_text}
                </pre>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </>
  );
}

function ScoreRow({ label, value }: { label: string; value: number }) {
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className={cn("font-medium", scoreColor(value))}>{value}</span>
      </div>
      <Progress value={value} />
    </div>
  );
}
