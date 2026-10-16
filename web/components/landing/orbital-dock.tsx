"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, useReducedMotion } from "framer-motion";
import { LayoutDashboard, Share2, Activity, Shapes, Compass } from "lucide-react";
import { spring } from "@/lib/motion";

const navItems = [
  { href: "/", label: "Overview", icon: Compass },
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/graph", label: "Semantic Graph", icon: Share2 },
  { href: "/drift", label: "Drift Monitor", icon: Activity },
  { href: "/similar", label: "Similar Symbols", icon: Shapes },
];

export function OrbitalDock() {
  const pathname = usePathname();
  const reduced = useReducedMotion();

  return (
    <nav
      aria-label="Orbital Navigation Dock"
      className="fixed bottom-6 left-1/2 -translate-x-1/2 z-sticky"
      data-testid="orbital-dock"
    >
      <div className="flex items-center gap-1.5 sm:gap-3 bg-surfaceGlass backdrop-blur-xl border border-border/80 rounded-full p-2 shadow-2xl">
        {navItems.map((item) => {
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);

          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              className="relative group p-2.5 sm:p-3 rounded-full flex flex-col items-center justify-center transition-colors outline-none focus-visible:ring-2 focus-visible:ring-accent"
            >
              {/* Active pill background */}
              {isActive && (
                <motion.div
                  layoutId="orbital-dock-active"
                  className="absolute inset-0 bg-accent/20 border border-accent/40 rounded-full z-0"
                  transition={reduced ? { duration: 0 } : spring.gentle}
                />
              )}

              {/* Icon with magnetic scale */}
              <motion.div
                whileHover={reduced ? undefined : { scale: 1.18, y: -3 }}
                whileTap={reduced ? undefined : { scale: 0.92 }}
                transition={spring.bouncy}
                className={`relative z-content transition-colors ${
                  isActive ? "text-accent font-semibold" : "text-textMuted group-hover:text-text"
                }`}
              >
                <Icon className="h-5 w-5" />
              </motion.div>

              {/* Hover Tooltip Label */}
              <div className="absolute -top-10 scale-0 group-hover:scale-100 transition-all duration-150 origin-bottom px-2.5 py-1 rounded-md bg-surfaceElevated border border-border text-[11px] font-medium text-text shadow-lg whitespace-nowrap pointer-events-none z-tooltip">
                {item.label}
              </div>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
