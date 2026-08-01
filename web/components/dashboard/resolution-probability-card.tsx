"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { duration, easing } from "@/lib/motion";
import { colors } from "@/lib/tokens";
import { EvidencePhaseBadge } from "@/components/ui/evidence-phase-badge";

export interface ConflictRiskCardProps {
  /** Flat heuristic conflict probability in [0, 1] from ConflictProbabilityEstimator. */
  conflictScore?: number;
  reasons?: string[];
  branchCount?: number;
  isLoading?: boolean;
  error?: string | null;
}

/**
 * Honest depiction of the flat ConflictProbabilityEstimator (not phase-5 resolution).
 */
export function ConflictRiskCard({
  conflictScore = 0,
  reasons = [],
  branchCount = 0,
  isLoading = false,
  error = null,
}: ConflictRiskCardProps) {
  const reduceMotion = useReducedMotion();
  const percent = Math.round(Math.max(0, Math.min(1, conflictScore)) * 100);
  const [displayPercent, setDisplayPercent] = useState(0);

  useEffect(() => {
    if (reduceMotion || isLoading || error) {
      setDisplayPercent(percent);
      return;
    }
    const start = performance.now();
    const from = displayPercent;
    const to = percent;
    const ms = duration.slow;
    const tick = (now: number) => {
      const t = Math.min((now - start) / ms, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      setDisplayPercent(Math.round(from + (to - from) * eased));
      if (t < 1) requestAnimationFrame(tick);
    };
    const id = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [percent, isLoading, error, reduceMotion]);

  if (isLoading) {
    return (
      <div
        className="rounded-xl border border-border bg-surface p-5 h-64 flex flex-col justify-between animate-pulse"
        data-testid="conflict-risk-card-skeleton"
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
          Check /v1/drift conflict_probability
        </p>
      </div>
    );
  }

  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percent / 100) * circumference;
  const riskColor =
    percent >= 60 ? colors.danger : percent >= 30 ? colors.warning : colors.success;

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
      data-testid="conflict-risk-card"
    >
      <div className="absolute -bottom-12 -left-12 w-28 h-28 rounded-full bg-accent/10 blur-xl pointer-events-none group-hover:bg-accent/20 transition-all" />

      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-xs font-bold uppercase tracking-wider text-textMuted">
            Conflict Risk
          </h3>
          <p className="text-xs text-textSubtle">
            Flat heuristic P(conflict) vs attractor
          </p>
        </div>
        <EvidencePhaseBadge phase="assistive-heuristic" />
      </div>

      <div className="flex items-center justify-between my-4 gap-4">
        <div className="relative w-24 h-24 flex items-center justify-center shrink-0">
          <svg
            viewBox="0 0 100 100"
            className="w-full h-full -rotate-90 overflow-visible"
            aria-hidden="true"
          >
            <circle
              cx="50"
              cy="50"
              r={radius}
              fill="none"
              stroke={riskColor}
              strokeWidth="8"
              strokeOpacity="0.15"
            />
            <motion.circle
              cx="50"
              cy="50"
              r={radius}
              fill="none"
              stroke={riskColor}
              strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={circumference}
              initial={
                reduceMotion
                  ? { strokeDashoffset: offset }
                  : { strokeDashoffset: circumference }
              }
              animate={{ strokeDashoffset: offset }}
              transition={
                reduceMotion
                  ? { duration: 0 }
                  : { duration: duration.primary / 1000, ease: easing.easeOut }
              }
            />
          </svg>
          <span
            className="absolute text-lg font-bold tabular-nums text-text"
            aria-live="polite"
          >
            {displayPercent}%
          </span>
        </div>
        <div className="flex-1 min-w-0 space-y-1">
          <p className="text-xs text-textMuted">
            Max across {branchCount} branch{branchCount === 1 ? "" : "es"}
          </p>
          {reasons.length > 0 ? (
            <ul className="text-[11px] text-textSubtle space-y-0.5 list-disc list-inside">
              {reasons.slice(0, 3).map((r) => (
                <li key={r} className="truncate" title={r}>
                  {r}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-[11px] text-textSubtle">
              No shared-file / symbol interference signals.
            </p>
          )}
        </div>
      </div>

      <div className="pt-3 border-t border-border text-[11px] text-textMuted space-y-1">
        <p>
          Not Ω<sub>ij</sub> — flat R<sup>m</sup> estimator on /v1/drift.
        </p>
        <Link
          href="/tensor"
          className="text-accent underline-offset-2 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          View flat Ω matrix
        </Link>
      </div>
    </motion.article>
  );
}

/** @deprecated Use ConflictRiskCard — kept for test migration */
export const ResolutionProbabilityCard = ConflictRiskCard;
