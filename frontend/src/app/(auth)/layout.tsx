import { Sparkles } from "lucide-react";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      {/* Brand panel */}
      <div className="relative hidden flex-col justify-between overflow-hidden bg-gradient-to-br from-primary/20 via-background to-background p-12 lg:flex">
        <div className="flex items-center gap-2 text-lg font-semibold">
          <Sparkles className="h-5 w-5 text-primary" />
          PrepForge
        </div>
        <div className="max-w-md space-y-4">
          <h1 className="text-3xl font-bold leading-tight">
            Land your next role with an AI that interviews like a pro.
          </h1>
          <p className="text-muted-foreground">
            Adaptive mock interviews, resume &amp; ATS analysis, a LeetCode-style coding room,
            behavioral grading, and a readiness dashboard — all in one place.
          </p>
        </div>
        <div className="text-xs text-muted-foreground">
          © {new Date().getFullYear()} PrepForge. Built for serious candidates.
        </div>
      </div>

      {/* Form panel */}
      <div className="flex items-center justify-center p-6">
        <div className="w-full max-w-sm animate-fade-in">{children}</div>
      </div>
    </div>
  );
}
