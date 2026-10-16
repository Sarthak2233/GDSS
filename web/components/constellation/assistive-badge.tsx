"use client";

import React from "react";
import { Zap, HelpCircle } from "lucide-react";
import { colors } from "@/lib/tokens";

export function AssistiveBadge() {
  return (
    <div
      className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-border/80 bg-surfaceGlass/80 backdrop-blur-md shadow-sm text-xs font-medium text-textMuted group relative"
      role="note"
      aria-label="Assistive Probabilistic Notice"
    >
      <span className="flex items-center gap-1.5 text-accent font-semibold">
        <Zap className="w-3.5 h-3.5 text-warning fill-warning/20" />
        Assistive · Probabilistic
      </span>
      <span className="text-border">|</span>
      <span className="text-textSubtle flex items-center gap-1">
        Embedding approx.
        <span className="sr-only">
          Similarity results are based on embedding approximations, not structural equivalence. Use as guidance, not as ground truth.
        </span>
        <span
          className="inline-flex cursor-help text-textMuted hover:text-text transition-colors"
          title="Similarity results are based on embedding approximations, not structural equivalence. Use as guidance, not as ground truth."
        >
          <HelpCircle className="w-3.5 h-3.5" />
        </span>
      </span>
    </div>
  );
}
