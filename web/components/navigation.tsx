"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Share2,
  Activity,
  Shapes,
  GitCommit,
  GitMerge,
} from "lucide-react";

import { Logo } from "@/components/ui/logo";

const links = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/graph", label: "Semantic Graph", icon: Share2 },
  { href: "/drift", label: "Drift Monitor", icon: Activity },
  { href: "/tensor", label: "Conflict Tensor", icon: GitMerge },
  { href: "/log", label: "Semantic Log", icon: GitCommit },
  { href: "/similar", label: "Embedding Space", icon: Shapes },
];

export function Navigation() {
  const pathname = usePathname();

  return (
    <aside className="w-64 h-full flex flex-col gap-3 shrink-0">
      {/* Box 1: Logo Box (Top-Left) */}
      <div className="bg-surface border border-border rounded-xl p-3 flex flex-col items-center justify-center shrink-0 shadow-md">
        <Logo />
        <p className="text-[7px] sm:text-[7px] text-center uppercase font-bold text-textMuted tracking-[0.2em] leading-snug relative z-content w-full drop-shadow mt-1">
          Gate Distributive<br />Semantic Synopsis
        </p>
      </div>

      {/* Box 3: Navigation Links Box (Bottom-Left) */}
      <nav className="flex-1 bg-surface border border-border rounded-xl p-3 flex flex-col gap-10 overflow-y-auto shadow-md">
        {links.map((link) => {
          const isActive = pathname.startsWith(link.href);
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors text-sm font-medium ${isActive
                ? "bg-accent/15 text-accent font-semibold"
                : "text-textMuted hover:bg-surfaceElevated hover:text-text"
                }`}
            >
              <link.icon className="h-5 w-5" />
              {link.label}
            </Link>
          );
        })}
      </nav>

      {/* Box 4: Deterministic Engine Status Badge */}
      <div className="bg-surface border border-border rounded-xl p-3 flex flex-col gap-1 shadow-md text-xs font-mono shrink-0">
        <div className="flex items-center justify-between">
          <span className="text-textSubtle text-[10px] uppercase font-bold tracking-wider">
            Engine Mode
          </span>
          <span className="h-2 w-2 rounded-full bg-success animate-pulse" aria-hidden="true" />
        </div>
        <p className="text-text font-semibold text-[11px]">
          Deterministic Core
        </p>
        <span className="text-[10px] text-accent font-semibold">
          $0 Tokens · Local AST Proof
        </span>
      </div>
    </aside>
  );
}
