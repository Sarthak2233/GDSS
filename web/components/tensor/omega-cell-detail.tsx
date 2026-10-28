"use client";

import Link from "next/link";
import { EvidencePhaseBadge } from "@/components/ui/evidence-phase-badge";

export interface OmegaCellDetailProps {
  i: string | null;
  j: string | null;
  omega: number | null;
  reasons: string[];
}

/**
 * Detail panel for a selected Ω cell: value, reasons, link to drift.
 */
export function OmegaCellDetail({
  i,
  j,
  omega,
  reasons,
}: OmegaCellDetailProps) {
  if (i === null || j === null || omega === null) {
    return (
      <aside
        className="rounded-xl border border-border bg-surface p-5"
        data-testid="omega-cell-detail"
      >
        <p className="text-xs font-bold uppercase tracking-wider text-textMuted">
          Cell detail
        </p>
        <p className="text-sm text-textSubtle mt-3">
          Select a cell in the Ω heatmap to inspect pairwise collision strength and mathematical factor weights.
        </p>
      </aside>
    );
  }

  const isSelfEnergy = i === j;
  const hasFile = reasons.some((r) => r === "same_file");
  const hasFunction = reasons.some((r) => r === "same_function");
  const hasSymbol = reasons.some((r) => r === "same_symbol");
  const hasDep = reasons.some((r) => r === "dependency_overlap");
  const interferenceReason = reasons.find((r) => r.startsWith("interference="));
  const interferenceScore = interferenceReason
    ? parseFloat(interferenceReason.split("=")[1]) || 0
    : 0;

  return (
    <aside
      className="rounded-xl border border-border bg-surface p-5 space-y-4"
      data-testid="omega-cell-detail"
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-textMuted">
            {isSelfEnergy ? "Self-Energy (Diagonal)" : "Pairwise Collision"}
          </p>
          <p className="text-sm font-mono text-text mt-1">
            <span className="text-accent">{i}</span> ×{" "}
            <span className={isSelfEnergy ? "text-accent" : "text-text"}>
              {j}
            </span>
          </p>
        </div>
        <EvidencePhaseBadge phase="deterministic" />
      </div>

      <div className="flex items-baseline gap-3">
        <p className="text-3xl font-bold tabular-nums text-text">
          Ω<sub>ij</sub> = {omega.toFixed(3)}
        </p>
        <span
          className={`px-2 py-0.5 rounded text-xs font-mono font-medium ${
            omega === 0
              ? "bg-surfaceElevated text-textMuted"
              : omega < 0.33
              ? "bg-warning/20 text-warning border border-warning/30"
              : omega < 0.66
              ? "bg-warning/30 text-warning border border-warning/50"
              : "bg-conflict/20 text-conflict border border-conflict/40"
          }`}
        >
          {omega === 0
            ? "COMMUTATIVE"
            : omega < 0.33
            ? "LOW HAZARD"
            : omega < 0.66
            ? "MODERATE RISK"
            : "HIGH COLLISION"}
        </span>
      </div>

      {isSelfEnergy ? (
        <div className="rounded-lg border border-border/60 bg-surfaceGlass p-3 text-xs space-y-1.5">
          <p className="font-semibold text-text">
            Diagonal Drift Self-Energy: min(1.0, I(B))
          </p>
          <p className="text-textMuted">
            Represents the total accumulated semantic drift of branch{" "}
            <span className="font-mono text-accent">{i}</span> from the
            attractor tip and historical commit transformations.
          </p>
        </div>
      ) : (
        <div className="rounded-lg border border-border/60 bg-surfaceGlass p-3 text-xs space-y-2">
          <p className="font-semibold text-text uppercase tracking-wider text-[11px]">
            5-Term Discrete Formula Decomposition
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] font-mono">
            <div
              className={`p-2 rounded border ${
                hasFile
                  ? "border-warning/50 bg-warning/10 text-text"
                  : "border-border/40 bg-surface/40 text-textMuted"
              }`}
            >
              <div className="flex justify-between">
                <span>w_file · S_file</span>
                <strong>{hasFile ? "+0.20" : "0.00"}</strong>
              </div>
              <span className="text-[10px] text-textSubtle">
                {hasFile ? "Shared file touched" : "Orthogonal files"}
              </span>
            </div>

            <div
              className={`p-2 rounded border ${
                hasFunction
                  ? "border-warning/50 bg-warning/10 text-text"
                  : "border-border/40 bg-surface/40 text-textMuted"
              }`}
            >
              <div className="flex justify-between">
                <span>w_func · S_func</span>
                <strong>{hasFunction ? "+0.50" : "0.00"}</strong>
              </div>
              <span className="text-[10px] text-textSubtle">
                {hasFunction ? "Same function modified" : "Independent functions"}
              </span>
            </div>

            <div
              className={`p-2 rounded border ${
                hasSymbol
                  ? "border-conflict/50 bg-conflict/10 text-text"
                  : "border-border/40 bg-surface/40 text-textMuted"
              }`}
            >
              <div className="flex justify-between">
                <span>w_sym · S_sym</span>
                <strong>{hasSymbol ? "+0.70" : "0.00"}</strong>
              </div>
              <span className="text-[10px] text-textSubtle">
                {hasSymbol ? "Symbol signature clash" : "No symbol overlap"}
              </span>
            </div>

            <div
              className={`p-2 rounded border ${
                hasDep
                  ? "border-accent/50 bg-accent/10 text-text"
                  : "border-border/40 bg-surface/40 text-textMuted"
              }`}
            >
              <div className="flex justify-between">
                <span>w_dep · S_dep</span>
                <strong>{hasDep ? "+0.40" : "0.00"}</strong>
              </div>
              <span className="text-[10px] text-textSubtle">
                {hasDep ? "Transitive call graph overlap" : "Independent paths"}
              </span>
            </div>
          </div>

          <div
            className={`p-2 rounded border text-[11px] font-mono ${
              interferenceScore > 0
                ? "border-conflict/50 bg-conflict/10 text-text"
                : "border-border/40 bg-surface/40 text-textMuted"
            }`}
          >
            <div className="flex justify-between">
              <span>w_interfere · I(T_i, T_j)</span>
              <strong>
                {interferenceScore > 0
                  ? `+${(0.3 * interferenceScore).toFixed(2)}`
                  : "0.00"}
              </strong>
            </div>
            <span className="text-[10px] text-textSubtle">
              {interferenceScore > 0
                ? `Non-commutative operator clash ratio: ${(interferenceScore * 100).toFixed(0)}%`
                : "Operators commute cleanly ([T_i, T_j] = 0)"}
            </span>
          </div>
        </div>
      )}

      {reasons.length > 0 && (
        <div className="space-y-1">
          <p className="text-[11px] font-bold text-textSubtle uppercase tracking-wider">
            Active Telemetry Reasons:
          </p>
          <ul className="text-xs text-textMuted space-y-1 list-disc list-inside font-mono">
            {reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex items-center justify-between text-xs text-textMuted pt-3 border-t border-border">
        <span>Cross-reference:</span>
        <div className="flex items-center gap-3">
          <Link
            href="/drift"
            className="text-accent underline-offset-2 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            Drift Monitor
          </Link>
          <span className="text-textSubtle">·</span>
          <Link
            href="/graph"
            className="text-accent underline-offset-2 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            Semantic Graph
          </Link>
        </div>
      </div>
    </aside>
  );
}
