"use client";

import { useState } from "react";
import { Bot, Loader2, Mic, Send, Type, User } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/misc";
import { PageHeader } from "@/components/page-header";
import { VoiceRecorder } from "@/components/voice-recorder";
import { api, apiErrorMessage } from "@/lib/api";
import type { SessionState, VoiceSession, VoiceTurnResponse } from "@/lib/types";
import { cn } from "@/lib/utils";

const TYPES = ["technical", "hr", "system_design", "ml", "genai", "devops", "pm"];
const DIFFICULTIES = ["easy", "medium", "hard"];

type Msg = { role: "interviewer" | "candidate"; text: string };

export default function InterviewPage() {
  const [config, setConfig] = useState({ type: "technical", difficulty: "medium", planned_questions: 10 });
  const [focusSkills, setFocusSkills] = useState("");
  const [mode, setMode] = useState<"text" | "voice">("text");
  const [session, setSession] = useState<SessionState | null>(null);
  const [voice, setVoice] = useState<VoiceSession | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [questionsAsked, setQuestionsAsked] = useState(0);
  const [done, setDone] = useState(false);
  const [answer, setAnswer] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function start() {
    setBusy(true);
    setError(null);
    try {
      const skills = focusSkills.split(",").map((s) => s.trim()).filter(Boolean);
      const { data } = await api.post<SessionState>("/interviews/start", {
        ...config,
        skills: skills.length ? skills : undefined,
        use_resume: true,
      });
      setSession(data);
      setQuestionsAsked(data.questions_asked);
      setMessages(data.current_question ? [{ role: "interviewer", text: data.current_question }] : []);
      if (mode === "voice") {
        const { data: vs } = await api.post<VoiceSession>("/voice/start", {
          interview_session_id: data.session_id,
        });
        setVoice(vs);
      }
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  async function submitText() {
    if (!session || !answer.trim()) return;
    const myAnswer = answer.trim();
    setMessages((m) => [...m, { role: "candidate", text: myAnswer }]);
    setAnswer("");
    setBusy(true);
    try {
      const { data } = await api.post<SessionState>(
        `/interviews/sessions/${session.session_id}/answer`,
        { answer: myAnswer }
      );
      applyState(data);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  function applyState(data: SessionState) {
    setQuestionsAsked(data.questions_asked);
    if (data.done && data.summary) {
      setDone(true);
      setMessages((m) => [...m, { role: "interviewer", text: `Interview complete. ${data.summary}` }]);
    } else if (data.current_question) {
      setMessages((m) => [...m, { role: "interviewer", text: data.current_question! }]);
    }
  }

  async function submitVoice(blob: Blob) {
    if (!voice) return;
    setBusy(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("audio", blob, "answer.webm");
      const { data } = await api.post<VoiceTurnResponse>(`/voice/${voice.id}/turn`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setMessages((m) => [...m, { role: "candidate", text: data.transcript }]);
      if (data.question_audio_b64) playAudio(data.question_audio_b64);
      if (data.done) {
        setDone(true);
        if (data.summary) setMessages((m) => [...m, { role: "interviewer", text: `Interview complete. ${data.summary}` }]);
      } else if (data.next_question) {
        setQuestionsAsked((q) => q + 1);
        setMessages((m) => [...m, { role: "interviewer", text: data.next_question! }]);
      }
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  // ── Start screen ──────────────────────────────────────────────────
  if (!session) {
    return (
      <>
        <PageHeader title="Interview Room" description="Run an adaptive AI mock interview — text or voice." />
        <Card className="max-w-xl">
          <CardHeader>
            <CardTitle>Start a new interview</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-2">
              <ModeButton active={mode === "text"} onClick={() => setMode("text")} icon={Type} label="Text" />
              <ModeButton active={mode === "voice"} onClick={() => setMode("voice")} icon={Mic} label="Voice" />
            </div>
            <Field label="Interview type">
              <Select value={config.type} options={TYPES} onChange={(v) => setConfig((c) => ({ ...c, type: v }))} />
            </Field>
            <Field label="Difficulty">
              <Select value={config.difficulty} options={DIFFICULTIES} onChange={(v) => setConfig((c) => ({ ...c, difficulty: v }))} />
            </Field>
            <Field label="Questions">
              <Select value={String(config.planned_questions)} options={["5", "10", "15", "20", "30"]} onChange={(v) => setConfig((c) => ({ ...c, planned_questions: Number(v) }))} />
            </Field>
            <Field label="Focus skills (optional)">
              <input
                value={focusSkills}
                onChange={(e) => setFocusSkills(e.target.value)}
                placeholder="e.g. Python, FastAPI, Docker — leave blank to use your résumé"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
            </Field>
            <p className="text-xs text-muted-foreground">
              Tip: upload a résumé in the Resume Analyzer and we will tailor questions to your skills automatically.
            </p>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button onClick={start} disabled={busy}>
              {busy && <Loader2 className="h-4 w-4 animate-spin" />}
              Start {mode} interview
            </Button>
          </CardContent>
        </Card>
      </>
    );
  }

  // ── Interview screen ──────────────────────────────────────────────
  return (
    <>
      <PageHeader title="Interview Room" description={`${session.type} · ${mode} mode`} />
      <div className="mb-3 flex items-center gap-2 text-sm text-muted-foreground">
        <Badge variant="muted">
          Question {Math.min(questionsAsked, session.planned_questions)} / {session.planned_questions}
        </Badge>
        {done && <Badge variant="success">Completed</Badge>}
      </div>

      <Card className="flex h-[60vh] flex-col">
        <CardContent className="flex-1 space-y-4 overflow-y-auto p-5">
          {messages.map((m, i) => (
            <div key={i} className={cn("flex gap-3", m.role === "candidate" && "flex-row-reverse")}>
              <div className={cn("flex h-8 w-8 shrink-0 items-center justify-center rounded-full", m.role === "interviewer" ? "bg-primary/15 text-primary" : "bg-secondary")}>
                {m.role === "interviewer" ? <Bot className="h-4 w-4" /> : <User className="h-4 w-4" />}
              </div>
              <div className={cn("max-w-[80%] rounded-lg px-4 py-2.5 text-sm", m.role === "interviewer" ? "bg-secondary" : "bg-primary text-primary-foreground")}>
                {m.text}
              </div>
            </div>
          ))}
          {busy && <div className="text-sm text-muted-foreground">Thinking…</div>}
        </CardContent>

        {!done && (
          <div className="border-t border-border p-3">
            {mode === "voice" ? (
              <VoiceRecorder onAudio={submitVoice} disabled={busy} />
            ) : (
              <div className="flex gap-2">
                <textarea
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      void submitText();
                    }
                  }}
                  rows={2}
                  placeholder="Type your answer… (Enter to send, Shift+Enter for newline)"
                  className="flex-1 resize-none rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                />
                <Button onClick={submitText} disabled={busy || !answer.trim()} size="icon" className="h-auto">
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            )}
          </div>
        )}
      </Card>
      {error && <p className="mt-2 text-sm text-destructive">{error}</p>}
    </>
  );
}

function playAudio(b64: string) {
  try {
    const audio = new Audio(`data:audio/wav;base64,${b64}`);
    void audio.play().catch(() => {});
  } catch {
    /* ignore playback errors */
  }
}

function ModeButton({
  active,
  onClick,
  icon: Icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: typeof Mic;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex flex-1 items-center justify-center gap-2 rounded-md border py-2 text-sm font-medium transition-colors",
        active ? "border-primary bg-primary/10 text-primary" : "border-border text-muted-foreground hover:bg-secondary"
      )}
    >
      <Icon className="h-4 w-4" />
      {label}
    </button>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-2">
      <span className="text-sm font-medium">{label}</span>
      {children}
    </div>
  );
}

function Select({ value, options, onChange }: { value: string; options: string[]; onChange: (v: string) => void }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm capitalize focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      {options.map((o) => (
        <option key={o} value={o}>
          {o.replace("_", " ")}
        </option>
      ))}
    </select>
  );
}
