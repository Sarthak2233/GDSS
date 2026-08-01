"use client";

import { useMemo, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { EvidencePhaseBadge } from "@/components/ui/evidence-phase-badge";
import { duration, easing } from "@/lib/motion";
import type { CommutativityPair } from "@/lib/api-types";

export interface CommutativityTableProps {
  pairs: CommutativityPair[];
}

type FilterMode = "interfere" | "all";

/**
 * Compact OperatorType×OperatorType commutativity view.
 * Defaults to INTERFERE pairs; deterministic evidence badge.
 */
export function CommutativityTable({ pairs }: CommutativityTableProps) {
  const reduceMotion = useReducedMotion();
  const [filter, setFilter] = useState<FilterMode>("interfere");

  const visible = useMemo(() => {
    if (filter === "all") return pairs;
    return pairs.filter((p) => p.class === "interfere");
  }, [pairs, filter]);

  // Deduplicate unordered display: show a≤b lexicographically for interfere filter density
  const rows = useMemo(() => {
    const seen = new Set<string>();
    const out: CommutativityPair[] = [];
    for (const p of visible) {
      const key = [p.a, p.b].sort().join("|") + "|" + p.class;
      if (seen.has(key)) continue;
      seen.add(key);
      out.push(p);
      if (out.length >= 48) break;
    }
    return out;
  }, [visible]);

  return (
    <section
      className="rounded-xl border border-border bg-surface p-5"
      data-testid="commutativity-table"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-textMuted">
            Commutativity table
          </p>
          <p className="text-xs text-textSubtle mt-0.5">
            [T<sub>i</sub>, T<sub>j</sub>] type pairs — deterministic
          </p>
        </div>
        <EvidencePhaseBadge phase="deterministic" />
      </div>

      <div className="flex gap-2 mb-3" role="group" aria-label="Filter commutativity class">
        <button
          type="button"
          onClick={() => setFilter("interfere")}
          className={`px-3 py-1 rounded-md text-xs font-medium border focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent ${
            filter === "interfere"
              ? "bg-danger/15 text-danger border-danger/40"
              : "bg-surfaceElevated text-textMuted border-border"
          }`}
        >
          Interfere
        </button>
        <button
          type="button"
          onClick={() => setFilter("all")}
          className={`px-3 py-1 rounded-md text-xs font-medium border focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent ${
            filter === "all"
              ? "bg-accent/15 text-accent border-accent/40"
              : "bg-surfaceElevated text-textMuted border-border"
          }`}
        >
          All
        </button>
      </div>

      <div className="overflow-x-auto max-h-40 overflow-y-auto">
        <table className="w-full text-left text-xs">
          <thead className="sticky top-0 bg-surface">
            <tr className="text-textMuted uppercase tracking-wider">
              <th className="py-2 pr-2 font-semibold">A</th>
              <th className="py-2 pr-2 font-semibold">B</th>
              <th className="py-2 font-semibold">Class</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((p) => (
              <motion.tr
                key={`${p.a}-${p.b}-${p.class}`}
                className="border-t border-border"
                initial={reduceMotion ? undefined : { opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={
                  reduceMotion
                    ? { duration: 0 }
                    : { duration: duration.tiny / 1000, ease: easing.easeOut }
                }
              >
                <td className="py-1.5 pr-2 font-mono text-text">{p.a}</td>
                <td className="py-1.5 pr-2 font-mono text-text">{p.b}</td>
                <td className="py-1.5 font-medium text-textMuted">{p.class}</td>
              </motion.tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && (
          <p className="text-sm text-textSubtle py-4">No pairs in this filter.</p>
        )}
      </div>
    </section>
  );
}
