"use client";

import { useRef, useState } from "react";
import { Loader2, Mic, Square } from "lucide-react";
import { Button } from "@/components/ui/button";

export function VoiceRecorder({
  onAudio,
  disabled,
}: {
  onAudio: (blob: Blob) => void;
  disabled?: boolean;
}) {
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  async function start() {
    setError(null);
    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      setError("Microphone is not available in this browser.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        stream.getTracks().forEach((t) => t.stop());
        onAudio(blob);
      };
      recorderRef.current = recorder;
      recorder.start();
      setRecording(true);
    } catch {
      setError("Could not access the microphone.");
    }
  }

  function stop() {
    recorderRef.current?.stop();
    setRecording(false);
  }

  return (
    <div className="flex flex-col items-center gap-2">
      {recording ? (
        <Button onClick={stop} variant="destructive" size="lg" className="rounded-full">
          <Square className="h-4 w-4" /> Stop &amp; send
        </Button>
      ) : (
        <Button onClick={start} disabled={disabled} size="lg" className="rounded-full">
          {disabled ? <Loader2 className="h-4 w-4 animate-spin" /> : <Mic className="h-4 w-4" />}
          {disabled ? "Processing…" : "Record answer"}
        </Button>
      )}
      {recording && (
        <span className="flex items-center gap-2 text-xs text-destructive">
          <span className="h-2 w-2 animate-pulse rounded-full bg-destructive" /> Recording…
        </span>
      )}
      {error && <span className="text-xs text-destructive">{error}</span>}
    </div>
  );
}
