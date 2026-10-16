"use client";

import React, { useMemo } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { colors, spacing } from "@/lib/tokens";
import { duration, easing } from "@/lib/motion";
import type { EmbeddingProjectionPoint } from "@/lib/api-types";

export interface EmbeddingSpaceCanvasProps {
  points: EmbeddingProjectionPoint[];
  selectedId?: string | null;
  highlightedIds?: Set<string>;
  onSelect: (id: string) => void;
}

function normalizeExtent(values: number[]): { min: number; max: number } {
  if (values.length === 0) return { min: -1, max: 1 };
  let min = Math.min(...values);
  let max = Math.max(...values);
  if (Math.abs(max - min) < 1e-9) {
    min -= 1;
    max += 1;
  }
  return { min, max };
}

export function EmbeddingSpaceCanvas({
  points,
  selectedId = null,
  highlightedIds,
  onSelect,
}: EmbeddingSpaceCanvasProps) {
  const reduceMotion = useReducedMotion();
  const hasHighlight = Boolean(highlightedIds && highlightedIds.size > 0);

  const layout = useMemo(() => {
    const xs = points.map((p) => p.x);
    const ys = points.map((p) => p.y);
    const xExt = normalizeExtent(xs);
    const yExt = normalizeExtent(ys);
    const pad = 48;
    const width = 640;
    const height = 400;
    const mapX = (x: number) =>
      pad + ((x - xExt.min) / (xExt.max - xExt.min)) * (width - pad * 2);
    const mapY = (y: number) =>
      height - pad - ((y - yExt.min) / (yExt.max - yExt.min)) * (height - pad * 2);
    return { width, height, mapX, mapY, pad };
  }, [points]);

  if (points.length === 0) {
    return (
      <div
        className="w-full h-full flex items-center justify-center bg-surface text-textMuted text-sm"
        role="status"
      >
        No embedding points available. Run gdss reindex if the vector index is empty.
      </div>
    );
  }

  return (
    <div
      className="w-full h-full min-h-0 bg-bg relative overflow-hidden"
      aria-label="Embedding space projection of repository symbols"
      data-testid="embedding-space-canvas"
    >
      <svg
        viewBox={`0 0 ${layout.width} ${layout.height}`}
        className="w-full h-full"
        aria-hidden="true"
      >
        <rect
          x={0}
          y={0}
          width={layout.width}
          height={layout.height}
          fill={colors.bg}
        />
        {/* Axes hint */}
        <line
          x1={layout.pad}
          y1={layout.height / 2}
          x2={layout.width - layout.pad}
          y2={layout.height / 2}
          stroke={colors.border}
          strokeWidth={1}
          strokeDasharray="4 4"
        />
        <line
          x1={layout.width / 2}
          y1={layout.pad}
          x2={layout.width / 2}
          y2={layout.height - layout.pad}
          stroke={colors.border}
          strokeWidth={1}
          strokeDasharray="4 4"
        />
        <text
          x={layout.pad}
          y={layout.height - spacing[2]}
          fill={colors.textSubtle}
          fontSize={10}
        >
          PC1
        </text>
        <text
          x={layout.width - layout.pad - spacing[6]}
          y={layout.pad}
          fill={colors.textSubtle}
          fontSize={10}
        >
          PC2
        </text>

        {points.map((p) => {
          const cx = layout.mapX(p.x);
          const cy = layout.mapY(p.y);
          const selected = selectedId === p.id;
          const highlighted = highlightedIds?.has(p.id) ?? false;
          const dimmed = hasHighlight && !highlighted && !selected;
          const r = selected ? 8 : highlighted ? 6 : 4;
          const fill = selected
            ? colors.accent
            : highlighted
              ? colors.merge
              : colors.node;

          return (
            <g key={p.id}>
              <motion.circle
                cx={cx}
                cy={cy}
                r={r}
                fill={fill}
                opacity={dimmed ? 0.25 : 0.9}
                initial={reduceMotion ? false : { opacity: 0, scale: 0.6 }}
                animate={{
                  opacity: dimmed ? 0.25 : 0.9,
                  scale: 1,
                }}
                transition={
                  reduceMotion
                    ? { duration: 0 }
                    : {
                        duration: duration.primary / 1000,
                        ease: easing.easeOut,
                      }
                }
                style={{ transformOrigin: `${cx}px ${cy}px` }}
              />
              {(selected || highlighted) && (
                <text
                  x={cx + 10}
                  y={cy + 3}
                  fill={colors.text}
                  fontSize={10}
                  className="pointer-events-none"
                >
                  {(p.name || p.id).slice(0, 24)}
                </text>
              )}
            </g>
          );
        })}
      </svg>
      {/* Absolute hit targets — keep interactive controls outside decorative SVG */}
      <div className="absolute inset-0" aria-hidden={false}>
        {points.map((p) => {
          const cx = layout.mapX(p.x);
          const cy = layout.mapY(p.y);
          const leftPct = (cx / layout.width) * 100;
          const topPct = (cy / layout.height) * 100;
          const selected = selectedId === p.id;
          return (
            <button
              key={p.id}
              type="button"
              aria-label={p.name || p.id}
              aria-pressed={selected}
              className="absolute w-6 h-6 -translate-x-1/2 -translate-y-1/2 rounded-full cursor-pointer bg-transparent border-0 p-0 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
              style={{ left: `${leftPct}%`, top: `${topPct}%` }}
              onClick={() => onSelect(p.id)}
            />
          );
        })}
      </div>
    </div>
  );
}
