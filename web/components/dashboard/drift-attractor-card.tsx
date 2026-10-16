"use client";

import React, { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { duration, easing } from "@/lib/motion";
import { Sparkline } from "@/components/ui/sparkline";
import { colors } from "@/lib/tokens";

import type { DriftHistoryPoint } from "@/lib/api-types";

export interface DriftBranchSummary {
  branch: string;
  magnitude: number;
  velocity: number;
  convergence: string; // from API convergence_label
  affected: { id: string; name: string }[];
  history?: DriftHistoryPoint[];
}

export interface DriftAttractorCardProps {
  referenceBranch: string;
  branches: DriftBranchSummary[];
  isLoading?: boolean;
  error?: string | null;
}

/**
 * Animated SVG Orbital Phase-Space Plot (Concentric attractor rings + orbiting branch nodes).
 */
function OrbitalVisualizer({
  branches,
}: {
  branches: DriftBranchSummary[];
}) {
  const reduceMotion = useReducedMotion();

  // Pick up to 3 branch orbital nodes
  const nodes = branches.slice(0, 3).map((b, idx) => {
    // Radius proportional to magnitude (clamped between 18 and 42)
    const radius = Math.min(42, Math.max(18, 20 + b.magnitude * 30));
    const angle = idx * 120 + 45;
    const rad = (angle * Math.PI) / 180;
    const x = 50 + radius * Math.cos(rad);
    const y = 50 + radius * Math.sin(rad);
    const isConverging = b.convergence === "converging" || b.velocity <= 0;
    return {
      id: b.branch,
      x,
      y,
      radius,
      color: isConverging ? colors.accent : colors.warning,
    };
  });

  return (
    <div className="relative w-24 h-24 flex items-center justify-center">
      <svg
        viewBox="0 0 100 100"
        className="w-full h-full overflow-visible"
        aria-hidden="true"
      >
        {/* Attractor Center & Rings */}
        <circle
          cx="50"
          cy="50"
          r="40"
          fill="none"
          stroke={colors.accent}
          strokeWidth="1"
          strokeOpacity="0.15"
          strokeDasharray="2 2"
        />
        <circle
          cx="50"
          cy="50"
          r="24"
          fill="none"
          stroke={colors.accent}
          strokeWidth="1"
          strokeOpacity="0.25"
        />
        <circle
          cx="50"
          cy="50"
          r="4"
          fill={colors.accent}
          stroke={colors.accent}
          strokeWidth="2"
          strokeOpacity="0.5"
        />

        {/* Orbiting Branch Nodes */}
        {nodes.map((node, i) => (
          <motion.g
            key={node.id}
            animate={
              reduceMotion
                ? undefined
                : {
                    rotate: [0, 360],
                  }
            }
            transition={
              reduceMotion
                ? undefined
                : {
                    rotate: {
                      duration: (duration.slow * 35) / 1000 + i * 4,
                      repeat: Infinity,
                      ease: "easeInOut",
                    },
                  }
            }
            style={{ transformOrigin: "50px 50px" }}
          >
            <line
              x1="50"
              y1="50"
              x2={node.x}
              y2={node.y}
              stroke={node.color}
              strokeWidth="1"
              strokeOpacity="0.3"
            />
            <circle cx={node.x} cy={node.y} r="3.5" fill={node.color} />
          </motion.g>
        ))}
      </svg>
    </div>
  );
}

export function DriftAttractorCard({
  referenceBranch,
  branches,
  isLoading = false,
  error = null,
}: DriftAttractorCardProps) {
  const reduceMotion = useReducedMotion();
  const [displayMag, setDisplayMag] = useState(0);

  // Calculate max drift magnitude across branches
  const maxBranch = branches.reduce(
    (max, b) => (b.magnitude > (max?.magnitude ?? -1) ? b : max),
    branches[0] || null
  );
  const maxMagnitude = maxBranch ? maxBranch.magnitude : 0;
  const isConverging =
    maxBranch &&
    (maxBranch.convergence === "converging" || maxBranch.velocity <= 0);

  // Animated counter for drift magnitude
  useEffect(() => {
    if (reduceMotion || isLoading || error) {
      setDisplayMag(maxMagnitude);
      return;
    }
    const start = performance.now();
    const from = displayMag;
    const to = maxMagnitude;
    const ms = duration.slow;
    const tick = (now: number) => {
      const t = Math.min((now - start) / ms, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      setDisplayMag(Number((from + (to - from) * eased).toFixed(3)));
      if (t < 1) requestAnimationFrame(tick);
    };
    const id = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [maxMagnitude, isLoading, error, reduceMotion]);

  if (isLoading) {
    return (
      <div
        className="rounded-xl border border-border bg-surface p-5 h-64 flex flex-col justify-between animate-pulse"
        data-testid="drift-attractor-card-skeleton"
      >
        <div className="h-4 w-1/3 bg-surfaceElevated rounded" />
        <div className="h-8 w-1/2 bg-surfaceElevated rounded" />
        <div className="h-4 w-2/3 bg-surfaceElevated rounded" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-border bg-surface p-5 h-64 flex flex-col justify-center items-center text-center">
        <p className="text-sm font-semibold text-danger">{error}</p>
        <p className="text-xs text-textMuted mt-1">
          Check reference attractor branch
        </p>
      </div>
    );
  }

  // Collect top 3 affected symbols across branches
  const affectedSymbols = branches
    .flatMap((b) => b.affected)
    .slice(0, 3);

  const maxBranchHistory = maxBranch?.history;
  const sampleSparkline =
    maxBranchHistory && maxBranchHistory.length > 1
      ? maxBranchHistory.map((p) => p.magnitude)
      : [maxMagnitude, maxMagnitude];

  return (
    <motion.article
      className="h-full rounded-xl border border-border bg-surface p-5 shadow-md flex flex-col justify-between relative overflow-hidden group hover:border-accent/40 transition-colors"
      initial={reduceMotion ? undefined : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={
        reduceMotion
          ? { duration: 0 }
          : { duration: duration.primary / 1000, ease: easing.easeOut }
      }
      data-testid="drift-attractor-card"
    >
      {/* Background glow accent */}
      <div className="absolute -bottom-12 -right-12 w-28 h-28 rounded-full bg-accent/10 blur-xl pointer-events-none group-hover:bg-accent/20 transition-all" />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xs font-bold uppercase tracking-wider text-textMuted">
            Drift vs Attractor
          </h3>
          <p className="text-xs text-textSubtle">Semantic Phase-Space Orbit</p>
        </div>
        <span
          className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ${
            branches.length === 0
              ? "bg-surfaceElevated text-textMuted"
              : isConverging
                ? "bg-accent/15 text-accent"
                : "bg-warning/15 text-warning"
          }`}
        >
          {branches.length === 0
            ? "0.00 Stable"
            : isConverging
              ? "↓ Converging"
              : "↑ Diverging"}
        </span>
      </div>

      {/* Body: Animated visualizer + Animated Counter + Trend/Comparison */}
      <div className="flex items-center justify-between my-3">
        <div>
          <div className="flex items-baseline gap-2">
            <span
              className="text-3xl font-bold tabular-nums text-text"
              aria-live="polite"
            >
              {displayMag.toFixed(3)}
            </span>
            <span className="text-xs font-medium text-textMuted">
              Max Drift
            </span>
          </div>

          <div className="mt-2 space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-xs text-textMuted">Attractor:</span>
              <span className="text-xs font-semibold text-text truncate max-w-[140px]">
                {referenceBranch}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-textMuted">Branches:</span>
              <span className="text-xs font-medium text-textSubtle">
                {branches.length} tracked
              </span>
            </div>
          </div>
        </div>

        {/* Orbital Phase-Space Visualizer */}
        <OrbitalVisualizer branches={branches} />
      </div>

      {/* Footer: Affected symbols context + Sparkline */}
      <div className="pt-3 border-t border-border flex items-center justify-between text-xs text-textMuted">
        <div className="flex items-center gap-2 overflow-hidden">
          <span className="shrink-0 text-textSubtle">Affected:</span>
          {affectedSymbols.length > 0 ? (
            <div className="flex items-center gap-1.5 truncate">
              {affectedSymbols.map((sym, i) => (
                <span
                  key={`${sym.id}-${i}`}
                  className="rounded bg-surfaceElevated px-1.5 py-0.5 text-text font-mono text-[11px]"
                >
                  {sym.name}
                </span>
              ))}
            </div>
          ) : (
            <span className="text-text font-medium">No drifted branches</span>
          )}
        </div>
        <div className="w-20 shrink-0">
          <Sparkline
            data={sampleSparkline}
            stroke={isConverging ? colors.accent : colors.warning}
          />
        </div>
      </div>
    </motion.article>
  );
}
