"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  Bot,
  Code2,
  FileText,
  GraduationCap,
  LayoutDashboard,
  ScanSearch,
  Settings,
  Sparkles,
  Users,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/resume", label: "Resume Analyzer", icon: FileText },
  { href: "/ats", label: "ATS Optimizer", icon: ScanSearch },
  { href: "/interview", label: "Interview Room", icon: Bot },
  { href: "/coding", label: "Coding Room", icon: Code2 },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/learning", label: "Learning Path", icon: GraduationCap },
  { href: "/teams", label: "Teams", icon: Users },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r border-border bg-card/40 md:flex">
      <div className="flex h-14 items-center gap-2 border-b border-border px-5 font-semibold">
        <Sparkles className="h-5 w-5 text-primary" />
        PrepForge
      </div>
      <nav className="flex-1 space-y-1 p-3">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground"
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
