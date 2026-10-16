"use client";

import React from "react";
import { motion, useReducedMotion } from "framer-motion";
import { duration, easing } from "@/lib/motion";
import { colors } from "@/lib/tokens";

export function DriftEmptyState() {
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      initial={reduceMotion ? undefined : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={
        reduceMotion
          ? { duration: 0 }
          : { duration: duration.primary / 1000, ease: easing.easeOut }
      }
      className="flex flex-col items-center justify-center p-10 text-center rounded-xl border border-border bg-surfaceGlass backdrop-blur-md gap-3"
      role="region"
      aria-label="No drift detected"
    >
      <div className="relative w-20 h-20 flex items-center justify-center mb-2">
        <svg
          viewBox="0 0 100 100"
          className="w-full h-full"
          aria-hidden="true"
        >
          {/* Outer Potential Ring */}
          <circle
            cx="50"
            cy="50"
            r="42"
            fill="none"
            stroke={colors.success}
            strokeWidth="1.5"
            strokeDasharray="4 4"
            opacity="0.4"
          />
          <circle
            cx="50"
            cy="50"
            r="28"
            fill="none"
            stroke={colors.success}
            strokeWidth="2"
            opacity="0.6"
          />
          <circle
            cx="50"
            cy="50"
            r="16"
            fill={colors.success}
            opacity="0.2"
          />
          <circle
            cx="50"
            cy="50"
            r="5"
            fill={colors.success}
          />
        </svg>

        <div className="absolute -top-1 right-0 px-2 py-0.5 rounded bg-success/20 border border-success/40 text-[10px] font-mono text-success font-semibold shadow-sm">
          [T_i, T_j] = 0
        </div>
      </div>

      <div className="flex items-center gap-2">
        <span
          className="px-2.5 py-0.5 rounded text-xs font-mono font-semibold uppercase tracking-wider border"
          style={{
            color: colors.success,
            borderColor: `${colors.success}50`,
            backgroundColor: `${colors.success}15`,
          }}
        >
          Commutative Equilibrium
        </span>
      </div>

      <h2 className="text-base font-semibold text-text">
        Repository geometry is stable around the attractor
      </h2>
      <p className="text-xs text-textMuted max-w-md font-mono">
        All local branch transformations commute cleanly with the reference attractor. No semantic conflict tensor alerts detected across active trajectories.
      </p>
    </motion.div>
  );
}
