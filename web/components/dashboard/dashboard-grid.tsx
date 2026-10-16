"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { fetcher } from "@/lib/api";
import { useRepo } from "@/context/RepoContext";
import type {
  ApiOkEnvelope,
  DriftData,
  StatusData,
} from "@/lib/api-types";
import { TrajectoryCard } from "@/components/dashboard/trajectory-card";
import { DriftAttractorCard } from "@/components/dashboard/drift-attractor-card";
import {
  ConflictTreeCard,
  OperatorSummary,
} from "@/components/dashboard/conflict-tree-card";
import { ConflictRiskCard } from "@/components/dashboard/resolution-probability-card";
import { GlobalHealthDialCard } from "@/components/dashboard/global-health-dial-card";
import { IntegrityRibbon } from "@/components/dashboard/integrity-ribbon";
import { EvidencePhaseBadge } from "@/components/ui/evidence-phase-badge";

export function DashboardGrid() {
  const { repo, refName } = useRepo();

  const statusQuery = useQuery({
    queryKey: ["status", refName],
    queryFn: () =>
      fetcher<ApiOkEnvelope<StatusData>>(
        `/v1/status?ref=${encodeURIComponent(refName)}`
      ),
    refetchInterval: 10000,
  });

  const driftQuery = useQuery({
    queryKey: ["drift", refName],
    queryFn: () =>
      fetcher<ApiOkEnvelope<DriftData>>(
        `/v1/drift?ref=${encodeURIComponent(refName)}`
      ),
    refetchInterval: 10000,
  });

  const isLoading = statusQuery.isLoading || driftQuery.isLoading;
  const statusError = statusQuery.error
    ? "Failed to load repository status"
    : null;
  const driftError = driftQuery.error
    ? "Failed to load phase-space drift"
    : null;

  const statusData = statusQuery.data?.data;
  const driftData = driftQuery.data?.data;

  const activeBranch = statusData?.active_branch || "main";
  const referenceBranch = statusData?.reference || refName || "main";

  const committedOperators =
    (statusData?.committed_operators as OperatorSummary[]) || [];
  const uncommittedOperators =
    (statusData?.uncommitted_operators as OperatorSummary[]) || [];
  const branches = driftData?.drift || [];

  const dangerOps = [...committedOperators, ...uncommittedOperators].filter(
    (o) =>
      o.type.includes("signature") ||
      o.type.includes("delete") ||
      o.type.includes("conflict")
  ).length;

  const maxDrift = branches.reduce((max, b) => Math.max(max, b.magnitude), 0);

  const maxConflict = branches.reduce(
    (best, b) => {
      const score = b.conflict_probability?.score ?? 0;
      if (score >= best.score) {
        return {
          score,
          reasons: b.conflict_probability?.reasons ?? [],
        };
      }
      return best;
    },
    { score: 0, reasons: [] as string[] }
  );

  const remoteSync = statusData?.remote_sync || {
    label: `origin/${referenceBranch}`,
    ahead: 0,
    behind: 0,
  };

  const attractorBranches = branches.map((b) => ({
    branch: b.branch,
    magnitude: b.magnitude,
    velocity: b.velocity,
    convergence: b.convergence_label,
    affected: b.affected,
    history: b.history,
  }));

  return (
    <div
      className="w-full flex-1 flex flex-col justify-between gap-6"
      data-testid="dashboard-grid"
    >
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 flex-1">
        <TrajectoryCard
          activeBranch={activeBranch}
          referenceBranch={referenceBranch}
          committedCount={committedOperators.length}
          uncommittedCount={uncommittedOperators.length}
          stabilityPercent={Math.max(
            0,
            Math.min(100, Number((100 - uncommittedOperators.length * 2.5).toFixed(1)))
          )}
          isLoading={statusQuery.isLoading}
          error={statusError}
        />

        <GlobalHealthDialCard
          maxDriftMagnitude={maxDrift}
          remoteSync={remoteSync}
          isLoading={isLoading}
          error={statusError || driftError}
        />

        <DriftAttractorCard
          referenceBranch={referenceBranch}
          branches={attractorBranches}
          isLoading={driftQuery.isLoading}
          error={driftError}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 flex-1">
        <ConflictTreeCard
          committedOperators={committedOperators}
          uncommittedOperators={uncommittedOperators}
          isLoading={statusQuery.isLoading}
          error={statusError}
        />

        <ConflictRiskCard
          conflictScore={maxConflict.score}
          reasons={maxConflict.reasons}
          branchCount={branches.length}
          isLoading={isLoading}
          error={statusError || driftError}
        />
      </div>

      <IntegrityRibbon
        repoPath={repo}
        referenceBranch={referenceBranch}
        isHealthy={!statusError && !driftError && dangerOps === 0}
        timestamp={new Date().toLocaleTimeString()}
        isLoading={isLoading}
        error={statusError || driftError}
      />

      <footer
        className="rounded-xl border border-border/80 bg-surfaceGlass p-4 text-xs text-textMuted space-y-2"
        data-testid="dashboard-honesty-footer"
      >
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-semibold text-text">What this shows</span>
          <EvidencePhaseBadge phase="deterministic" />
          <EvidencePhaseBadge phase="assistive-heuristic" />
        </div>
        <p>
          Trajectory operators, remote ahead/behind, and drift magnitude I(B
          <sub>i</sub>) are deterministic (phases 1–3). Conflict risk is the
          flat R<sup>m</sup> heuristic from{" "}
          <code className="text-textSubtle">ConflictProbabilityEstimator</code>
          — not the full Ω<sub>ij</sub> tensor (phase 4) and not auto-resolve /
          AI merge (phases 5–6).
        </p>
        <p className="text-textSubtle">
          See <span className="font-mono">docs/MANIFOLD_TENSOR_GUIDE.md</span>{" "}
          for the geometric caveat.
        </p>
      </footer>
    </div>
  );
}
