"use client";

import Link from "next/link";
import { Code2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge, Skeleton } from "@/components/ui/misc";
import { PageHeader } from "@/components/page-header";
import { useChallenges } from "@/lib/hooks";

const DIFF_VARIANT: Record<string, "success" | "warning" | "muted"> = {
  easy: "success",
  medium: "warning",
  hard: "muted",
};

export default function CodingPage() {
  const { data: challenges, isLoading } = useChallenges();

  return (
    <>
      <PageHeader
        title="Coding Room"
        description="LeetCode-style challenges with hidden tests and DSA evaluation."
      />

      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      ) : !challenges?.length ? (
        <Card>
          <CardContent className="p-8 text-center text-sm text-muted-foreground">
            No challenges available yet. A mentor or admin can author them via the API.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {challenges.map((c) => (
            <Link key={c.id} href={`/coding/${c.id}`} className="block">
              <Card className="h-full transition-colors hover:border-primary/40">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="flex items-center gap-2">
                      <Code2 className="h-4 w-4 text-primary" /> {c.title}
                    </CardTitle>
                    <Badge variant={DIFF_VARIANT[c.difficulty] ?? "muted"}>{c.difficulty}</Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-1">
                    {c.tags.map((t) => (
                      <Badge key={t} variant="muted">
                        {t}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </>
  );
}
