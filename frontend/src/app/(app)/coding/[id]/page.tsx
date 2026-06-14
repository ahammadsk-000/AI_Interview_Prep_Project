"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Editor from "@monaco-editor/react";
import { CheckCircle2, Loader2, Play, Upload, XCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge, Skeleton } from "@/components/ui/misc";
import { api, apiErrorMessage } from "@/lib/api";
import type { ChallengeDetail, SubmissionResult } from "@/lib/types";
import { cn, scoreColor } from "@/lib/utils";

const LANGUAGES = ["python", "javascript", "java", "go", "cpp", "csharp"];

export default function ChallengeDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [challenge, setChallenge] = useState<ChallengeDetail | null>(null);
  const [language, setLanguage] = useState("python");
  const [source, setSource] = useState("");
  const [result, setResult] = useState<SubmissionResult | null>(null);
  const [busy, setBusy] = useState<"run" | "submit" | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<ChallengeDetail>(`/coding/challenges/${id}`)
      .then(({ data }) => {
        setChallenge(data);
        setSource(data.starter_code?.[language] ?? data.starter_code?.python ?? "");
      })
      .catch((e) => setError(apiErrorMessage(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function execute(kind: "run" | "submit") {
    setBusy(kind);
    setError(null);
    setResult(null);
    try {
      const { data } = await api.post<SubmissionResult>(
        `/coding/challenges/${id}/${kind}`,
        { language, source }
      );
      setResult(data);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setBusy(null);
    }
  }

  if (!challenge) {
    return <Skeleton className="h-[70vh] w-full" />;
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {/* Problem */}
      <Card className="lg:max-h-[80vh] lg:overflow-y-auto">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>{challenge.title}</CardTitle>
            <Badge variant="muted">{challenge.difficulty}</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="whitespace-pre-wrap text-sm text-muted-foreground">{challenge.prompt}</p>
          <div>
            <div className="mb-1 text-xs font-medium uppercase text-muted-foreground">Entrypoint</div>
            <code className="rounded bg-secondary px-2 py-1 text-sm">{challenge.entrypoint}(…)</code>
          </div>
          <div>
            <div className="mb-2 text-xs font-medium uppercase text-muted-foreground">
              Sample tests ({challenge.hidden_test_count} hidden)
            </div>
            <div className="space-y-1">
              {challenge.visible_test_cases.map((tc, i) => (
                <div key={i} className="rounded-md bg-secondary px-3 py-2 text-xs font-mono">
                  {challenge.entrypoint}({JSON.stringify(tc.args).slice(1, -1)}) → {JSON.stringify(tc.expected)}
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Editor + results */}
      <div className="space-y-4">
        <Card>
          <CardHeader className="flex-row items-center justify-between space-y-0">
            <select
              value={language}
              onChange={(e) => {
                setLanguage(e.target.value);
                setSource(challenge.starter_code?.[e.target.value] ?? source);
              }}
              className="h-8 rounded-md border border-input bg-background px-2 text-sm capitalize"
            >
              {LANGUAGES.map((l) => (
                <option key={l} value={l}>
                  {l}
                </option>
              ))}
            </select>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" onClick={() => execute("run")} disabled={!!busy}>
                {busy === "run" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                Run
              </Button>
              <Button size="sm" onClick={() => execute("submit")} disabled={!!busy}>
                {busy === "submit" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                Submit
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="overflow-hidden rounded-md border border-border">
              <Editor
                height="42vh"
                language={language === "cpp" ? "cpp" : language === "csharp" ? "csharp" : language}
                theme="vs-dark"
                value={source}
                onChange={(v) => setSource(v ?? "")}
                options={{ minimap: { enabled: false }, fontSize: 13, scrollBeyondLastLine: false }}
              />
            </div>
          </CardContent>
        </Card>

        {error && <p className="text-sm text-destructive">{error}</p>}

        {result && <ResultPanel result={result} />}
      </div>
    </div>
  );
}

function ResultPanel({ result }: { result: SubmissionResult }) {
  const accepted = result.status === "accepted";
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle className="flex items-center gap-2">
          {accepted ? (
            <CheckCircle2 className="h-5 w-5 text-success" />
          ) : (
            <XCircle className="h-5 w-5 text-destructive" />
          )}
          <span className="capitalize">{result.status.replace("_", " ")}</span>
        </CardTitle>
        <span className="text-sm text-muted-foreground">
          {result.passed}/{result.total} passed
        </span>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-3 gap-3 text-center">
          <Metric label="Readiness" value={result.readiness_score} />
          <Metric label="Correctness" value={result.correctness_score} />
          <Metric label="Code quality" value={result.code_quality_score} />
        </div>
        <div className="flex flex-wrap gap-2 text-xs">
          <Badge variant="muted">Time {result.time_complexity}</Badge>
          <Badge variant="muted">Space {result.space_complexity}</Badge>
          {result.runtime_ms != null && <Badge variant="muted">{result.runtime_ms.toFixed(1)} ms</Badge>}
        </div>
        {result.cases.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {result.cases.map((c) => (
              <span
                key={c.index}
                title={c.error ?? undefined}
                className={cn(
                  "flex h-6 w-6 items-center justify-center rounded text-xs",
                  c.passed ? "bg-success/15 text-success" : "bg-destructive/15 text-destructive"
                )}
              >
                {c.index + 1}
              </span>
            ))}
          </div>
        )}
        {result.suggestions.length > 0 && (
          <ul className="space-y-1 text-sm text-muted-foreground">
            {result.suggestions.map((s, i) => (
              <li key={i}>• {s}</li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md bg-secondary p-3">
      <div className={cn("text-xl font-semibold", scoreColor(value))}>{value}</div>
      <div className="text-xs text-muted-foreground">{label}</div>
    </div>
  );
}
