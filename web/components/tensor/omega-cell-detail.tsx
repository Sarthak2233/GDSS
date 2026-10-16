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
          Select a cell in the Ω heatmap to inspect pairwise conflict strength.
        </p>
      </aside>
    );
  }

  return (
    <aside
      className="rounded-xl border border-border bg-surface p-5 space-y-3"
      data-testid="omega-cell-detail"
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-textMuted">
            Cell detail
          </p>
          <p className="text-sm font-mono text-text mt-1">
            {i} × {j}
          </p>
        </div>
        <EvidencePhaseBadge phase="deterministic" />
      </div>

      <p className="text-2xl font-bold tabular-nums text-text">
        ω = {omega.toFixed(3)}
      </p>

      {reasons.length > 0 ? (
        <ul className="text-xs text-textMuted space-y-1 list-disc list-inside">
          {reasons.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      ) : (
        <p className="text-xs text-textSubtle">No stored reasons (ω = 0).</p>
      )}

      <p className="text-xs text-textMuted pt-2 border-t border-border">
        Compare branch drift on{" "}
        <Link
          href="/drift"
          className="text-accent underline-offset-2 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          Drift Monitor
        </Link>
        .
      </p>
    </aside>
  );
}
