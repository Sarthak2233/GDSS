"use client";

import { useEffect, useRef, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { GitBranch, Activity, ShieldAlert, Sparkles } from "lucide-react";
import { duration, easing } from "@/lib/motion";
import { colors } from "@/lib/tokens";

interface StatItem {
  id: string;
  label: string;
  targetValue: number;
  suffix?: string;
  isDecimal?: boolean;
  icon: typeof GitBranch;
  color: string;
  bgColor: string;
}

const stats: StatItem[] = [
  {
    id: "branches",
    label: "Branches Tracked",
    targetValue: 47,
    icon: GitBranch,
    color: colors.accent,
    bgColor: "rgba(124, 92, 255, 0.1)",
  },
  {
    id: "drift",
    label: "Drift Vector",
    targetValue: 0.23,
    suffix: " rad",
    isDecimal: true,
    icon: Activity,
    color: colors.drift,
    bgColor: "rgba(255, 180, 84, 0.1)",
  },
  {
    id: "conflicts",
    label: "Conflict Tensor",
    targetValue: 3,
    suffix: " Ω",
    icon: ShieldAlert,
    color: colors.conflict,
    bgColor: "rgba(255, 107, 107, 0.1)",
  },
  {
    id: "convergence",
    label: "Convergence",
    targetValue: 94,
    suffix: "%",
    icon: Sparkles,
    color: colors.trajectory,
    bgColor: "rgba(61, 220, 151, 0.1)",
  },
];

export function StatPills() {
  const reduced = useReducedMotion();

  return (
    <div
      className="grid grid-cols-2 sm:grid-cols-4 gap-3 max-w-4xl w-full mx-auto my-6 z-content relative px-4"
      data-testid="stat-pills"
    >
      {stats.map((stat, idx) => (
        <StatPillCard key={stat.id} stat={stat} index={idx} reduced={reduced} />
      ))}
    </div>
  );
}

function StatPillCard({
  stat,
  index,
  reduced,
}: {
  stat: StatItem;
  index: number;
  reduced: boolean | null;
}) {
  const [val, setVal] = useState(0);
  const raf = useRef<number | null>(null);

  useEffect(() => {
    if (reduced) {
      setVal(stat.targetValue);
      return;
    }

    const startTime = performance.now() + index * 100;
    const ms = duration.slow;
    const tick = (now: number) => {
      if (now < startTime) {
        raf.current = requestAnimationFrame(tick);
        return;
      }
      const elapsed = Math.min((now - startTime) / ms, 1);
      const eased = 1 - Math.pow(1 - elapsed, 3);
      setVal(stat.targetValue * eased);
      if (elapsed < 1) {
        raf.current = requestAnimationFrame(tick);
      }
    };

    raf.current = requestAnimationFrame(tick);
    return () => {
      if (raf.current) cancelAnimationFrame(raf.current);
    };
  }, [stat.targetValue, index, reduced]);

  const Icon = stat.icon;
  const formattedVal = stat.isDecimal ? val.toFixed(2) : Math.round(val);

  return (
    <motion.div
      initial={reduced ? undefined : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={
        reduced
          ? { duration: 0 }
          : { duration: duration.primary / 1000, delay: index * 0.08, ease: easing.easeOut }
      }
      className="flex items-center gap-3 p-3 rounded-xl bg-surfaceGlass backdrop-blur-md border border-border/70 shadow-lg"
    >
      <div
        className="p-2.5 rounded-lg shrink-0 flex items-center justify-center"
        style={{ backgroundColor: stat.bgColor, color: stat.color }}
      >
        <Icon className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-[11px] font-medium text-textSubtle truncate">{stat.label}</p>
        <p className="text-base sm:text-lg font-bold tabular-nums text-text">
          {formattedVal}
          {stat.suffix}
        </p>
      </div>
    </motion.div>
  );
}
