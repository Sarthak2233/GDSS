"use client";

import React from "react";
import { motion, useReducedMotion } from "framer-motion";
import { duration, easing } from "@/lib/motion";
import { colors } from "@/lib/tokens";

export interface DriftErrorStateProps {
  error?: string | null;
  onRetry?: () => void;
}

export function DriftErrorState({
  error = "Failed to fetch drift metadata",
  onRetry,
}: DriftErrorStateProps) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      initial={reduceMotion ? undefined : { opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={
        reduceMotion
          ? { duration: 0 }
          : { duration: duration.primary / 1000, ease: easing.easeOut }
      }
      className="flex flex-col gap-3 p-6 rounded-xl border border-border bg-surfaceGlass"
      role="alert"
      aria-live="polite"
    >
      <div className="flex items-center gap-2">
        <span
          className="w-2.5 h-2.5 rounded-full shrink-0"
          style={{ backgroundColor: colors.danger }}
          aria-hidden="true"
        />
        <h2 className="text-base font-semibold text-text">
          WHAT: Drift Monitor unavailable
        </h2>
      </div>

      <p className="text-sm text-textMuted pl-4">
        <strong className="text-text">WHY:</strong> {error || "The local GDSS API did not respond with valid drift telemetry."}
      </p>

      <div className="flex items-center justify-between pl-4 pt-1">
        <p className="text-sm text-textSubtle">
          <strong className="text-text">FIX:</strong> Ensure <code className="px-1.5 py-0.5 rounded bg-surface border border-border">gdss serve</code> is running on port 8787 or check repository path.
        </p>

        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="px-3 py-1.5 text-xs font-medium rounded-md border border-border hover:border-borderStrong bg-surfaceElevated text-text transition-colors"
          >
            Retry
          </button>
        )}
      </div>
    </motion.div>
  );
}
