"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { motion, useReducedMotion } from "framer-motion";
import { GitCommit, RefreshCw } from "lucide-react";
import { fetcher } from "@/lib/api";
import { duration, easing } from "@/lib/motion";
import type { ApiOkEnvelope, LogCommit } from "@/lib/api-types";
import { EvidencePhaseBadge } from "@/components/ui/evidence-phase-badge";

export default function LogPage() {
  const reduceMotion = useReducedMotion();

  const logQuery = useQuery({
    queryKey: ["log"],
    queryFn: () =>
      fetcher<ApiOkEnvelope<LogCommit[]>>("/v1/log?n=30"),
    staleTime: 10_000,
  });

  const commits = logQuery.data?.data || [];

  return (
    <motion.div
      initial={reduceMotion ? undefined : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={
        reduceMotion
          ? { duration: 0 }
          : { duration: duration.page / 1000, ease: easing.easeOut }
      }
      className="flex flex-col h-full space-y-6"
      data-testid="semantic-log-page"
    >
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-border">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <GitCommit className="w-6 h-6 text-accent" aria-hidden="true" />
            <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-text">
              Semantic Log
            </h1>
            <EvidencePhaseBadge phase="deterministic" />
          </div>
          <p className="text-sm text-textMuted mt-1 max-w-2xl">
            Each commit is a tangent vector dC on the manifold. Operators are
            SemanticOperators T<sub>i</sub> extracted from parent→tip diffs.
            Metadata only — no commit messages or author PII.
          </p>
        </div>
        <button
          type="button"
          onClick={() => logQuery.refetch()}
          aria-label="Refresh semantic log"
          className="p-2 rounded-lg border border-border bg-surface hover:bg-surfaceElevated text-textMuted hover:text-text transition-colors"
        >
          <RefreshCw
            className={`w-4 h-4 ${logQuery.isLoading ? "animate-spin text-accent" : ""}`}
          />
        </button>
      </div>

      {logQuery.isError && (
        <div className="rounded-xl border border-danger/30 bg-danger/10 p-4 text-sm text-danger">
          <p className="font-semibold">WHAT: Failed to load /v1/log</p>
          <p className="text-xs text-textMuted mt-1">
            WHY: Local API may be down. FIX: run{" "}
            <code className="font-mono">gdss serve --repo PATH</code> and retry.
          </p>
        </div>
      )}

      {logQuery.isLoading && (
        <div
          className="h-64 rounded-xl border border-border bg-surfaceGlass animate-pulse"
          aria-busy="true"
        />
      )}

      {!logQuery.isLoading && !logQuery.isError && commits.length === 0 && (
        <div className="rounded-xl border border-border bg-surface p-8 text-center text-textMuted">
          <p className="font-semibold text-text">No commits in trajectory</p>
          <p className="text-sm mt-1">
            Analyze a repository with history to see semantic operators per
            commit.
          </p>
        </div>
      )}

      {!logQuery.isLoading && commits.length > 0 && (
        <ol className="flex flex-col gap-3" aria-label="Semantic commit timeline">
          {commits.map((c) => (
            <li
              key={c.sha}
              className="rounded-xl border border-border bg-surface p-4 shadow-sm"
            >
              <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                <span className="font-mono text-sm text-accent">{c.sha.slice(0, 8)}</span>
                <span className="text-xs text-textSubtle tabular-nums">
                  {c.timestamp}
                </span>
              </div>
              {c.operators.length === 0 ? (
                <p className="text-xs text-textMuted">No semantic operators</p>
              ) : (
                <ul className="space-y-1">
                  {c.operators.map((op, idx) => (
                    <li
                      key={`${c.sha}-${idx}`}
                      className="text-xs font-mono text-text flex flex-wrap gap-2"
                    >
                      <span className="text-accent font-semibold">{op.type}</span>
                      <span className="text-textMuted">{op.file}</span>
                      {op.name && <span className="text-text">{op.name}</span>}
                    </li>
                  ))}
                </ul>
              )}
            </li>
          ))}
        </ol>
      )}
    </motion.div>
  );
}
