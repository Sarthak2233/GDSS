"use client";

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { motion, useReducedMotion, AnimatePresence } from "framer-motion";
import { Activity, RefreshCw, BookOpen, ChevronDown, ChevronUp } from "lucide-react";
import { fetcher } from "@/lib/api";
import { useRepo } from "@/context/RepoContext";
import { duration, easing } from "@/lib/motion";
import type {
  ApiOkEnvelope,
  DriftAlertItem,
  DriftData,
} from "@/lib/api-types";
import {
  DriftTimelineChart,
  DriftBranchData,
} from "@/components/drift/drift-timeline-chart";
import {
  SeverityAlertsMatrix,
} from "@/components/drift/severity-alerts-matrix";
import {
  DriftManifoldRadar,
} from "@/components/drift/drift-manifold-radar";
import { DriftErrorState } from "@/components/drift/drift-error-state";
import { DriftEmptyState } from "@/components/drift/drift-empty-state";
import { EvidencePhaseBadge } from "@/components/ui/evidence-phase-badge";

export default function DriftPage() {
  const { refName, selectedBranches } = useRepo();
  const router = useRouter();
  const reduceMotion = useReducedMotion();

  const [selectedBranch, setSelectedBranch] = useState<string | undefined>(
    undefined
  );
  const [showManifoldGuide, setShowManifoldGuide] = useState<boolean>(false);

  const branchesParam =
    selectedBranches.length > 0
      ? `&branches=${encodeURIComponent(selectedBranches.join(","))}`
      : "";

  const driftQuery = useQuery({
    queryKey: ["drift", refName, selectedBranches],
    queryFn: () =>
      fetcher<ApiOkEnvelope<DriftData>>(
        `/v1/drift?ref=${encodeURIComponent(refName)}${branchesParam}`
      ),
    staleTime: 5000,
    placeholderData: (prev) => prev,
  });

  const alertsQuery = useQuery({
    queryKey: ["alerts", refName],
    queryFn: () =>
      fetcher<ApiOkEnvelope<DriftAlertItem[]>>(
        `/v1/alerts?ref=${encodeURIComponent(refName)}`
      ),
    staleTime: 5000,
    placeholderData: (prev) => prev,
  });

  const isLoading = driftQuery.isLoading || alertsQuery.isLoading;
  const isError = driftQuery.isError || alertsQuery.isError;
  const errorMessage =
    (driftQuery.error as Error)?.message ||
    (alertsQuery.error as Error)?.message ||
    "Failed to fetch drift or alert telemetry from local API.";

  const handleSelectSymbol = (symbolId: string) => {
    router.push(`/graph?symbol=${encodeURIComponent(symbolId)}`);
  };

  const handleRefresh = () => {
    driftQuery.refetch();
    alertsQuery.refetch();
  };

  const branchesData: DriftBranchData[] = React.useMemo(() => {
    if (!driftQuery.data?.data?.drift) return [];
    return driftQuery.data.data.drift.map((b) => ({
      branch: b.branch,
      magnitude: b.magnitude,
      tip_distance: b.tip_distance,
      trajectory_integral: b.trajectory_integral,
      velocity: b.velocity,
      convergence_score: b.convergence_score,
      convergence: b.convergence_label,
      affected: b.affected || [],
      history: b.history || [],
    }));
  }, [driftQuery.data]);

  const alertsData: DriftAlertItem[] = React.useMemo(() => {
    if (!alertsQuery.data?.data) return [];
    return alertsQuery.data.data;
  }, [alertsQuery.data]);

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
            <Activity
              className="w-6 h-6 text-accent"
              aria-hidden="true"
            />
            <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-text">
              Drift Monitor
            </h1>
            <EvidencePhaseBadge phase="deterministic" />
          </div>
          <p className="text-sm text-textMuted mt-1">
            Semantic branch drift I(B<sub>i</sub>) and severity-bucketed alerts
            against reference{" "}
            <span className="font-mono text-accent">{refName}</span>.
            Convergence labels come from velocity sign; scores are floats in
            [0, 1].
          </p>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-border bg-surfaceGlass text-xs font-mono">
            <span className="text-textSubtle">Reference Attractor:</span>
            <strong className="text-accent">{refName}</strong>
          </div>

          <button
            type="button"
            onClick={handleRefresh}
            aria-label="Refresh drift telemetry"
            className="p-2 rounded-lg border border-border bg-surface hover:bg-surfaceElevated text-textMuted hover:text-text transition-colors"
          >
            <RefreshCw
              className={`w-4 h-4 ${isLoading ? "animate-spin text-accent" : ""}`}
            />
          </button>
        </div>
      </div>

      <div className="flex flex-col rounded-xl border border-border/80 bg-surfaceGlass overflow-hidden">
        <button
          type="button"
          onClick={() => setShowManifoldGuide((prev) => !prev)}
          aria-expanded={showManifoldGuide}
          className="w-full flex items-center justify-between p-4 text-left hover:bg-surface/50 transition-colors"
        >
          <div className="flex items-center gap-2.5">
            <BookOpen className="w-4 h-4 text-accent" aria-hidden="true" />
            <span className="text-sm font-semibold text-text">
              How to read this Manifold (Geodesic Mathematics)
            </span>
          </div>
          <div className="flex items-center gap-2 text-xs text-textMuted font-mono">
            <span>{showManifoldGuide ? "Hide Guide" : "Show Guide"}</span>
            {showManifoldGuide ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </div>
        </button>

        <AnimatePresence>
          {showManifoldGuide && (
            <motion.div
              initial={reduceMotion ? undefined : { height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={reduceMotion ? undefined : { height: 0, opacity: 0 }}
              transition={{ duration: duration.secondary / 1000, ease: easing.easeInOut }}
              className="border-t border-border/60 bg-surface/40 p-5 text-xs text-textMuted space-y-3 font-mono leading-relaxed"
            >
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="p-3 rounded bg-surface/80 border border-border/60">
                  <div className="font-semibold text-text mb-1">
                    Attractor R (Canonical Base)
                  </div>
                  <p>
                    The reference branch (e.g.{" "}
                    <span className="text-accent">{refName}</span>) is the
                    attractor. Magnitude I(B) = α·d_tip + β·I_traj.
                  </p>
                </div>
                <div className="p-3 rounded bg-surface/80 border border-border/60">
                  <div className="font-semibold text-text mb-1">
                    Tip vs trajectory (d_tip vs I_traj)
                  </div>
                  <p>
                    d_tip is embedding cosine distance between tips;
                    I_traj is cumulative AST transforms along merge_base..tip.
                  </p>
                </div>
                <div className="p-3 rounded bg-surface/80 border border-border/60">
                  <div className="font-semibold text-text mb-1">
                    Velocity v = ΔI/Δt
                  </div>
                  <p>
                    v &le; 0: converging toward attractor; v &gt; 0: diverging.
                    Convergence score clamped in [0, 1].
                  </p>
                </div>
                <div className="p-3 rounded bg-surface/80 border border-border/60">
                  <div className="font-semibold text-text mb-1">
                    Collision Tensor Ω<sub>ij</sub>
                  </div>
                  <p>
                    Drift measures 1-to-base divergence. Pairwise branch-to-branch
                    collisions [T_i, T_j] are tracked in Conflict Tensor.
                  </p>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {isError && (
        <DriftErrorState
          error={errorMessage}
          onRetry={handleRefresh}
        />
      )}

      {isLoading && !isError && (
        <div className="flex flex-col gap-6" aria-busy="true">
          <div className="h-64 w-full rounded-xl border border-border bg-surfaceGlass p-6 flex flex-col justify-between animate-pulse">
            <div className="flex justify-between items-center">
              <div className="h-5 w-48 bg-surfaceElevated rounded" />
              <div className="h-4 w-32 bg-surfaceElevated rounded" />
            </div>
            <div className="flex items-center justify-center">
              <div className="w-36 h-36 rounded-full border-2 border-dashed border-border flex items-center justify-center text-xs text-textMuted font-mono">
                Computing trajectory vectors...
              </div>
            </div>
            <div className="h-4 w-64 bg-surfaceElevated rounded" />
          </div>
          <div className="h-80 w-full rounded-xl border border-border bg-surfaceGlass p-6 flex flex-col gap-4 animate-pulse">
            <div className="h-5 w-56 bg-surfaceElevated rounded" />
            <div className="h-10 w-full bg-surfaceElevated rounded" />
            <div className="h-16 w-full bg-surfaceElevated rounded" />
            <div className="h-16 w-full bg-surfaceElevated rounded" />
          </div>
        </div>
      )}

      {!isLoading && !isError && (
        <>
          {branchesData.length === 0 && alertsData.length === 0 ? (
            <DriftEmptyState />
          ) : (
            <div className="flex flex-col gap-8">
              <DriftManifoldRadar
                branches={branchesData}
                referenceBranch={refName}
                selectedBranch={selectedBranch}
                onSelectBranch={(branch) =>
                  setSelectedBranch((prev) => (prev === branch ? undefined : branch))
                }
                onSelectSymbol={handleSelectSymbol}
              />

              <DriftTimelineChart
                branches={branchesData}
                referenceBranch={refName}
                selectedBranch={selectedBranch}
                onSelectBranch={(branch) =>
                  setSelectedBranch((prev) => (prev === branch ? undefined : branch))
                }
                onSelectSymbol={handleSelectSymbol}
              />

              <SeverityAlertsMatrix
                alerts={alertsData}
                selectedBranch={selectedBranch === "ALL" ? undefined : selectedBranch}
                onSelectBranch={(branch) =>
                  setSelectedBranch((prev) => (prev === branch ? undefined : branch))
                }
                onSelectSymbol={handleSelectSymbol}
              />
            </div>
          )}
        </>
      )}
    </motion.div>
  );
}
