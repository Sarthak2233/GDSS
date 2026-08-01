"use client";

import React from "react";
import { colors } from "@/lib/tokens";
import type { SimilarHit } from "@/lib/api-types";

export interface NeighborRankPanelProps {
  querySymbol: string | null;
  hits: SimilarHit[];
  onSelect: (id: string) => void;
}

export function NeighborRankPanel({
  querySymbol,
  hits,
  onSelect,
}: NeighborRankPanelProps) {
  return (
    <aside
      className="w-full md:w-72 flex-shrink-0 rounded-xl border border-border bg-surfaceElevated p-4 flex flex-col gap-3"
      aria-label="Nearest neighbors"
    >
      <div>
        <h2 className="text-sm font-semibold text-foreground">Nearest neighbors</h2>
        <p className="text-xs text-textSubtle mt-0.5">
          {querySymbol
            ? `Cosine neighbors of ${querySymbol} (assistive)`
            : "Select a symbol to rank embedding neighbors"}
        </p>
      </div>

      {!querySymbol && (
        <p className="text-xs text-textMuted" role="status">
          No query yet.
        </p>
      )}

      {querySymbol && hits.length === 0 && (
        <p className="text-xs text-textMuted" role="status">
          No neighbors found for this symbol.
        </p>
      )}

      <ul className="flex flex-col gap-2 overflow-y-auto max-h-80">
        {hits.map((hit, index) => {
          const pct = Math.round(Math.max(0, Math.min(1, hit.score)) * 100);
          return (
            <li key={hit.id}>
              <button
                type="button"
                onClick={() => onSelect(hit.id)}
                aria-label={`${hit.name || hit.id}`}
                className="w-full text-left rounded-lg border border-border bg-surface hover:border-accent/50 px-3 py-2 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-medium text-text truncate">
                    <span className="text-textSubtle mr-1.5">#{index + 1}</span>
                    {hit.name || hit.id}
                  </span>
                  <span className="text-xs font-mono text-merge flex-shrink-0">
                    {pct}%
                  </span>
                </div>
                <div
                  className="mt-1.5 h-1.5 rounded-full bg-border overflow-hidden"
                  aria-hidden
                >
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${pct}%`,
                      backgroundColor: colors.merge,
                    }}
                  />
                </div>
                {hit.location && (
                  <p className="text-[10px] text-textSubtle font-mono truncate mt-1">
                    {hit.location}
                  </p>
                )}
              </button>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
