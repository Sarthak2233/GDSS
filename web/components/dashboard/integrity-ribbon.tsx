"use client";

import React from "react";
import { motion, useReducedMotion } from "framer-motion";
import { duration, easing } from "@/lib/motion";
import { ShieldCheck, ShieldAlert, Activity } from "lucide-react";

export interface IntegrityRibbonProps {
  repoPath: string;
  referenceBranch: string;
  isHealthy?: boolean;
  timestamp?: string;
  isLoading?: boolean;
  error?: string | null;
}

export function IntegrityRibbon({
  repoPath,
  referenceBranch,
  isHealthy = true,
  timestamp,
  isLoading = false,
  error = null,
}: IntegrityRibbonProps) {
  const reduceMotion = useReducedMotion();

  if (isLoading) {
    return (
      <div
        className="rounded-xl border border-border bg-surface p-4 flex items-center justify-between animate-pulse"
        data-testid="integrity-ribbon-skeleton"
      >
        <div className="h-6 w-40 bg-surfaceElevated rounded" />
        <div className="h-4 w-60 bg-surfaceElevated rounded" />
        <div className="h-4 w-28 bg-surfaceElevated rounded" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-danger/30 bg-danger/10 p-4 flex items-center justify-between text-xs text-danger">
        <div className="flex items-center gap-2">
          <ShieldAlert className="h-4 w-4 shrink-0" />
          <span className="font-semibold">{error}</span>
        </div>
        <span className="text-textMuted">Check git repository state</span>
      </div>
    );
  }

  return (
    <motion.aside
      className="rounded-xl border border-border bg-surfaceElevated/60 p-4 shadow-sm flex flex-wrap items-center justify-between gap-4 text-xs"
      initial={reduceMotion ? undefined : { opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={
        reduceMotion
          ? { duration: 0 }
          : { duration: duration.primary / 1000, ease: easing.easeOut }
      }
      data-testid="integrity-ribbon"
    >
      {/* Left: Integrity Status Badge */}
      <div className="flex items-center gap-2">
        {isHealthy ? (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-success/30 bg-success/15 px-3 py-1 font-bold tracking-wider text-success uppercase">
            <ShieldCheck className="h-3.5 w-3.5" />
            REPO INTEGRITY VERIFIED
          </span>
        ) : (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-danger/30 bg-danger/15 px-3 py-1 font-bold tracking-wider text-danger uppercase">
            <ShieldAlert className="h-3.5 w-3.5" />
            INTEGRITY DEGRADED
          </span>
        )}
      </div>

      {/* Center: Workspace Details */}
      <div className="flex items-center gap-4 text-textMuted">
        <div className="flex items-center gap-1.5">
          <span>Path:</span>
          <span className="font-mono text-text font-semibold truncate max-w-[240px]">
            {repoPath}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <span>Attractor Ref:</span>
          <span className="font-mono text-text font-semibold">
            {referenceBranch}
          </span>
        </div>
        {timestamp && (
          <div className="hidden md:flex items-center gap-1.5">
            <span>Last Sync:</span>
            <span className="text-textSubtle">{timestamp}</span>
          </div>
        )}
      </div>

      {/* Right: Git Observer Beacon */}
      <div className="flex items-center gap-2">
        <span className="relative flex h-2.5 w-2.5">
          {!reduceMotion && (
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75" />
          )}
          <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-accent" />
        </span>
        <span className="font-medium text-text">Git Observer active</span>
      </div>
    </motion.aside>
  );
}
