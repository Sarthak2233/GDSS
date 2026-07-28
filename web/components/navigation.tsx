"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Share2, Activity, Shapes } from "lucide-react";

import { Logo } from "@/components/ui/logo";

const links = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/graph", label: "Semantic Graph", icon: Share2 },
  { href: "/drift", label: "Drift Monitor", icon: Activity },
  { href: "/similar", label: "Similar Symbols", icon: Shapes },
];

export function Navigation() {
  const pathname = usePathname();

  return (
    <nav className="w-64 border-r border-border h-full bg-background flex flex-col">
      <div className="py-1 px-2 border-b border-border flex flex-col items-center">
        <Logo />
        <p className="text-[7px] sm:text-[7px] text-center uppercase font-bold text-muted-foreground tracking-[0.2em] leading-[1.4] relative z-10 w-full drop-shadow">
          Geometric Distributed<br />Software Synchronizer
        </p>
      </div>
      <div className="py-6 flex-1 flex flex-col gap-1 relative">
        {links.map((link) => {
          const isActive = pathname.startsWith(link.href);
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`flex items-center gap-3 px-4 py-2 mx-2 rounded-md transition-colors ${isActive
                ? "bg-primary/10 text-primary font-medium"
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
                }`}
            >
              <link.icon className="h-5 w-5" />
              {link.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
