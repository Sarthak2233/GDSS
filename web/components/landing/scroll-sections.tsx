"use client";

import { motion, useReducedMotion } from "framer-motion";
import { GitCommit, ShieldAlert, GitMerge, Terminal, Cloud, Server, ChevronRight } from "lucide-react";
import { duration, easing } from "@/lib/motion";
import { colors } from "@/lib/tokens";

export function ScrollSections() {
  const reduced = useReducedMotion();

  const sec = (ms: number) => ms / 1000;

  const cardVariants = {
    hidden: { opacity: 0, y: reduced ? 0 : 20 },
    show: {
      opacity: 1,
      y: 0,
      transition: { duration: sec(duration.primary), ease: easing.easeOut },
    },
  };

  return (
    <div className="space-y-16 py-12 max-w-5xl mx-auto px-4 relative z-content" data-testid="scroll-sections">
      {/* Section 1: The Vision / Problem */}
      <section className="p-8 rounded-2xl bg-surfaceGlass backdrop-blur-md border border-border shadow-xl">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-warning/10 text-warning text-xs font-semibold uppercase">
              Semantic Intelligence
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-text">
              Git Sees Lines. <br />
              <span className="text-accent">GDSS Sees Geometry.</span>
            </h2>
            <p className="text-sm text-textMuted leading-relaxed">
              Traditional merge tools only compare line offsets and text regions. GDSS treats a branch as a trajectory γ_i(t) on a semantic manifold M. Merging is non-commutative transformation algebra.
            </p>
          </div>
          <div className="p-6 rounded-xl bg-surfaceElevated border border-border font-mono text-xs text-textMuted space-y-3 shadow-inner">
            <div className="flex items-center gap-2 text-accent font-semibold border-b border-border pb-2">
              <Terminal className="h-4 w-4" />
              <span>Semantic Manifold Differential</span>
            </div>
            <div className="space-y-1.5 leading-relaxed text-[11px]">
              <p><span className="text-textSubtle">1. Attractor State D(t):</span> Reference dev branch</p>
              <p><span className="text-textSubtle">2. Branch Trajectory:</span> γ_i(t) = B_i(t) − D(t)</p>
              <p><span className="text-textSubtle">3. Conflict Tensor:</span> Ω_ij = [T_i, T_j] ≠ 0</p>
              <p><span className="text-trajectory">4. Geodesic Path:</span> Deterministic convergence</p>
            </div>
          </div>
        </div>
      </section>

      {/* Section 2: Core Mathematics */}
      <section className="space-y-6">
        <div className="text-center space-y-2">
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-text">
            Architectural Mathematics
          </h2>
          <p className="text-sm text-textMuted max-w-xl mx-auto">
            Three foundational pillars for continuous branch alignment.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <motion.div
            variants={cardVariants}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, margin: "-40px" }}
            className="p-6 rounded-xl bg-surface border border-border flex flex-col gap-3 shadow-md"
          >
            <div className="p-3 rounded-lg w-fit" style={{ backgroundColor: "rgba(124, 92, 255, 0.15)", color: colors.accent }}>
              <GitCommit className="h-5 w-5" />
            </div>
            <h3 className="text-lg font-semibold text-text">Tangent Vectors</h3>
            <p className="text-xs text-textMuted leading-relaxed">
              Every commit dC acts as a tangent transformation vector modifying the manifold state.
            </p>
          </motion.div>

          <motion.div
            variants={cardVariants}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, margin: "-40px" }}
            className="p-6 rounded-xl bg-surface border border-border flex flex-col gap-3 shadow-md"
          >
            <div className="p-3 rounded-lg w-fit" style={{ backgroundColor: "rgba(255, 107, 107, 0.15)", color: colors.conflict }}>
              <ShieldAlert className="h-5 w-5" />
            </div>
            <h3 className="text-lg font-semibold text-text">Conflict Tensor Ω</h3>
            <p className="text-xs text-textMuted leading-relaxed">
              Measures non-commutativity between branch operations before git merge is attempted.
            </p>
          </motion.div>

          <motion.div
            variants={cardVariants}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, margin: "-40px" }}
            className="p-6 rounded-xl bg-surface border border-border flex flex-col gap-3 shadow-md"
          >
            <div className="p-3 rounded-lg w-fit" style={{ backgroundColor: "rgba(61, 220, 151, 0.15)", color: colors.trajectory }}>
              <GitMerge className="h-5 w-5" />
            </div>
            <h3 className="text-lg font-semibold text-text">Geodesic Paths</h3>
            <p className="text-xs text-textMuted leading-relaxed">
              Finds the shortest semantic convergence path between active developer branches.
            </p>
          </motion.div>
        </div>
      </section>

      {/* Section 3: Deployment Tiers */}
      <section className="p-8 rounded-2xl bg-surfaceGlass backdrop-blur-md border border-border shadow-xl space-y-6">
        <div className="text-center space-y-2">
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-text">
            Three Deployment Tiers
          </h2>
          <p className="text-sm text-textMuted max-w-xl mx-auto">
            From local developer CLI to self-hosted enterprise appliances.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-5 rounded-xl bg-surfaceElevated/60 border border-border space-y-2">
            <div className="flex items-center justify-between text-accent font-semibold text-sm">
              <span className="flex items-center gap-2"><Terminal className="h-4 w-4" /> 1. Local CLI</span>
              <ChevronRight className="h-4 w-4" />
            </div>
            <p className="text-xs text-textMuted leading-relaxed">
              Parser, AST symbol extractor, and drift monitor. Runs completely offline on dev machines.
            </p>
          </div>

          <div className="p-5 rounded-xl bg-surfaceElevated/60 border border-border space-y-2">
            <div className="flex items-center justify-between text-merge font-semibold text-sm">
              <span className="flex items-center gap-2"><Cloud className="h-4 w-4" /> 2. Hybrid SaaS</span>
              <ChevronRight className="h-4 w-4" />
            </div>
            <p className="text-xs text-textMuted leading-relaxed">
              Aggregates metadata for org-wide analytics, dashboards, and real-time conflict alerts.
            </p>
          </div>

          <div className="p-5 rounded-xl bg-surfaceElevated/60 border border-border space-y-2">
            <div className="flex items-center justify-between text-trajectory font-semibold text-sm">
              <span className="flex items-center gap-2"><Server className="h-4 w-4" /> 3. Enterprise</span>
              <ChevronRight className="h-4 w-4" />
            </div>
            <p className="text-xs text-textMuted leading-relaxed">
              Turnkey self-hosted appliance for absolute data sovereignty (SOC2 / GDPR ready).
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
