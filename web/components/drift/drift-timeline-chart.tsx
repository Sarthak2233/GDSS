"use client";

import React, { useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { duration, easing } from "@/lib/motion";
import { colors } from "@/lib/tokens";
import { Sparkline } from "@/components/ui/sparkline";

export interface DriftBranchData {
  branch: string;
  magnitude: number;
  velocity: number;
  convergence: string; // "converging" | "diverging" | "stable" from API convergence_label
  convergence_score?: number;
  tip_distance?: number;
  trajectory_integral?: number;
  affected: { id: string; name: string }[];
  history?: number[];
}

export interface DriftTimelineChartProps {
  branches: DriftBranchData[];
  referenceBranch?: string;
  selectedBranch?: string;
  onSelectBranch?: (branch: string) => void;
  onSelectSymbol?: (symbolId: string) => void;
}

export function DriftTimelineChart({
  branches,
  referenceBranch = "main",
  selectedBranch,
  onSelectBranch,
  onSelectSymbol,
}: DriftTimelineChartProps) {
  const reduceMotion = useReducedMotion();
  const [expandedBranch, setExpandedBranch] = useState<string | null>(null);

  const toggleExpand = (branch: string) => {
    setExpandedBranch((prev) => (prev === branch ? null : branch));
  };

  if (branches.length === 0) {
    return null;
  }

  // Calculate Manifold Summary Telemetry
  const totalTrajectories = branches.length;
  const averageDivergence =
    branches.reduce((acc, b) => acc + b.magnitude, 0) / Math.max(1, totalTrajectories);
  const convergingCount = branches.filter(
    (b) => b.convergence === "converging" || b.velocity <= 0
  ).length;
  const divergingCount = totalTrajectories - convergingCount;

  let entropyStatus = "LOW ENTROPY";
  let entropyColor: string = colors.success;
  if (averageDivergence >= 0.6) {
    entropyStatus = "HIGH ENTROPY";
    entropyColor = colors.danger;
  } else if (averageDivergence >= 0.3) {
    entropyStatus = "MODERATE ENTROPY";
    entropyColor = colors.warning;
  }

  const renderSummaryRibbon = () => (
    <div className="flex flex-wrap items-center justify-between gap-4 p-3 rounded-lg border border-border bg-surface/80 text-xs font-mono">
      <div className="flex items-center gap-4">
        <div>
          <span className="text-textSubtle">Total Trajectories: </span>
          <strong className="text-text font-semibold">{totalTrajectories}</strong>
        </div>
        <div>
          <span className="text-textSubtle">Average Divergence: </span>
          <strong className="text-text font-semibold">
            {(averageDivergence * 100).toFixed(0)}%
          </strong>
        </div>
        <div>
          <span className="text-textSubtle">Vectors: </span>
          <strong className="text-success font-semibold">{convergingCount} converging</strong>
          <span className="text-textMuted"> / </span>
          <strong className="text-warning font-semibold">{divergingCount} diverging</strong>
        </div>
      </div>
      <div
        className="px-2 py-0.5 rounded border uppercase text-[10px] font-semibold"
        style={{
          color: entropyColor,
          borderColor: `${entropyColor}40`,
          backgroundColor: `${entropyColor}15`,
        }}
      >
        {entropyStatus}
      </div>
    </div>
  );

  // Fallback table for prefers-reduced-motion
  if (reduceMotion) {
    return (
      <div
        className="w-full flex flex-col gap-4 rounded-xl border border-border bg-surfaceGlass p-6"
        role="region"
        aria-label="Drift timeline table"
      >
        <h2 className="text-base font-semibold text-text">
          Per-Branch Trajectory against <span className="font-mono text-accent">{referenceBranch}</span>
        </h2>

        {renderSummaryRibbon()}

        <table className="w-full text-left text-sm" role="table">
          <caption className="sr-only">Branch drift magnitude and convergence table</caption>
          <thead>
            <tr className="border-b border-border text-textSubtle text-xs uppercase tracking-wider">
              <th className="py-2 pr-4">Branch</th>
              <th className="py-2 pr-4">Magnitude</th>
              <th className="py-2 pr-4">Velocity</th>
              <th className="py-2 pr-4">Convergence</th>
              <th className="py-2">Affected Symbols</th>
            </tr>
          </thead>
          <tbody>
            {branches.map((b) => (
              <tr key={b.branch} className="border-b border-border/40 hover:bg-surface/50">
                <td className="py-3 pr-4 font-mono text-text">{b.branch}</td>
                <td className="py-3 pr-4 font-semibold text-text">
                  {(b.magnitude * 100).toFixed(0)}%
                </td>
                <td className="py-3 pr-4 text-textMuted">
                  {b.velocity > 0 ? "↑ +" : b.velocity < 0 ? "↓ " : "→ "}
                  {(Math.abs(b.velocity) * 100).toFixed(1)}%
                </td>
                <td className="py-3 pr-4">
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${
                      b.convergence === "converging"
                        ? "border-accent/40 text-accent bg-accent/10"
                        : b.convergence === "diverging"
                        ? "border-danger/40 text-danger bg-danger/10"
                        : "border-border text-textMuted bg-surface"
                    }`}
                  >
                    {b.convergence.toUpperCase()}
                  </span>
                </td>
                <td className="py-3">
                  <div className="flex flex-col gap-1">
                    <div className="flex flex-wrap gap-1">
                      {b.affected.slice(0, 3).map((sym) => (
                        <button
                          key={sym.id}
                          type="button"
                          onClick={() => onSelectSymbol?.(sym.id)}
                          className="px-2 py-0.5 rounded text-xs border border-border bg-surface hover:border-borderStrong text-text transition-colors"
                        >
                          {sym.name}
                        </button>
                      ))}
                      {b.affected.length > 3 && (
                        <span className="text-xs text-textSubtle px-1">
                          +{b.affected.length - 3} more
                        </span>
                      )}
                    </div>
                    {b.affected.length === 0 && b.magnitude > 0 && (
                      <span className="text-[11px] text-textSubtle italic">
                        Structural refactoring, comments, or whitespace edits preserving AST topology.
                      </span>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <div
      className="w-full flex flex-col gap-4 rounded-xl border border-border bg-surfaceGlass p-6"
      role="region"
      aria-label="Drift trajectory timeline"
    >
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-text">
            Per-Branch Trajectory against <span className="font-mono text-accent">{referenceBranch}</span>
          </h2>
          <p className="text-xs text-textMuted mt-0.5">
            Geodesic divergence magnitude, velocity, and affected AST symbols.
          </p>
        </div>
      </div>

      {renderSummaryRibbon()}

      <div className="flex flex-col gap-4 mt-2" role="list">
        {branches.map((b) => {
          const isSelected = selectedBranch === b.branch;
          const isExpanded = expandedBranch === b.branch;
          const historyPoints =
            b.history && b.history.length > 1
              ? b.history
              : [
                  Math.max(0, b.magnitude - b.velocity * 4),
                  Math.max(0, b.magnitude - b.velocity * 3),
                  Math.max(0, b.magnitude - b.velocity * 2),
                  Math.max(0, b.magnitude - b.velocity),
                  b.magnitude,
                ];

          const isConverging = b.convergence === "converging" || b.velocity <= 0;
          const badgeColor: string = isConverging ? colors.accent : colors.warning;
          const magnitudePercent = Math.min(100, Math.max(0, b.magnitude * 100));

          return (
            <motion.div
              key={b.branch}
              role="listitem"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: duration.primary / 1000, ease: easing.easeOut }}
              className={`flex flex-col rounded-lg border transition-colors bg-surface/60 ${
                isSelected ? "border-accent" : "border-border hover:border-borderStrong"
              }`}
            >
              <div className="flex flex-col md:flex-row md:items-center justify-between p-4 gap-4">
                <div className="flex items-center gap-3 min-w-[200px]">
                  <button
                    type="button"
                    onClick={() => onSelectBranch?.(b.branch)}
                    className="font-mono text-sm font-medium text-text hover:text-accent transition-colors text-left"
                  >
                    {b.branch}
                  </button>
                  <span
                    className="px-2 py-0.5 rounded text-[11px] font-mono font-semibold border uppercase tracking-wider"
                    style={{
                      borderColor: badgeColor,
                      color: badgeColor,
                      backgroundColor: `${badgeColor}15`,
                    }}
                  >
                    {isConverging
                      ? "CONVERGING TOWARD ATTRACTOR"
                      : "DIVERGING FROM ATTRACTOR"}
                  </span>
                </div>

                {/* Geodesic Energy Gauge */}
                <div className="flex-1 max-w-[220px] flex flex-col gap-1">
                  <div className="flex justify-between text-[11px] font-mono text-textMuted">
                    <span>Geodesic Energy</span>
                    <strong className="text-text">{magnitudePercent.toFixed(0)}%</strong>
                  </div>
                  <div className="h-1.5 w-full bg-border rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${magnitudePercent}%`,
                        backgroundColor: badgeColor,
                      }}
                    />
                  </div>
                </div>

                {/* Sparkline Trend */}
                <div className="flex items-center gap-2">
                  <Sparkline
                    data={historyPoints}
                    width={110}
                    height={32}
                    stroke={badgeColor}
                  />
                </div>

                {/* Magnitude & Velocity */}
                <div className="flex items-center gap-6">
                  <div className="flex flex-col text-right">
                    <span className="text-xs text-textSubtle">Magnitude</span>
                    <span className="text-base font-bold text-text">
                      {magnitudePercent.toFixed(0)}%
                    </span>
                  </div>
                  <div className="flex flex-col text-right">
                    <span className="text-xs text-textSubtle">Velocity</span>
                    <span
                      className="text-sm font-medium"
                      style={{ color: b.velocity > 0 ? colors.warning : colors.success }}
                    >
                      {b.velocity > 0 ? "↑ +" : b.velocity < 0 ? "↓ " : "→ "}
                      {(Math.abs(b.velocity) * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>

                {/* Toggle Affected Symbols */}
                <button
                  type="button"
                  onClick={() => toggleExpand(b.branch)}
                  aria-expanded={isExpanded}
                  className="px-3 py-1.5 rounded-md text-xs font-medium border border-border bg-surface hover:bg-surfaceElevated text-textMuted hover:text-text transition-colors"
                >
                  {b.affected.length} affected {b.affected.length === 1 ? "symbol" : "symbols"}{" "}
                  {isExpanded ? "▲" : "▼"}
                </button>
              </div>

              {/* Expandable Affected Symbols & Philosophical Context */}
              {isExpanded && (
                <div className="px-4 pb-4 pt-3 border-t border-border/40 flex flex-col gap-2 bg-surface/30">
                  <span className="text-xs text-textSubtle">
                    Click any symbol to inspect in 3D Semantic Constellation:
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {b.affected.map((sym) => (
                      <button
                        key={sym.id}
                        type="button"
                        onClick={() => onSelectSymbol?.(sym.id)}
                        className="px-2.5 py-1 rounded-md text-xs font-mono border border-border bg-surface hover:border-accent/60 text-text transition-colors"
                      >
                        {sym.name}
                      </button>
                    ))}
                    {b.affected.length === 0 && b.magnitude > 0 && (
                      <div className="w-full p-3 rounded-lg bg-surface border border-border/60 text-xs text-textMuted font-mono">
                        <strong className="text-text font-semibold">
                          Structural refactoring, comments, or whitespace edits preserving AST topology.
                        </strong>{" "}
                        No semantic symbols diverged from the reference attractor.
                      </div>
                    )}
                  </div>
                </div>
              )}
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
