"use client";

import { motion, useReducedMotion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { duration, easing } from "@/lib/motion";
import { colors } from "@/lib/tokens";
import { cn } from "@/lib/utils";
import { Sparkline } from "@/components/ui/sparkline";

/**
 * GDSS MetricCard - canonical dashboard component.
 * Never shows a bare number: Trend + Context + Comparison + Animation.
 * Anatomy: Container -> Header -> Body -> Actions -> Footer, revealed staggered.
 */
export type MetricTone = "default" | "warning" | "danger" | "success";

const toneColor: Record<MetricTone, string> = {
  default: "text-text",
  warning: "text-warning",
  danger: "text-danger",
  success: "text-success",
};

const sparkColor: Record<MetricTone, string> = {
  default: colors.accent,
  warning: colors.warning,
  danger: colors.danger,
  success: colors.success,
};

export function MetricCard({
  label,
  value,
  trend,
  spark,
  tone = "default",
}: {
  label: string;
  value: number;
  trend: { delta: number; percent: number; period: string };
  spark?: number[];
  tone?: MetricTone;
}) {
  const reduceMotion = useReducedMotion();
  const [display, setDisplay] = useState(0);
  const raf = useRef<number | null>(null);

  // Animated counter: previous -> value over `duration.slow` (Level 6 state change).
  useEffect(() => {
    if (reduceMotion) {
      setDisplay(value);
      return;
    }
    const start = performance.now();
    const from = display;
    const to = value;
    const ms = duration.slow;
    const tick = (now: number) => {
      const t = Math.min((now - start) / ms, 1);
      const eased = 1 - Math.pow(1 - t, 3); // easeOutCubic
      setDisplay(Math.round(from + (to - from) * eased));
      if (t < 1) raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => {
      if (raf.current) cancelAnimationFrame(raf.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, reduceMotion]);

  const arrow = trend.delta >= 0 ? "\u2191" : "\u2193";
  const sign = trend.percent >= 0 ? "+" : "";

  return (
    <motion.article
      className="rounded-lg border border-border bg-surface p-6"
      initial={reduceMotion ? undefined : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={
        reduceMotion
          ? { duration: 0 }
          : { duration: duration.primary / 1000, ease: easing.easeOut }
      }
      data-testid="metric-card"
    >
      {/* Header */}
      <p className="text-sm text-textMuted">{label}</p>

      {/* Body: animated counter + trend (Trend + Context + Comparison) */}
      <div className="mt-2 flex items-baseline gap-3">
        <span
          className={cn("text-4xl font-bold tabular-nums", toneColor[tone])}
          aria-live="polite"
        >
          {display}
        </span>
        <span className={cn("text-sm font-medium", toneColor[tone])}>
          {arrow} {trend.percent}
          {sign}%
        </span>
      </div>

      {/* Actions / context */}
      <p className="mt-1 text-xs text-textSubtle">{trend.period}</p>

      {/* Footer: sparkline (Animation) */}
      {spark && (
        <div className={cn("mt-4", toneColor[tone])}>
          <Sparkline data={spark} stroke={sparkColor[tone]} />
        </div>
      )}
    </motion.article>
  );
}
