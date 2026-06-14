"use client";

import { useEffect, useState } from "react";
import { Compass, Loader2, Sparkles, Target } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge, Label, Progress } from "@/components/ui/misc";
import { PageHeader } from "@/components/page-header";
import { api, apiErrorMessage } from "@/lib/api";
import { useMe } from "@/lib/hooks";
import type { AgentRun } from "@/lib/types";
import { cn, scoreColor } from "@/lib/utils";

interface Feedback {
  overall_readiness: number;
  strengths: string[];
  improvements: string[];
  summary: string;
}
interface CareerPlan {
  focus_areas: { area: string; action: string }[];
  summary: string;
}
interface InterviewPlan {
  interview_type: string;
  recommended_questions: string[];
}

export default function LearningPage() {
  const { data: me } = useMe();
  const [role, setRole] = useState("");
  const [resume, setResume] = useState("");
  const [run, setRun] = useState<AgentRun | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (me?.target_role) setRole(me.target_role);
  }, [me]);

  async function generate() {
    setBusy(true);
    setError(null);
    try {
      const { data } = await api.post<AgentRun>("/agents/career-readiness", {
        target_role: role || undefined,
        resume_text: resume || undefined,
      });
      setRun(data);
    } catch (e) {
      setError(apiErrorMessage(e, "Could not generate your plan."));
    } finally {
      setBusy(false);
    }
  }

  const feedback = run?.output.feedback as Feedback | undefined;
  const plan = run?.output.career_plan as CareerPlan | undefined;
  const interview = run?.output.interview_plan as InterviewPlan | undefined;

  return (
    <>
      <PageHeader
        title="Learning Path"
        description="Run the multi-agent Career Coach to get a personalized action plan."
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="h-4 w-4 text-primary" /> Your goal
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="role">Target role</Label>
              <input
                id="role"
                value={role}
                onChange={(e) => setRole(e.target.value)}
                placeholder="GenAI Engineer"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="resume">Résumé text (optional)</Label>
              <textarea
                id="resume"
                value={resume}
                onChange={(e) => setResume(e.target.value)}
                rows={6}
                placeholder="Paste your résumé to include resume & ATS signals…"
                className="w-full resize-none rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button onClick={generate} disabled={busy} className="w-full">
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              Generate my plan
            </Button>
          </CardContent>
        </Card>

        <div className="space-y-4 lg:col-span-2">
          {!run ? (
            <Card>
              <CardContent className="p-10 text-center text-sm text-muted-foreground">
                Set your goal and generate a plan. Seven AI agents (resume, ATS, interviewer, coding,
                behavioral, feedback, career coach) collaborate to produce it.
              </CardContent>
            </Card>
          ) : (
            <>
              {feedback && (
                <Card>
                  <CardHeader>
                    <CardTitle>Readiness verdict</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex items-baseline gap-2">
                      <span className={cn("text-4xl font-bold", scoreColor(feedback.overall_readiness))}>
                        {feedback.overall_readiness}
                      </span>
                      <span className="text-muted-foreground">/100 overall readiness</span>
                    </div>
                    <Progress value={feedback.overall_readiness} />
                    <p className="text-sm text-muted-foreground">{feedback.summary}</p>
                    {feedback.strengths.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {feedback.strengths.map((s) => (
                          <Badge key={s} variant="success">
                            {s}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

              {plan && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Compass className="h-4 w-4 text-primary" /> Your action plan
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <p className="text-sm text-muted-foreground">{plan.summary}</p>
                    {plan.focus_areas.map((f, i) => (
                      <div key={i} className="rounded-md border border-border p-3">
                        <div className="text-sm font-medium capitalize">{f.area}</div>
                        <div className="text-sm text-muted-foreground">{f.action}</div>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}

              {interview && (
                <Card>
                  <CardHeader>
                    <CardTitle>Practice questions ({interview.interview_type})</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2 text-sm">
                      {interview.recommended_questions.map((q, i) => (
                        <li key={i} className="flex gap-2">
                          <span className="text-primary">{i + 1}.</span>
                          {q}
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </div>
      </div>
    </>
  );
}
