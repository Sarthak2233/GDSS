"use client";

import React, { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { duration, easing } from "@/lib/motion";
import { Sparkline } from "@/components/ui/sparkline";
import { colors } from "@/lib/tokens";
import { EvidencePhaseBadge } from "@/components/ui/evidence-phase-badge";

export interface RemoteSyncInfo {
  label: string;
  ahead?: number;
  behind?: number;
}

export interface GlobalHealthDialCardProps {
  /** Max drift magnitude across branches (real /v1/drift signal). */
  maxDriftMagnitude?: number;
  remoteSync?: RemoteSyncInfo;
  isLoading?: boolean;
  error?: string | null;
  /** @deprecated Use maxDriftMagnitude; kept for gradual migration */
  alignmentScore?: number;
}

/**
 * Concentric radar HUD diagram scanning global repository health.
 */
function RadarVisualizer({ score = 94 }: { score: number }) {
  const reduceMotion = useReducedMotion();
  const isHealthy = score >= 85;

  return (
    <div className="relative w-24 h-24 flex items-center justify-center">
      <svg
        viewBox="0 0 100 100"
        className="w-full h-full overflow-visible"
        aria-hidden="true"
      >
        {/* Outer and Inner Radar Rings */}
        <circle
          cx="50"
          cy="50"
          r="42"
          fill="none"
          stroke={isHealthy ? colors.accent : colors.warning}
          strokeWidth="1.5"
          strokeOpacity="0.25"
        />
        <circle
          cx="50"
          cy="50"
          r="28"
          fill="none"
          stroke={isHealthy ? colors.accent : colors.warning}
          strokeWidth="1"
          strokeOpacity="0.4"
          strokeDasharray="3 3"
        />
        <circle
          cx="50"
          cy="50"
          r="14"
          fill="none"
          stroke={isHealthy ? colors.accent : colors.warning}
          strokeWidth="1"
          strokeOpacity="0.6"
        />
        <circle
          cx="50"
          cy="50"
          r="3"
          fill={isHealthy ? colors.accent : colors.warning}
        />

        {/* Crosshair axes */}
        <line
          x1="50"
          y1="8"
          x2="50"
          y2="92"
          stroke={isHealthy ? colors.accent : colors.warning}
          strokeWidth="0.75"
          strokeOpacity="0.3"
        />
        <line
          x1="8"
          y1="50"
          x2="92"
          y2="50"
          stroke={isHealthy ? colors.accent : colors.warning}
          strokeWidth="0.75"
          strokeOpacity="0.3"
        />

        {/* Rotating sweep line */}
        <motion.line
          x1="50"
          y1="50"
          x2="50"
          y2="10"
          stroke={isHealthy ? colors.accent : colors.warning}
          strokeWidth="2"
          strokeLinecap="round"
          strokeOpacity="0.8"
          animate={reduceMotion ? undefined : { rotate: [0, 360] }}
          transition={
            reduceMotion
              ? undefined
              : {
                  duration: (duration.slow * 8) / 1000,
                  repeat: Infinity,
                  ease: "easeInOut",
                }
          }
          style={{ transformOrigin: "50px 50px" }}
        />
      </svg>
    </div>
  );
}

export function GlobalHealthDialCard({
  maxDriftMagnitude,
  alignmentScore,
  remoteSync = { label: "N/A", ahead: 0, behind: 0 },
  isLoading = false,
  error = null,
}: GlobalHealthDialCardProps) {
  const reduceMotion = useReducedMotion();
  // Prefer real max drift; fall back to legacy alignmentScore only if provided alone
  const magnitude =
    maxDriftMagnitude !== undefined
      ? maxDriftMagnitude
      : alignmentScore !== undefined
        ? Math.max(0, (100 - alignmentScore) / 30)
        : 0;
  const healthPercent = Math.max(
    0,
    Math.min(100, Math.round(100 - magnitude * 100))
  );
  const [displayScore, setDisplayScore] = useState(0);

  useEffect(() => {
    if (reduceMotion || isLoading || error) {
      setDisplayScore(healthPercent);
      return;
    }
    const start = performance.now();
    const from = displayScore;
    const to = healthPercent;
    const ms = duration.slow;
    const tick = (now: number) => {
      const t = Math.min((now - start) / ms, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      setDisplayScore(Math.round(from + (to - from) * eased));
      if (t < 1) requestAnimationFrame(tick);
    };
    const id = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [healthPercent, isLoading, error, reduceMotion]);

  if (isLoading) {
    return (
      <div
        className="rounded-xl border border-border bg-surface p-5 h-64 flex flex-col justify-between animate-pulse"
        data-testid="global-health-dial-card-skeleton"
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
          Verify remote sync connectivity
        </p>
      </div>
    );
  }

  const ahead = remoteSync.ahead || 0;
  const behind = remoteSync.behind || 0;
  const isSynced = ahead === 0 && behind === 0;
  const sampleSparkline = [
    Math.max(0, healthPercent - 8),
    Math.max(0, healthPercent - 4),
    Math.max(0, healthPercent - 6),
    healthPercent,
  ];

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
      data-testid="global-health-dial-card"
    >
      <div className="absolute -top-12 -left-12 w-28 h-28 rounded-full bg-accent/10 blur-xl pointer-events-none group-hover:bg-accent/20 transition-all" />

      <div className="flex items-center justify-between gap-2">
        <div>
          <h3 className="text-xs font-bold uppercase tracking-wider text-textMuted">
            Remote Sync &amp; Drift
          </h3>
          <p className="text-xs text-textSubtle">
            Ahead/behind + max I(B<sub>i</sub>)
          </p>
        </div>
        <EvidencePhaseBadge phase="deterministic" />
      </div>

      <div className="flex items-center justify-between my-3">
        <div>
          <div className="flex items-baseline gap-2">
            <span
              className="text-3xl font-bold tabular-nums text-text"
              aria-live="polite"
            >
              {displayScore}%
            </span>
            <span className="text-xs font-medium text-textMuted">
              inverse of max drift
            </span>
          </div>

          <div className="mt-2 space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-xs text-textMuted">Remote:</span>
              <span className="text-xs font-semibold text-text truncate max-w-[140px]">
                {remoteSync.label}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-textMuted">Status:</span>
              <span
                className={`text-xs font-medium ${
                  isSynced ? "text-success" : "text-warning"
                }`}
              >
                {isSynced
                  ? "Synced with remote"
                  : `${ahead} ahead, ${behind} behind`}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-textMuted">Max drift:</span>
              <span className="text-xs font-mono text-text tabular-nums">
                {magnitude.toFixed(3)}
              </span>
            </div>
          </div>
        </div>

        <RadarVisualizer score={healthPercent} />
      </div>

      <div className="pt-3 border-t border-border flex items-center justify-between text-xs text-textMuted">
        <span className="text-text font-medium">
          From /v1/status remote_sync + /v1/drift
        </span>
        <div className="w-20">
          <Sparkline data={sampleSparkline} stroke={colors.accent} />
        </div>
      </div>
    </motion.article>
  );
}
