"use client";

import { motion, useReducedMotion } from "framer-motion";
import { EvidencePhaseBadge } from "@/components/ui/evidence-phase-badge";
import { duration, easing } from "@/lib/motion";
import { colors } from "@/lib/tokens";

export interface MergeRiskCardProps {
  mergeRisk: number;
  reference: string;
  isLoading?: boolean;
}

/**
 * Hero R_merge from flat Omega — deterministic, not geometric.
 */
export function MergeRiskCard({
  mergeRisk,
  reference,
  isLoading = false,
}: MergeRiskCardProps) {
  const reduceMotion = useReducedMotion();
  const display = Math.max(0, mergeRisk);

  if (isLoading) {
    return (
      <div
        className="rounded-xl border border-border bg-surface p-5 h-40 animate-pulse"
        data-testid="merge-risk-card-skeleton"
      >
        <div className="h-4 w-1/3 bg-surfaceElevated rounded" />
        <div className="h-10 w-1/2 bg-surfaceElevated rounded mt-6" />
      </div>
    );
  }

  const riskColor =
    display >= 1 ? colors.danger : display >= 0.4 ? colors.warning : colors.success;

  return (
    <motion.article
      className="rounded-xl border border-border bg-surface p-5 shadow-md"
      data-testid="merge-risk-card"
      initial={reduceMotion ? undefined : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={
        reduceMotion
          ? { duration: 0 }
          : { duration: duration.primary / 1000, ease: easing.easeOut }
      }
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-textMuted">
            R_merge
          </p>
          <p className="text-xs text-textSubtle mt-0.5">
            Sum of sparse Ω entries vs{" "}
            <span className="font-mono text-accent">{reference}</span>
          </p>
        </div>
        <EvidencePhaseBadge phase="deterministic" />
      </div>

      <p
        className="text-4xl font-bold tabular-nums mt-4"
        style={{ color: riskColor }}
        aria-live="polite"
      >
        {display.toFixed(4)}
      </p>

      <p className="text-[11px] text-textMuted mt-3 pt-3 border-t border-border">
        Flat rank-2 Ω (not geometric). Predicts interference; never auto-merges.
      </p>
    </motion.article>
  );
}
