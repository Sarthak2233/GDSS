"use client";

import React, { useState, useMemo } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { duration, easing } from "@/lib/motion";
import { colors } from "@/lib/tokens";
import { DriftEmptyState } from "@/components/drift/drift-empty-state";
import { DriftErrorState } from "@/components/drift/drift-error-state";

export interface DriftAlertItem {
  branch: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | string;
  message: string;
  magnitude: number;
  affected: { id: string; name: string }[];
}

export interface SeverityAlertsMatrixProps {
  alerts: DriftAlertItem[];
  selectedSeverity?: string;
  onSelectSeverity?: (severity: string) => void;
  selectedBranch?: string;
  onSelectBranch?: (branch: string) => void;
  onSelectSymbol?: (symbolId: string) => void;
  isLoading?: boolean;
  error?: string | null;
}

const SEVERITIES = ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"] as const;

export function SeverityAlertsMatrix({
  alerts,
  selectedSeverity: controlledSeverity,
  onSelectSeverity,
  selectedBranch: controlledBranch,
  onSelectBranch,
  onSelectSymbol,
  isLoading = false,
  error = null,
}: SeverityAlertsMatrixProps) {
  const reduceMotion = useReducedMotion();

  const [internalSeverity, setInternalSeverity] = useState<string>("ALL");
  const [internalBranch, setInternalBranch] = useState<string>("ALL");

  const activeSeverity = controlledSeverity ?? internalSeverity;
  const activeBranch = controlledBranch ?? internalBranch;

  const handleSeverityChange = (sev: string) => {
    if (onSelectSeverity) {
      onSelectSeverity(sev);
    } else {
      setInternalSeverity(sev);
    }
  };

  const handleBranchChange = (br: string) => {
    if (onSelectBranch) {
      onSelectBranch(br);
    } else {
      setInternalBranch(br);
    }
  };

  const uniqueBranches = useMemo(() => {
    const set = new Set<string>();
    alerts.forEach((a) => set.add(a.branch));
    return ["ALL", ...Array.from(set)];
  }, [alerts]);

  const bucketCounts = useMemo(() => {
    const counts: Record<string, number> = {
      ALL: alerts.length,
      CRITICAL: 0,
      HIGH: 0,
      MEDIUM: 0,
      LOW: 0,
    };
    alerts.forEach((a) => {
      const s = a.severity.toUpperCase();
      counts[s] = (counts[s] || 0) + 1;
    });
    return counts;
  }, [alerts]);

  const filteredAlerts = useMemo(() => {
    return alerts.filter((a) => {
      const matchSev =
        activeSeverity === "ALL" ||
        a.severity.toUpperCase() === activeSeverity.toUpperCase();
      const matchBr =
        activeBranch === "ALL" || a.branch === activeBranch;
      return matchSev && matchBr;
    });
  }, [alerts, activeSeverity, activeBranch]);

  if (isLoading) {
    return (
      <div
        className="w-full rounded-xl border border-border bg-surfaceGlass p-6 animate-pulse"
        role="region"
        aria-busy="true"
        aria-label="Loading severity alerts"
      >
        <div className="h-6 w-48 bg-surfaceElevated rounded mb-4" />
        <div className="flex gap-2 mb-6">
          <div className="h-8 w-24 bg-surfaceElevated rounded" />
          <div className="h-8 w-24 bg-surfaceElevated rounded" />
          <div className="h-8 w-24 bg-surfaceElevated rounded" />
        </div>
        <div className="flex flex-col gap-3">
          <div className="h-24 w-full bg-surfaceElevated rounded-lg" />
          <div className="h-24 w-full bg-surfaceElevated rounded-lg" />
        </div>
      </div>
    );
  }

  if (error) {
    return <DriftErrorState error={error} />;
  }

  if (alerts.length === 0) {
    return <DriftEmptyState />;
  }

  return (
    <div
      className="w-full flex flex-col gap-6 rounded-xl border border-border bg-surfaceGlass p-6"
      role="region"
      aria-label="Severity-bucketed alerts console"
    >
      {/* Header & Filter Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-text">
            Severity-Bucketed Alerts Console
          </h2>
          <p className="text-xs text-textMuted mt-0.5">
            Real-time conflict and drift severity evaluations across all repository trajectories.
          </p>
        </div>

        {/* Severity Bucket Pills */}
        <div className="flex flex-wrap items-center gap-1.5" role="toolbar" aria-label="Filter alerts by severity">
          {SEVERITIES.map((sev) => {
            const isSelected = activeSeverity.toUpperCase() === sev;
            const count = bucketCounts[sev] || 0;
            let pillColor: string = colors.textSubtle;
            if (sev === "CRITICAL") pillColor = colors.danger;
            else if (sev === "HIGH") pillColor = colors.warning;
            else if (sev === "MEDIUM") pillColor = colors.accent;
            else if (sev === "LOW") pillColor = colors.success;

            return (
              <button
                key={sev}
                type="button"
                onClick={() => handleSeverityChange(sev)}
                aria-pressed={isSelected}
                className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors flex items-center gap-1.5 ${
                  isSelected
                    ? "border-accent bg-accent/15 text-text"
                    : "border-border bg-surface hover:border-borderStrong text-textMuted hover:text-text"
                }`}
              >
                <span>{sev}</span>
                <span
                  className="px-1.5 py-0.2 rounded-full text-[10px] font-mono"
                  style={{
                    backgroundColor: `${pillColor}20`,
                    color: pillColor,
                  }}
                >
                  {count}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Branch Selector Bar */}
      {uniqueBranches.length > 2 && (
        <div className="flex items-center gap-2 flex-wrap text-xs text-textSubtle border-t border-border/40 pt-3">
          <span>Filter by Branch:</span>
          {uniqueBranches.map((br) => {
            const isSelected = activeBranch === br;
            return (
              <button
                key={br}
                type="button"
                onClick={() => handleBranchChange(br)}
                className={`px-2.5 py-1 rounded-md font-mono transition-colors border ${
                  isSelected
                    ? "border-accent text-accent bg-accent/10"
                    : "border-border text-textMuted hover:text-text bg-surface"
                }`}
              >
                {br}
              </button>
            );
          })}
        </div>
      )}

      {/* Alerts Matrix / List */}
      {filteredAlerts.length === 0 ? (
        <div className="p-8 text-center rounded-lg border border-border bg-surface/50 text-sm text-textMuted">
          No alerts match the selected severity ({activeSeverity}) or branch ({activeBranch}).
        </div>
      ) : (
        <div className="flex flex-col gap-3" role="list">
          {filteredAlerts.map((alert, idx) => {
            const sev = alert.severity.toUpperCase();
            let sevColor: string = colors.textMuted;
            let sevBorder: string = "border-border";
            let sevBg: string = "bg-surface";
            let explanation: string = "Minor structural delta within expected bounds.";

            if (sev === "CRITICAL") {
              sevColor = colors.danger;
              sevBorder = "border-danger/60";
              sevBg = "bg-danger/10";
              explanation = "Severe semantic conflict or API breaking change predicted.";
            } else if (sev === "HIGH") {
              sevColor = colors.warning;
              sevBorder = "border-warning/50";
              sevBg = "bg-warning/10";
              explanation = "Significant drift; inspect symbols before merging.";
            } else if (sev === "MEDIUM") {
              sevColor = colors.accent;
              sevBorder = "border-accent/40";
              sevBg = "bg-accent/10";
              explanation = "Moderate structural refactoring across methods/classes.";
            } else if (sev === "LOW") {
              sevColor = colors.success;
              sevBorder = "border-success/30";
              sevBg = "bg-success/10";
              explanation = "Minimal divergence from the reference attractor.";
            }

            return (
              <motion.div
                key={`${alert.branch}-${idx}`}
                role="listitem"
                initial={reduceMotion ? undefined : { opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={
                  reduceMotion
                    ? { duration: 0 }
                    : { duration: duration.primary / 1000, ease: easing.easeOut }
                }
                className={`flex flex-col rounded-lg border p-4 gap-3 transition-colors ${
                  sev === "CRITICAL" && !reduceMotion
                    ? `${sevBorder} bg-surfaceElevated shadow-[0_0_15px_rgba(255,107,107,0.15)]`
                    : "border-border bg-surface/60 hover:border-borderStrong"
                }`}
              >
                <div className="flex items-center justify-between gap-4 flex-wrap">
                  <div className="flex items-center gap-3">
                    <span
                      className={`px-2.5 py-0.5 rounded text-xs font-semibold tracking-wider border ${sevBorder} ${sevBg}`}
                      style={{ color: sevColor }}
                    >
                      {sev}
                    </span>
                    <span className="font-mono text-sm font-medium text-text">
                      {alert.branch}
                    </span>
                  </div>

                  <div className="flex items-center gap-3 text-xs text-textSubtle font-mono">
                    <span>
                      Magnitude:{" "}
                      <strong className="text-text">
                        {(alert.magnitude * 100).toFixed(0)}%
                      </strong>
                    </span>
                    <div className="w-16 h-1.5 bg-border rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{
                          width: `${Math.min(100, Math.max(0, alert.magnitude * 100))}%`,
                          backgroundColor: sevColor,
                        }}
                      />
                    </div>
                  </div>
                </div>

                {/* Explanation / Message */}
                <p className="text-xs text-textMuted">
                  {alert.message || explanation}
                </p>

                {/* Geometric Remediation Guide Footer */}
                <div className="p-2.5 rounded bg-surface/80 border border-border/60 text-[11px] font-mono text-textMuted flex items-center gap-2">
                  <span
                    className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                    style={{ backgroundColor: sevColor }}
                  />
                  <span>
                    {sev === "CRITICAL" &&
                      "Non-commutative transformation [T_i, T_j] ≠ 0. Manual semantic resolution required before merge."}
                    {sev === "HIGH" &&
                      "High geodesic divergence detected. Inspect symbol boundaries in 3D Constellation."}
                    {sev === "MEDIUM" &&
                      "Moderate structural refactoring. Review method signatures and call graphs."}
                    {sev === "LOW" &&
                      "Commutative transformations within normal structural drift bounds."}
                    {!["CRITICAL", "HIGH", "MEDIUM", "LOW"].includes(sev) &&
                      "Review semantic drift trajectories."}
                  </span>
                </div>

                {/* Affected Symbols Chips */}
                {alert.affected && alert.affected.length > 0 && (
                  <div className="flex items-center gap-1.5 flex-wrap pt-1 border-t border-border/40">
                    <span className="text-[11px] text-textSubtle">
                      Affected Symbols:
                    </span>
                    {alert.affected.map((sym) => (
                      <button
                        key={sym.id}
                        type="button"
                        onClick={() => onSelectSymbol?.(sym.id)}
                        className="px-2 py-0.5 rounded text-xs font-mono border border-border bg-surface hover:border-accent hover:text-accent text-text transition-colors"
                      >
                        {sym.name}
                      </button>
                    ))}
                  </div>
                )}
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}
