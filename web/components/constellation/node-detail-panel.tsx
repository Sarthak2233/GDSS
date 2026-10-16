"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, ExternalLink, Code2, FileText, Cpu, GitFork } from "lucide-react";
import { duration, easing } from "@/lib/motion";
import { colors } from "@/lib/tokens";
import type { GraphNode, SimilarHit } from "@/lib/constellation/constellation-engine";
import { NODE_COLORS } from "@/lib/constellation/constellation-engine";

export interface ConnectedSymbol {
  id: string;
  name: string;
  type: string;
  relationship?: string;
  location?: string;
}

export interface NodeDetailPanelProps {
  node: GraphNode | null;
  similarHits?: SimilarHit[];
  connectedSymbols?: ConnectedSymbol[];
  onClose: () => void;
  onNeighborSelect?: (id: string) => void;
  onConnectedSelect?: (id: string) => void;
}

export function NodeDetailPanel({
  node,
  similarHits,
  connectedSymbols,
  onClose,
  onNeighborSelect,
  onConnectedSelect,
}: NodeDetailPanelProps) {
  const [reduceMotion, setReduceMotion] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return;
    const mql = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduceMotion(mql.matches);
    const handler = (e: MediaQueryListEvent) => setReduceMotion(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, []);

  if (!node) return null;

  const nodeColor = NODE_COLORS[node.type] ?? colors.accent;
  const hits = similarHits ? similarHits.slice(0, 5) : [];

  return (
    <AnimatePresence>
      <motion.aside
        className="absolute top-4 right-4 z-content w-80 rounded-xl border border-border bg-surfaceGlass/90 backdrop-blur-xl p-5 shadow-2xl flex flex-col gap-4 text-text"
        initial={reduceMotion ? undefined : { opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        exit={reduceMotion ? undefined : { opacity: 0, x: 20 }}
        transition={
          reduceMotion
            ? { duration: 0 }
            : { duration: duration.primary / 1000, ease: easing.easeOut }
        }
        role="region"
        aria-label="Symbol Details"
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-2 border-b border-border pb-3">
          <div className="min-w-0 flex-1">
            <span
              className="inline-block px-2 py-0.5 rounded text-xs font-semibold mb-1 uppercase tracking-wider"
              style={{
                backgroundColor: `${nodeColor}22`,
                color: nodeColor,
              }}
            >
              {node.type}
            </span>
            <h3
              className="text-lg font-bold truncate text-foreground"
              title={node.name || node.id}
            >
              {node.name || node.id}
            </h3>
            <p
              className="text-xs text-textSubtle font-mono truncate mt-0.5"
              title={node.location || undefined}
            >
              {node.location || "No location info"}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-surfaceElevated text-textMuted hover:text-text transition-colors flex-shrink-0"
            aria-label="Close details panel"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Connected AST Symbols Section */}
        {connectedSymbols && (
          <div className="flex flex-col gap-2">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-textMuted flex items-center gap-1.5">
              <GitFork className="w-3.5 h-3.5 text-blue-400" />
              Connected Symbols ({connectedSymbols.length})
            </h4>
            {connectedSymbols.length === 0 ? (
              <p className="text-xs text-textSubtle py-2">No direct AST edges found.</p>
            ) : (
              <ul className="flex flex-col gap-1.5 max-h-48 overflow-y-auto pr-1">
                {connectedSymbols.slice(0, 10).map((sym) => {
                  const badgeColor = NODE_COLORS[sym.type] ?? colors.accent;
                  return (
                    <li key={`${sym.relationship}-${sym.id}`}>
                      <button
                        type="button"
                        onClick={() => (onConnectedSelect ? onConnectedSelect(sym.id) : onNeighborSelect?.(sym.id))}
                        className="w-full text-left p-2 rounded-lg border border-border/50 bg-surfaceElevated/50 hover:bg-surfaceElevated hover:border-border transition-all flex items-center justify-between gap-2 group"
                      >
                        <div className="min-w-0 flex-1">
                          <p className="text-xs font-medium truncate text-text group-hover:text-blue-400 transition-colors">
                            {sym.name || sym.id}
                          </p>
                          {sym.location && (
                            <p className="text-[10px] text-textSubtle font-mono truncate">
                              {sym.location}
                            </p>
                          )}
                        </div>
                        <span
                          className="text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded flex-shrink-0"
                          style={{
                            backgroundColor: `${badgeColor}22`,
                            color: badgeColor,
                          }}
                        >
                          {sym.relationship || sym.type}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        )}

        {/* Similar Neighbors Section */}
        {similarHits && (
          <div className="flex flex-col gap-2">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-textMuted flex items-center gap-1.5">
              <Cpu className="w-3.5 h-3.5 text-accent" />
              Similar Symbols ({hits.length})
            </h4>
            {hits.length === 0 ? (
              <p className="text-xs text-textSubtle py-2">No similar symbols found in index.</p>
            ) : (
              <ul className="flex flex-col gap-1.5">
                {hits.map((hit, idx) => {
                  const percent = Math.round(hit.score * 100);
                  return (
                    <li key={hit.id}>
                      <button
                        type="button"
                        onClick={() => onNeighborSelect?.(hit.id)}
                        className="w-full text-left p-2 rounded-lg border border-border/50 bg-surfaceElevated/50 hover:bg-surfaceElevated hover:border-border transition-all flex items-center justify-between gap-2 group"
                      >
                        <div className="min-w-0 flex-1">
                          <p className="text-xs font-medium truncate text-text group-hover:text-accent transition-colors">
                            {hit.name || hit.id}
                          </p>
                          <p className="text-[10px] text-textSubtle font-mono truncate">
                            {hit.location || "—"}
                          </p>
                        </div>
                        <span
                          className="text-xs font-bold px-1.5 py-0.5 rounded flex-shrink-0"
                          style={{
                            backgroundColor:
                              percent >= 85
                                ? `${colors.success}22`
                                : `${colors.accent}22`,
                            color: percent >= 85 ? colors.success : colors.accent,
                          }}
                        >
                          {percent}%
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        )}
      </motion.aside>
    </AnimatePresence>
  );
}
