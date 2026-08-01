"use client";

import React, { useMemo } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { duration, easing } from "@/lib/motion";
import type { TensorEntry } from "@/lib/api-types";

export interface OmegaCellSelection {
  i: string;
  j: string;
}

export interface OmegaHeatmapProps {
  branches: string[];
  entries: TensorEntry[];
  selected: OmegaCellSelection | null;
  onSelect: (cell: OmegaCellSelection) => void;
}

function lookupOmega(
  entries: TensorEntry[],
  i: string,
  j: string
): TensorEntry | null {
  for (const e of entries) {
    if ((e.i === i && e.j === j) || (e.i === j && e.j === i)) {
      return e;
    }
  }
  return null;
}

function cellClass(omega: number): string {
  if (omega <= 0) return "bg-surfaceElevated text-textMuted";
  if (omega < 0.33) return "bg-warning/40 text-text";
  if (omega < 0.66) return "bg-warning/70 text-text";
  return "bg-conflict/80 text-text";
}

/**
 * Dense N×N Ω heatmap filled from sparse API entries.
 * Tall ~70vh panel; cells grow to fill available height.
 */
export function OmegaHeatmap({
  branches,
  entries,
  selected,
  onSelect,
}: OmegaHeatmapProps) {
  const reduceMotion = useReducedMotion();

  const cells = useMemo(() => {
    return branches.flatMap((row) =>
      branches.map((col) => {
        const entry = lookupOmega(entries, row, col);
        return {
          i: row,
          j: col,
          omega: entry?.omega ?? 0,
        };
      })
    );
  }, [branches, entries]);

  const n = branches.length;

  return (
    <section
      className="rounded-xl border border-border bg-surface p-6 shadow-md shrink-0 flex flex-col min-h-[70vh]"
      data-testid="omega-heatmap"
    >
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3 shrink-0">
        <div>
          <p className="text-sm font-bold uppercase tracking-wider text-text">
            Ω heatmap
          </p>
          <p className="text-xs text-textMuted mt-1">
            Flat pairwise matrix ({n}×{n}). Click a cell for reasons.
          </p>
        </div>
        <div className="flex items-center gap-3 text-[11px] text-textMuted">
          <span className="inline-flex items-center gap-1.5">
            <span className="h-3 w-3 rounded-sm bg-surfaceElevated border border-border" />
            0
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-3 w-3 rounded-sm bg-warning/40" />
            low
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-3 w-3 rounded-sm bg-warning/70" />
            mid
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-3 w-3 rounded-sm bg-conflict/80" />
            high
          </span>
        </div>
      </div>

      <div className="flex-1 min-h-[56vh] overflow-auto flex justify-center py-2">
        <div
          role="grid"
          aria-label="Flat conflict tensor Omega matrix"
          className="flex flex-col gap-3 w-full max-w-4xl h-full min-h-[52vh]"
        >
          <div role="row" className="flex gap-3 items-end shrink-0">
            <div
              role="columnheader"
              className="w-40 shrink-0 h-12"
              aria-hidden="true"
            />
            {branches.map((col) => (
              <div
                key={`h-${col}`}
                role="columnheader"
                className="flex-1 min-w-32 h-12 flex items-end justify-center pb-2"
                title={col}
              >
                <span className="text-sm font-mono font-semibold text-text truncate max-w-full text-center">
                  {col}
                </span>
              </div>
            ))}
          </div>

          {branches.map((row, rowIdx) => (
            <div
              key={row}
              role="row"
              className="flex gap-3 items-stretch flex-1 min-h-40"
            >
              <div
                role="rowheader"
                className="w-40 shrink-0 flex items-center justify-end pr-3"
                title={row}
              >
                <span className="text-sm font-mono font-semibold text-text truncate max-w-full text-right">
                  {row}
                </span>
              </div>
              {branches.map((col, colIdx) => {
                const cell = cells[rowIdx * n + colIdx];
                const isSelected =
                  selected !== null &&
                  ((selected.i === row && selected.j === col) ||
                    (selected.i === col && selected.j === row));
                const label = `Omega ${row} × ${col}: ${cell.omega.toFixed(2)}`;

                return (
                  <motion.button
                    key={`${row}-${col}`}
                    type="button"
                    role="gridcell"
                    aria-label={label}
                    aria-selected={isSelected}
                    onClick={() => onSelect({ i: row, j: col })}
                    className={`flex-1 min-w-32 min-h-40 rounded-lg border text-2xl font-mono font-semibold tabular-nums focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent hover:brightness-110 ${cellClass(cell.omega)} ${
                      isSelected
                        ? `border-conflict ring-2 ring-conflict${reduceMotion ? "" : " animate-glow-conflict"}`
                        : "border-border"
                    }`}
                    initial={reduceMotion ? false : { scale: 0.98 }}
                    animate={{
                      scale: isSelected && !reduceMotion ? 1.02 : 1,
                    }}
                    transition={
                      reduceMotion
                        ? { duration: 0 }
                        : {
                            duration: duration.secondary / 1000,
                            ease: easing.easeOut,
                          }
                    }
                  >
                    {cell.omega > 0 ? cell.omega.toFixed(2) : "—"}
                  </motion.button>
                );
              })}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
