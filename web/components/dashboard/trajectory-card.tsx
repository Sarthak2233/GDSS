"use client";

import React, { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { duration, easing } from "@/lib/motion";
import { Sparkline } from "@/components/ui/sparkline";
import { colors } from "@/lib/tokens";

export interface TrajectoryCardProps {
  activeBranch: string;
  referenceBranch: string;
  committedCount: number;
  uncommittedCount: number;
  stabilityPercent?: number;
  isLoading?: boolean;
  error?: string | null;
}

/**
 * Animated SVG geometric polyhedron (crystal) representing active trajectory stability.
 */
function PolyhedronVisualizer({ stability = 98.7 }: { stability: number }) {
  const reduceMotion = useReducedMotion();
  const isStable = stability >= 90;

  // Polyhedron 2D wireframe projection vertices
  const points = [
    { x: 50, y: 10 },
    { x: 85, y: 35 },
    { x: 75, y: 80 },
    { x: 25, y: 80 },
    { x: 15, y: 35 },
    { x: 50, y: 50 }, // center vertex
  ];

  return (
    <div className="relative w-24 h-24 flex items-center justify-center">
      <svg
        viewBox="0 0 100 100"
        className="w-full h-full overflow-visible"
        aria-hidden="true"
      >
        <motion.g
          animate={
            reduceMotion
              ? undefined
              : {
                  rotate: [0, 360],
                  scale: [1, 1.04, 1],
                }
          }
          transition={
            reduceMotion
              ? undefined
              : {
                  rotate: {
                    duration: (duration.slow * 50) / 1000,
                    repeat: Infinity,
                    ease: "easeInOut",
                  },
                  scale: {
                    duration: (duration.slow * 8) / 1000,
                    repeat: Infinity,
                    ease: "easeInOut",
                  },
                }
          }
          style={{ transformOrigin: "50px 50px" }}
        >
          {/* Outer polygon edges */}
          <polygon
            points="50,10 85,35 75,80 25,80 15,35"
            fill="none"
            stroke={isStable ? colors.accent : colors.warning}
            strokeWidth="1.5"
            strokeOpacity="0.8"
          />
          {/* Internal crystalline struts connecting to center vertex */}
          {points.slice(0, 5).map((pt, i) => (
            <line
              key={i}
              x1={pt.x}
              y1={pt.y}
              x2="50"
              y2="50"
              stroke={isStable ? colors.accent : colors.warning}
              strokeWidth="1"
              strokeOpacity="0.4"
              strokeDasharray="3 2"
            />
          ))}
          {/* Vertices */}
          {points.map((pt, i) => (
            <circle
              key={i}
              cx={pt.x}
              cy={pt.y}
              r={i === 5 ? "3.5" : "2.5"}
              fill={isStable ? colors.accent : colors.warning}
            />
          ))}
        </motion.g>
      </svg>
    </div>
  );
}

export function TrajectoryCard({
  activeBranch,
  referenceBranch,
  committedCount,
  uncommittedCount,
  stabilityPercent = 98.7,
  isLoading = false,
  error = null,
}: TrajectoryCardProps) {
  const reduceMotion = useReducedMotion();
  const [displayPercent, setDisplayPercent] = useState(0);

  // Animated counter for stability percent
  useEffect(() => {
    if (reduceMotion || isLoading || error) {
      setDisplayPercent(stabilityPercent);
      return;
    }
    const start = performance.now();
    const from = displayPercent;
    const to = stabilityPercent;
    const ms = duration.slow;
    const tick = (now: number) => {
      const t = Math.min((now - start) / ms, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      setDisplayPercent(Number((from + (to - from) * eased).toFixed(1)));
      if (t < 1) requestAnimationFrame(tick);
    };
    const id = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stabilityPercent, isLoading, error, reduceMotion]);

  if (isLoading) {
    return (
      <div
        className="rounded-xl border border-border bg-surface p-5 h-64 flex flex-col justify-between animate-pulse"
        data-testid="trajectory-card-skeleton"
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
          Verify branch trajectory in repository
        </p>
      </div>
    );
  }

  const sampleSparkline = [92, 94, 93, 96, 97, 98, stabilityPercent];

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
      data-testid="trajectory-card"
    >
      {/* Background glow accent */}
      <div className="absolute -top-12 -right-12 w-28 h-28 rounded-full bg-accent/10 blur-xl pointer-events-none group-hover:bg-accent/20 transition-all" />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xs font-bold uppercase tracking-wider text-textMuted">
            Trajectory Polyhedron
          </h3>
          <p className="text-xs text-textSubtle">Semantic Stability Index</p>
        </div>
        <span className="inline-flex items-center gap-1 rounded-full bg-accent/15 px-2 py-0.5 text-xs font-semibold text-accent">
          ↑ +2.1%
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
              {displayPercent}%
            </span>
            <span className="text-xs font-medium text-success">Stable</span>
          </div>

          <div className="mt-2 space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-xs text-textMuted">Branch:</span>
              <span className="text-xs font-semibold text-text truncate max-w-[140px]">
                {activeBranch || "DETACHED"}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-textMuted">Attractor:</span>
              <span className="text-xs font-medium text-textSubtle truncate max-w-[140px]">
                {referenceBranch}
              </span>
            </div>
          </div>
        </div>

        {/* 2D Polyhedron Crystal Visualizer */}
        <PolyhedronVisualizer stability={stabilityPercent} />
      </div>

      {/* Footer: Operator context + Sparkline */}
      <div className="pt-3 border-t border-border flex items-center justify-between text-xs text-textMuted">
        <div className="flex items-center gap-3">
          <span className="text-text font-semibold">{uncommittedCount} uncommitted</span>
          <span className="text-text font-semibold">{committedCount} committed</span>
        </div>
        <div className="w-20">
          <Sparkline data={sampleSparkline} stroke={colors.accent} />
        </div>
      </div>
    </motion.article>
  );
}
