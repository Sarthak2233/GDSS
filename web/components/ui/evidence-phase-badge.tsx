"use client";

import type { EvidencePhase } from "@/lib/api-types";

const LABELS: Record<EvidencePhase, string> = {
  deterministic: "Deterministic (phase 1–3)",
  "assistive-heuristic": "Assistive heuristic (phase 3 flat)",
  "not-available": "Not yet available (phase 4+)",
};

const STYLES: Record<EvidencePhase, string> = {
  deterministic: "bg-success/10 text-success border-success/30",
  "assistive-heuristic": "bg-warning/10 text-warning border-warning/30",
  "not-available": "bg-danger/10 text-danger border-danger/30",
};

export interface EvidencePhaseBadgeProps {
  phase: EvidencePhase;
  className?: string;
}

/**
 * Labels the evidence source of a metric so UI claims match backend capability.
 */
export function EvidencePhaseBadge({
  phase,
  className = "",
}: EvidencePhaseBadgeProps) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wide border ${STYLES[phase]} ${className}`}
      data-testid="evidence-phase-badge"
      data-phase={phase}
    >
      {LABELS[phase]}
    </span>
  );
}
