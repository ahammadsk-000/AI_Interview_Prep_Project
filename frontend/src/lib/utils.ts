import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function scoreColor(score: number | null | undefined): string {
  if (score == null) return "text-muted-foreground";
  if (score >= 75) return "text-success";
  if (score >= 50) return "text-amber-500";
  return "text-destructive";
}

export function initials(name?: string | null, email?: string): string {
  if (name) {
    return name
      .split(" ")
      .map((p) => p[0])
      .slice(0, 2)
      .join("")
      .toUpperCase();
  }
  return (email?.[0] ?? "?").toUpperCase();
}
