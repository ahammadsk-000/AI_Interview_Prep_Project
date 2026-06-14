"use client";

import { useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { FileText, Loader2, Upload } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge, Skeleton } from "@/components/ui/misc";
import { PageHeader } from "@/components/page-header";
import { api, apiErrorMessage } from "@/lib/api";
import { useResumes } from "@/lib/hooks";

export default function ResumePage() {
  const { data: resumes, isLoading } = useResumes();
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function upload(file: File) {
    setUploading(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      await api.post("/resumes", form, { headers: { "Content-Type": "multipart/form-data" } });
      qc.invalidateQueries({ queryKey: ["resumes"] });
    } catch (e) {
      setError(apiErrorMessage(e, "Upload failed."));
    } finally {
      setUploading(false);
    }
  }

  return (
    <>
      <PageHeader title="Resume Analyzer" description="Upload a résumé (PDF, DOCX, or TXT) to parse and score it." />

      <Card className="mb-4">
        <CardContent className="p-6">
          <div
            className="flex cursor-pointer flex-col items-center gap-3 rounded-lg border border-dashed border-border p-8 text-center transition-colors hover:bg-secondary/50"
            onClick={() => fileRef.current?.click()}
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
              {uploading ? <Loader2 className="h-6 w-6 animate-spin" /> : <Upload className="h-6 w-6" />}
            </div>
            <div className="text-sm font-medium">Click to upload your résumé</div>
            <div className="text-xs text-muted-foreground">PDF · DOCX · TXT, up to 5&nbsp;MB</div>
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.docx,.txt"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) void upload(f);
              }}
            />
          </div>
          {error && <p className="mt-3 text-sm text-destructive">{error}</p>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Your résumés</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {isLoading ? (
            <Skeleton className="h-16 w-full" />
          ) : !resumes?.length ? (
            <p className="text-sm text-muted-foreground">No résumés yet. Upload one to get started.</p>
          ) : (
            resumes.map((r) => (
              <div key={r.id} className="flex items-center justify-between rounded-md border border-border p-3">
                <div className="flex items-center gap-3">
                  <FileText className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <div className="text-sm font-medium">{r.filename}</div>
                    <div className="text-xs text-muted-foreground">
                      {r.parsed_chars.toLocaleString()} chars parsed
                    </div>
                  </div>
                </div>
                <Badge variant={r.status === "parsed" ? "success" : "muted"}>{r.status}</Badge>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </>
  );
}
