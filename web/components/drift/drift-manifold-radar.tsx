"use client";

import React, { useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { duration, easing } from "@/lib/motion";
import { colors } from "@/lib/tokens";

export interface DriftManifoldRadarProps {
  branches: {
    branch: string;
    magnitude: number;
    velocity: number;
    convergence: "converging" | "diverging" | string;
    affected: { id: string; name: string }[];
  }[];
  referenceBranch: string;
  selectedBranch?: string;
  onSelectBranch?: (branch: string) => void;
  onSelectSymbol?: (symbolId: string) => void;
}

export function DriftManifoldRadar({
  branches,
  referenceBranch,
  selectedBranch,
  onSelectBranch,
  onSelectSymbol,
}: DriftManifoldRadarProps) {
  const reduceMotion = useReducedMotion();
  const [hoveredBranch, setHoveredBranch] = useState<string | null>(null);

  const rings = [0.25, 0.5, 0.75, 1.0];

  // Helper to compute orbital coordinates for branches
  const getBranchPosition = (magnitude: number, index: number, total: number) => {
    const angleStep = (2 * Math.PI) / Math.max(1, total);
    const angle = index * angleStep - Math.PI / 2; // Start from top
    const radius = Math.min(1, Math.max(0.1, magnitude)) * 120; // Max 120px from origin (center 150, 150)
    return {
      x: 150 + radius * Math.cos(angle),
      y: 150 + radius * Math.sin(angle),
      angle,
    };
  };

  if (reduceMotion) {
    return (
      <div
        className="w-full rounded-xl border border-border bg-surfaceGlass p-6"
        role="region"
        aria-label="Geodesic orbital radar view"
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-base font-semibold text-text">
              Geodesic Orbital Radar
            </h2>
            <p className="text-xs text-textMuted mt-0.5">
              Reference Attractor: <span className="font-mono text-accent">{referenceBranch}</span>
            </p>
          </div>
        </div>

        <div className="flex flex-col gap-2" role="list">
          {branches.map((b) => (
            <div key={b.branch} role="listitem">
              <button
                type="button"
                onClick={() => onSelectBranch?.(b.branch)}
                className="w-full flex items-center justify-between p-3 rounded-lg border border-border bg-surface hover:border-accent text-left transition-colors"
              >
                <div>
                  <div className="font-mono text-sm font-medium text-text">
                    {b.branch}
                  </div>
                  <div className="text-xs text-textSubtle mt-0.5">
                    Magnitude: {(b.magnitude * 100).toFixed(0)}% · Velocity: {(b.velocity * 100).toFixed(1)}%
                  </div>
                </div>
                <span
                  className={`px-2 py-0.5 rounded text-[11px] font-mono uppercase ${
                    b.convergence === "converging"
                      ? "bg-success/15 text-success border border-success/40"
                      : "bg-warning/15 text-warning border border-warning/40"
                  }`}
                >
                  {b.convergence}
                </span>
              </button>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div
      className="w-full rounded-xl border border-border bg-surfaceGlass p-6 overflow-hidden relative"
      role="region"
      aria-label="Geodesic orbital radar view"
    >
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <h2 className="text-base font-semibold text-text">
            Geodesic Orbital Radar
          </h2>
          <p className="text-xs text-textMuted mt-0.5">
            Phase-plane visualization of branch trajectories <span className="font-mono italic">γ(t)</span> orbiting the reference attractor <span className="font-mono text-accent">{referenceBranch}</span>.
          </p>
        </div>

        <div className="flex items-center gap-4 text-xs font-mono text-textSubtle">
          <div className="flex items-center gap-1.5">
            <span
              className="w-2.5 h-2.5 rounded-full"
              style={{ backgroundColor: colors.success }}
            />
            <span>Converging toward {referenceBranch}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span
              className="w-2.5 h-2.5 rounded-full"
              style={{ backgroundColor: colors.warning }}
            />
            <span>Diverging vector</span>
          </div>
        </div>
      </div>

      {/* Main SVG Radar Canvas */}
      <div className="flex flex-col md:flex-row items-center gap-8 justify-center py-4">
        <div className="relative w-[300px] h-[300px] flex-shrink-0">
          <svg
            viewBox="0 0 300 300"
            className="w-full h-full"
            aria-hidden="true"
          >
            {/* Concentric Potential Rings */}
            {rings.map((ring) => {
              const r = ring * 120;
              return (
                <g key={ring}>
                  <circle
                    cx="150"
                    cy="150"
                    r={r}
                    fill="none"
                    stroke={colors.border}
                    strokeWidth="1"
                    strokeDasharray={ring === 1.0 ? "none" : "4 4"}
                    opacity="0.6"
                  />
                  <text
                    x="153"
                    y={150 - r + 11}
                    fill={colors.textSubtle}
                    fontSize="9"
                    fontFamily="monospace"
                  >
                    {(ring * 100).toFixed(0)}%
                  </text>
                </g>
              );
            })}

            {/* Radar Crosshairs */}
            <line
              x1="30"
              y1="150"
              x2="270"
              y2="150"
              stroke={colors.border}
              strokeWidth="1"
              opacity="0.4"
            />
            <line
              x1="150"
              y1="30"
              x2="150"
              y2="270"
              stroke={colors.border}
              strokeWidth="1"
              opacity="0.4"
            />

            {/* Trajectory Geodesic Paths and Nodes */}
            {branches.map((b, idx) => {
              const pos = getBranchPosition(b.magnitude, idx, branches.length);
              const isConverging = b.convergence === "converging";
              const nodeColor: string = isConverging ? colors.success : colors.warning;
              const isSelected = selectedBranch === b.branch;
              const isHovered = hoveredBranch === b.branch;

              return (
                <g key={b.branch}>
                  {/* Curved Geodesic Trail from origin to branch */}
                  <path
                    d={`M 150 150 Q ${(150 + pos.x) / 2 - 10} ${(150 + pos.y) / 2 - 10} ${pos.x} ${pos.y}`}
                    fill="none"
                    stroke={nodeColor}
                    strokeWidth={isSelected || isHovered ? "2.5" : "1.5"}
                    strokeDasharray={isConverging ? "none" : "3 3"}
                    opacity={isSelected || isHovered ? "0.9" : "0.5"}
                  />

                  {/* Planet / Trajectory Node */}
                  <motion.circle
                    cx={pos.x}
                    cy={pos.y}
                    r={isSelected || isHovered ? 8 : 6}
                    fill={nodeColor}
                    stroke={colors.surface}
                    strokeWidth="2"
                    className="cursor-pointer"
                    whileHover={{ scale: 1.2 }}
                    transition={{ duration: duration.primary / 1000, ease: easing.easeOut }}
                    onClick={() => onSelectBranch?.(b.branch)}
                    onMouseEnter={() => setHoveredBranch(b.branch)}
                    onMouseLeave={() => setHoveredBranch(null)}
                  />
                </g>
              );
            })}

            {/* Center Origin Attractor (main) */}
            <circle
              cx="150"
              cy="150"
              r="12"
              fill={colors.accent}
              opacity="0.25"
            />
            <circle
              cx="150"
              cy="150"
              r="6"
              fill={colors.accent}
            />
          </svg>

          {/* Reference Attractor Badge at center */}
          <div className="absolute top-[138px] left-[165px] px-2 py-0.5 rounded bg-surface/90 border border-accent/40 text-[10px] font-mono text-accent pointer-events-none shadow-sm">
            {referenceBranch}
          </div>
        </div>

        {/* Trajectory List Sidebar / Inspector */}
        <div className="flex-1 flex flex-col gap-2.5 max-h-[300px] overflow-y-auto w-full" role="list">
          {branches.map((b) => {
            const isSelected = selectedBranch === b.branch;
            const isConverging = b.convergence === "converging";
            let statusColor: string = colors.warning;
            if (isConverging) statusColor = colors.success;

            return (
              <div key={b.branch} role="listitem">
                <button
                  type="button"
                  onClick={() => onSelectBranch?.(b.branch)}
                  onMouseEnter={() => setHoveredBranch(b.branch)}
                  onMouseLeave={() => setHoveredBranch(null)}
                  className={`w-full p-3 rounded-lg border text-left transition-all flex flex-col gap-1.5 ${
                    isSelected || hoveredBranch === b.branch
                      ? "border-accent bg-accent/10 shadow-sm"
                      : "border-border bg-surface/60 hover:border-borderStrong"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-sm font-semibold text-text truncate">
                      {b.branch}
                    </span>
                    <span
                      className="text-[10px] font-mono px-1.5 py-0.5 rounded border uppercase"
                      style={{
                        color: statusColor,
                        borderColor: `${statusColor}50`,
                        backgroundColor: `${statusColor}15`,
                      }}
                    >
                      {b.convergence}
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-xs text-textMuted font-mono">
                    <span>
                      Δs: <strong className="text-text">{(b.magnitude * 100).toFixed(0)}%</strong>
                    </span>
                    <span>
                      v: <strong className="text-text">{(b.velocity * 100).toFixed(1)}%</strong>
                    </span>
                    <span>
                      symbols: <strong className="text-text">{b.affected?.length || 0}</strong>
                    </span>
                  </div>
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
