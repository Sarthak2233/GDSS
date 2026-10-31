"use client";

import React, { useMemo, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { motion, useReducedMotion } from "framer-motion";
import { GitMerge, RefreshCw } from "lucide-react";
import { fetcher } from "@/lib/api";
import { useRepo } from "@/context/RepoContext";
import { duration, easing } from "@/lib/motion";
import type { ApiOkEnvelope, TensorData, TensorEntry } from "@/lib/api-types";
import { EvidencePhaseBadge } from "@/components/ui/evidence-phase-badge";
import {
  OmegaHeatmap,
  type OmegaCellSelection,
} from "@/components/tensor/omega-heatmap";
import { OmegaCellDetail } from "@/components/tensor/omega-cell-detail";
import { CommutativityTable } from "@/components/tensor/commutativity-table";
import { MergeRiskCard } from "@/components/tensor/merge-risk-card";

function lookupEntry(
  entries: TensorEntry[],
  sel: OmegaCellSelection | null
): TensorEntry | null {
  if (!sel) return null;
  for (const e of entries) {
    if (
      (e.i === sel.i && e.j === sel.j) ||
      (e.i === sel.j && e.j === sel.i)
    ) {
      return e;
    }
  }
  return null;
}

export default function TensorPage() {
  const { refName, selectedBranches } = useRepo();
  const reduceMotion = useReducedMotion();
  const [selected, setSelected] = useState<OmegaCellSelection | null>(null);
  const [includeRemotes, setIncludeRemotes] = useState<boolean>(false);

  const branchesParam =
    selectedBranches.length > 0
      ? `&branches=${encodeURIComponent(selectedBranches.join(","))}`
      : "";

  const tensorQuery = useQuery({
    queryKey: ["tensor", refName, selectedBranches, includeRemotes],
    queryFn: () =>
      fetcher<ApiOkEnvelope<TensorData>>(
        `/v1/tensor?ref=${encodeURIComponent(refName)}${branchesParam}${
          includeRemotes ? "&include_remotes=true" : ""
        }`
      ),
    staleTime: 5000,
    placeholderData: (prev) => prev,
  });

  const data = tensorQuery.data?.data;
  const selectedEntry = useMemo(() => {
    const entries = data?.entries ?? [];
    return lookupEntry(entries, selected);
  }, [data?.entries, selected]);

  const isEmpty =
    data &&
    (data.entries.length === 0 ||
      Boolean(data.message) ||
      (data.branches.length <= 1 && data.merge_risk === 0));

  return (
    <motion.div
      initial={reduceMotion ? undefined : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={
        reduceMotion
          ? { duration: 0 }
          : { duration: duration.page / 1000, ease: easing.easeOut }
      }
      className="flex flex-col min-h-full space-y-6"
    >
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-border">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <GitMerge className="w-6 h-6 text-accent" aria-hidden="true" />
            <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-text">
              Conflict Tensor
            </h1>
            <EvidencePhaseBadge phase="deterministic" />
          </div>
          <p className="text-sm text-textMuted mt-1">
            Flat pairwise Ω<sub>ij</sub> collision matrix across concurrent branches vs attractor{" "}
            <span className="font-mono text-accent">{refName}</span>.
          </p>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          {/* Branch Scope Toggle */}
          <div className="flex items-center rounded-lg border border-border bg-surfaceGlass p-0.5 text-xs font-mono">
            <button
              type="button"
              onClick={() => setIncludeRemotes(false)}
              className={`px-2.5 py-1 rounded-md transition-colors ${
                !includeRemotes
                  ? "bg-accent/20 text-accent font-semibold shadow-xs"
                  : "text-textMuted hover:text-text"
              }`}
            >
              Local Branches
            </button>
            <button
              type="button"
              onClick={() => setIncludeRemotes(true)}
              className={`px-2.5 py-1 rounded-md transition-colors ${
                includeRemotes
                  ? "bg-accent/20 text-accent font-semibold shadow-xs"
                  : "text-textMuted hover:text-text"
              }`}
            >
              + Remotes &amp; PRs
            </button>
          </div>

          <button
            type="button"
            onClick={() => tensorQuery.refetch()}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-border text-sm text-textMuted hover:bg-surfaceElevated focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            <RefreshCw className="w-4 h-4" aria-hidden="true" />
            Refresh
          </button>
        </div>
      </div>

      {tensorQuery.isLoading && (
        <p className="text-sm text-textMuted" role="status">
          Loading flat Ω matrix…
        </p>
      )}

      {tensorQuery.isError && (
        <div
          className="rounded-xl border border-danger/40 bg-danger/10 p-5"
          role="alert"
        >
          <p className="text-sm font-semibold text-danger">
            Failed to load conflict tensor
          </p>
          <p className="text-xs text-textMuted mt-1">
            {(tensorQuery.error as Error)?.message ||
              "Check gdss serve and GET /v1/tensor"}
          </p>
        </div>
      )}

      {data && isEmpty && (
        <div className="rounded-xl border border-border bg-surfaceGlass p-6 space-y-3">
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded text-xs font-mono font-semibold uppercase tracking-wider bg-accent/15 text-accent border border-accent/40">
              Single Branch Mode
            </span>
            <p className="text-sm font-semibold text-text">
              No concurrent pairwise collisions detected
            </p>
          </div>
          <p className="text-sm text-textMuted leading-relaxed">
            The Conflict Tensor computes pairwise interference (Ω<sub>ij</sub>) between{" "}
            <strong>multiple concurrent pull requests or feature branches</strong> before they merge into{" "}
            <span className="font-mono text-accent">{refName}</span>. With only one feature branch active,
            there are no cross-PR collisions to evaluate.
          </p>
          <div className="p-3 rounded-lg bg-surface/60 border border-border/60 text-xs font-mono text-textSubtle space-y-1">
            <p className="text-text font-semibold">Pro Tips:</p>
            <p>• Switch to &quot;+ Remotes &amp; PRs&quot; above to include remote tracking branches in the matrix.</p>
            <p>• Run <code className="text-accent">git fetch origin</code> to fetch colleagues&apos; active PR branches.</p>
            <p>• Check <Link href="/drift" className="text-accent underline">Drift Monitor</Link> to inspect single-branch drift against the attractor.</p>
          </div>
        </div>
      )}

      {data && !tensorQuery.isLoading && (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-1">
              <MergeRiskCard
                mergeRisk={data.merge_risk}
                reference={data.reference}
              />
            </div>
            <div className="lg:col-span-2">
              <OmegaCellDetail
                i={selected?.i ?? null}
                j={selected?.j ?? null}
                omega={
                  selected
                    ? (selectedEntry?.omega ?? 0)
                    : null
                }
                reasons={selectedEntry?.reasons ?? []}
              />
            </div>
          </div>

          {!isEmpty && (
            <OmegaHeatmap
              branches={data.branches}
              entries={data.entries}
              selected={selected}
              onSelect={setSelected}
            />
          )}

          <CommutativityTable pairs={data.commutativity} />

          <footer className="text-[11px] text-textMuted border-t border-border pt-4 space-y-1">
            <p>
              Honesty: this is the <strong>flat</strong> pairwise marginal from
              operator overlap + interference (diagonal = drift self-energy).
              Geometric form is phase 4a–c.
            </p>
            <p>GDSS never auto-merges — it predicts and surfaces risk only.</p>
          </footer>
        </>
      )}
    </motion.div>
  );
}
