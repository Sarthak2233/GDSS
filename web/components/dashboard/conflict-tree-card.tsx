"use client";

import React, { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { duration, easing } from "@/lib/motion";
import { Sparkline } from "@/components/ui/sparkline";
import { colors } from "@/lib/tokens";
import { EvidencePhaseBadge } from "@/components/ui/evidence-phase-badge";

export interface OperatorSummary {
  type: string;
  file: string;
  name?: string;
  symbol_id?: string;
  changed_block_count?: number;
}

export interface ConflictTreeCardProps {
  committedOperators: OperatorSummary[];
  uncommittedOperators: OperatorSummary[];
  isLoading?: boolean;
  error?: string | null;
}

/**
 * SVG Semantic Operator Tree diagram branching from a root symbol to transformed nodes.
 */
function TreeVisualizer({
  operators,
  hasDanger,
}: {
  operators: OperatorSummary[];
  hasDanger: boolean;
}) {
  const reduceMotion = useReducedMotion();

  // Create up to 4 branching target points
  const leafCount = Math.max(1, Math.min(4, operators.length || 1));
  const leaves = Array.from({ length: leafCount }, (_, idx) => {
    const y = 20 + idx * (60 / Math.max(1, leafCount - 1));
    const op = operators[idx];
    const isDanger =
      op &&
      (op.type.includes("signature") ||
        op.type.includes("delete") ||
        op.type.includes("conflict"));
    return {
      id: `leaf-${idx}`,
      y: Number.isNaN(y) ? 50 : y,
      color: isDanger
        ? colors.danger
        : hasDanger
          ? colors.warning
          : colors.accent,
    };
  });

  return (
    <div className="relative w-28 h-24 flex items-center justify-center">
      <svg
        viewBox="0 0 120 100"
        className="w-full h-full overflow-visible"
        aria-hidden="true"
      >
        {/* Root Symbol Node */}
        <circle cx="15" cy="50" r="4.5" fill={colors.accent} />
        <circle
          cx="15"
          cy="50"
          r="8"
          fill="none"
          stroke={colors.accent}
          strokeWidth="1"
          strokeOpacity="0.3"
        />

        {/* Branching tree edges & leaf nodes */}
        {leaves.map((leaf, idx) => (
          <motion.g
            key={leaf.id}
            initial={reduceMotion ? undefined : { opacity: 0.7 }}
            animate={
              reduceMotion
                ? undefined
                : {
                    opacity: [0.7, 1, 0.7],
                  }
            }
            transition={
              reduceMotion
                ? undefined
                : {
                    duration: (duration.slow * 6) / 1000 + idx * 0.5,
                    repeat: Infinity,
                    ease: "easeInOut",
                  }
            }
          >
            {/* Curved branch path */}
            <path
              d={`M 15 50 C 45 50, 60 ${leaf.y}, 95 ${leaf.y}`}
              fill="none"
              stroke={leaf.color}
              strokeWidth="1.5"
              strokeOpacity="0.75"
            />
            {/* Leaf node */}
            <circle cx="95" cy={leaf.y} r="3.5" fill={leaf.color} />
          </motion.g>
        ))}
      </svg>
    </div>
  );
}

export function ConflictTreeCard({
  committedOperators,
  uncommittedOperators,
  isLoading = false,
  error = null,
}: ConflictTreeCardProps) {
  const reduceMotion = useReducedMotion();
  const [activeTab, setActiveTab] = useState<"uncommitted" | "committed">(
    "uncommitted"
  );
  const [displayCount, setDisplayCount] = useState(0);

  const operators =
    activeTab === "uncommitted" ? uncommittedOperators : committedOperators;
  const count = operators.length;

  // Determine risk level
  const hasDanger = operators.some(
    (o) =>
      o.type.includes("signature") ||
      o.type.includes("delete") ||
      o.type.includes("conflict")
  );
  const hasWarning =
    operators.some((o) => o.type.includes("edit") || o.type.includes("extract")) ||
    hasDanger;

  const riskLabel = hasDanger
    ? "HIGH RISK"
    : hasWarning
      ? "MODERATE RISK"
      : "LOW RISK";

  const riskBadgeClass = hasDanger
    ? "bg-danger/15 text-danger border-danger/30"
    : hasWarning
      ? "bg-warning/15 text-warning border-warning/30"
      : "bg-success/15 text-success border-success/30";

  // Animated counter
  useEffect(() => {
    if (reduceMotion || isLoading || error) {
      setDisplayCount(count);
      return;
    }
    const start = performance.now();
    const from = displayCount;
    const to = count;
    const ms = duration.slow;
    const tick = (now: number) => {
      const t = Math.min((now - start) / ms, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      setDisplayCount(Math.round(from + (to - from) * eased));
      if (t < 1) requestAnimationFrame(tick);
    };
    const id = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [count, isLoading, error, reduceMotion]);

  if (isLoading) {
    return (
      <div
        className="rounded-xl border border-border bg-surface p-5 h-64 flex flex-col justify-between animate-pulse"
        data-testid="conflict-tree-card-skeleton"
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
          Check AST transformation parser
        </p>
      </div>
    );
  }

  // Breakdown counts
  const renames = operators.filter((o) => o.type.includes("rename")).length;
  const moves = operators.filter((o) => o.type.includes("move")).length;
  const signatures = operators.filter((o) =>
    o.type.includes("signature")
  ).length;

  const sampleSparkline = [
    Math.max(0, count - 3),
    Math.max(0, count - 1),
    Math.max(0, count - 2),
    count,
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
      data-testid="conflict-tree-card"
    >
      {/* Background glow accent */}
      <div className="absolute -top-12 -left-12 w-28 h-28 rounded-full bg-accent/10 blur-xl pointer-events-none group-hover:bg-accent/20 transition-all" />

      {/* Header with tabs & risk badge */}
      <div className="flex items-center justify-between gap-2">
        <div>
          <h3 className="text-xs font-bold uppercase tracking-wider text-textMuted">
            Operator Breakdown
          </h3>
          <p className="text-xs text-textSubtle">
            Committed vs uncommitted SemanticOperators (not Ω<sub>ij</sub>)
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <EvidencePhaseBadge phase="deterministic" />
          <span
          className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold ${riskBadgeClass}`}
        >
          {riskLabel}
        </span>
        </div>
      </div>

      {/* Operator Matrix Tabs */}
      <div className="flex items-center gap-2 mt-3 border-b border-border pb-2">
        <button
          type="button"
          onClick={() => setActiveTab("uncommitted")}
          aria-label={`Uncommitted (${uncommittedOperators.length})`}
          className={`px-3 py-1 rounded-md text-xs font-semibold transition-colors ${
            activeTab === "uncommitted"
              ? "bg-accent/15 text-accent"
              : "text-textMuted hover:text-text hover:bg-surfaceElevated"
          }`}
        >
          Uncommitted ({uncommittedOperators.length})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("committed")}
          aria-label={`Committed (${committedOperators.length})`}
          className={`px-3 py-1 rounded-md text-xs font-semibold transition-colors ${
            activeTab === "committed"
              ? "bg-accent/15 text-accent"
              : "text-textMuted hover:text-text hover:bg-surfaceElevated"
          }`}
        >
          Committed ({committedOperators.length})
        </button>
      </div>

      {/* Body: Animated Counter + Breakdown + Visualizer */}
      <div className="flex items-center justify-between my-3">
        <div>
          <div className="flex items-baseline gap-2">
            <span
              className="text-3xl font-bold tabular-nums text-text"
              aria-live="polite"
            >
              {displayCount}
            </span>
            <span className="text-xs font-medium text-textMuted">
              Operators
            </span>
          </div>

          <div className="mt-2 flex flex-wrap gap-2">
            <span className="rounded bg-surfaceElevated px-2 py-0.5 text-[11px] text-text">
              <strong>{renames}</strong> renames
            </span>
            <span className="rounded bg-surfaceElevated px-2 py-0.5 text-[11px] text-text">
              <strong>{moves}</strong> moves
            </span>
            <span className="rounded bg-surfaceElevated px-2 py-0.5 text-[11px] text-text">
              <strong>{signatures}</strong> signatures
            </span>
          </div>
        </div>

        {/* Semantic Operator Tree SVG Visualizer */}
        <TreeVisualizer operators={operators} hasDanger={hasDanger} />
      </div>

      {/* Footer: Top operators preview + Sparkline */}
      <div className="pt-3 border-t border-border flex items-center justify-between text-xs text-textMuted">
        <div className="overflow-hidden pr-2">
          {operators.length > 0 ? (
            <div className="truncate text-text font-mono text-[11px]">
              {operators[0].file} — {operators[0].type}
            </div>
          ) : (
            <span className="text-text font-medium">
              No semantic operators detected
            </span>
          )}
        </div>
        <div className="w-20 shrink-0">
          <Sparkline
            data={sampleSparkline}
            stroke={hasDanger ? colors.danger : colors.accent}
          />
        </div>
      </div>
    </motion.article>
  );
}
