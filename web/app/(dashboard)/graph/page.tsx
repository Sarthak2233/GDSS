"use client";

import React, { useState, useMemo } from "react";
import dynamic from "next/dynamic";
import { useQuery } from "@tanstack/react-query";
import { Network, Share2, Layers, AlertCircle, RefreshCw } from "lucide-react";
import { GDSS_API_BASE_URL } from "@/lib/api";
import { useRepo } from "@/context/RepoContext";
import { NodeDetailPanel } from "@/components/constellation/node-detail-panel";
import { ConstellationLegend } from "@/components/constellation/constellation-legend";
import { SymbolSearchPicker } from "@/components/constellation/symbol-search-picker";
import type { GraphResponse, GraphNode } from "@/lib/constellation/constellation-engine";

const ConstellationCanvas = dynamic(
  () =>
    import("@/components/constellation/constellation-canvas").then(
      (mod) => mod.ConstellationCanvas
    ),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-full flex items-center justify-center bg-surface rounded-xl border border-border">
        <div className="flex items-center gap-2 text-textMuted text-sm animate-pulse">
          <Network className="w-5 h-5 text-accent animate-spin" />
          <span>Loading 3D Constellation...</span>
        </div>
      </div>
    ),
  }
);

export default function GraphPage() {
  const { refName } = useRepo();
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const { data, isLoading, error, refetch } = useQuery<GraphResponse>({
    queryKey: ["graph", refName],
    queryFn: async () => {
      const url = new URL("/v1/graph", GDSS_API_BASE_URL || window.location.origin);
      if (refName) url.searchParams.set("ref", refName);

      const resp = await fetch(url.toString());
      if (!resp.ok) throw new Error("Failed to fetch graph data");
      const json = await resp.json();
      return json.data as GraphResponse;
    },
    staleTime: 30_000,
  });

  const symbolsQuery = useQuery({
    queryKey: ["symbols", refName],
    queryFn: async () => {
      const url = new URL("/v1/symbols", GDSS_API_BASE_URL || window.location.origin);
      if (refName) url.searchParams.set("ref", refName);
      const resp = await fetch(url.toString());
      if (!resp.ok) throw new Error("Failed to fetch symbols");
      const json = await resp.json();
      return (json.data?.symbols || []) as {
        id: string;
        name: string;
        type: string;
        location: string;
      }[];
    },
    staleTime: 30_000,
  });

  const nodes = useMemo(() => data?.nodes || [], [data]);
  const edges = useMemo(() => data?.edges || [], [data]);
  const summary = data?.summary || { total_nodes: 0, total_edges: 0 };

  const selectedNode = useMemo(() => {
    if (!selectedNodeId) return null;
    return nodes.find((n) => n.id === selectedNodeId) || null;
  }, [selectedNodeId, nodes]);

  const symbolsList = useMemo(() => {
    if (symbolsQuery.data && symbolsQuery.data.length > 0) {
      return symbolsQuery.data.map((n) => ({
        id: n.id,
        name: n.name || n.id,
        type: n.type,
        location: n.location || "",
      }));
    }
    return nodes.map((n) => ({
      id: n.id,
      name: n.name || n.id,
      type: n.type,
      location: n.location || "",
    }));
  }, [symbolsQuery.data, nodes]);

  const highlightedNodes = useMemo(() => {
    if (!selectedNodeId) return undefined;
    const set = new Set<string>([selectedNodeId]);
    for (const e of edges) {
      if (e.source === selectedNodeId) set.add(e.target);
      if (e.target === selectedNodeId) set.add(e.source);
    }
    return set;
  }, [selectedNodeId, edges]);

  const connectedSymbols = useMemo(() => {
    if (!selectedNodeId) return undefined;
    const result = [];
    const nodeMap = new Map(nodes.map((n) => [n.id, n]));
    for (const e of edges) {
      if (e.source === selectedNodeId) {
        const tgt = nodeMap.get(e.target);
        if (tgt) {
          result.push({
            id: tgt.id,
            name: tgt.name || tgt.id,
            type: tgt.type,
            relationship: e.relationship || "calls",
            location: tgt.location,
          });
        }
      } else if (e.target === selectedNodeId) {
        const src = nodeMap.get(e.source);
        if (src) {
          result.push({
            id: src.id,
            name: src.name || src.id,
            type: src.type,
            relationship: `called by (${e.relationship || "calls"})`,
            location: src.location,
          });
        }
      }
    }
    return result;
  }, [selectedNodeId, edges, nodes]);

  return (
    <div className="flex flex-col h-full w-full justify-between gap-4 relative overflow-hidden">
      {/* Header */}
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border pb-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
              <Network className="w-6 h-6 text-accent" />
              Semantic Graph
            </h1>
            <span className="text-xs px-2 py-0.5 rounded-full border border-border bg-surfaceElevated text-textMuted font-mono">
              Phase F4
            </span>
          </div>
          <p className="text-xs text-textSubtle mt-1">
            Interactive 3D code constellation of repository symbols and dependencies.
          </p>
        </div>

        {/* Status Pills */}
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border bg-surface text-xs font-medium text-text">
            <Layers className="w-3.5 h-3.5 text-accent" />
            <span>{summary.total_nodes} Symbols</span>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border bg-surface text-xs font-medium text-text">
            <Share2 className="w-3.5 h-3.5 text-merge" />
            <span>{summary.total_edges} Connections</span>
          </div>
          {error && (
            <button
              type="button"
              onClick={() => refetch()}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-danger/40 bg-danger/10 text-xs font-medium text-danger hover:bg-danger/20 transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Retry</span>
            </button>
          )}
        </div>
      </header>

      {/* Interactive Constellation Legend & Two-Brain Guide */}
      <ConstellationLegend mode="graph" />

      {/* Symbol Search & Autocomplete */}
      <div className="w-full">
        <SymbolSearchPicker
          symbols={symbolsList}
          onSelectSymbol={(id) => setSelectedNodeId(id)}
          placeholder="Search repository AST symbols (e.g., ASTParser)..."
        />
      </div>

      {/* Main Graph Viewport */}
      <div className="flex-1 w-full min-h-0 relative rounded-xl overflow-hidden border border-border bg-bg">
        {isLoading ? (
          <div className="w-full h-full flex items-center justify-center">
            <div className="flex items-center gap-2 text-textMuted text-sm animate-pulse">
              <Network className="w-5 h-5 text-accent animate-spin" />
              <span>Loading 3D Constellation...</span>
            </div>
          </div>
        ) : error ? (
          <div className="w-full h-full flex flex-col items-center justify-center gap-2 p-6 text-center">
            <AlertCircle className="w-8 h-8 text-danger" />
            <p className="text-sm font-semibold text-text">Failed to load repository graph</p>
            <p className="text-xs text-textSubtle max-w-sm">
              Ensure the GDSS local API (`gdss serve`) is running and indexed.
            </p>
          </div>
        ) : (
          <ConstellationCanvas
            nodes={nodes}
            edges={edges}
            onNodeSelect={(id) => setSelectedNodeId(id)}
            highlightedNodes={highlightedNodes}
            selectedNodeId={selectedNodeId}
          />
        )}

        <NodeDetailPanel
          node={selectedNode}
          connectedSymbols={connectedSymbols}
          onClose={() => setSelectedNodeId(null)}
          onConnectedSelect={(id) => setSelectedNodeId(id)}
        />
      </div>
    </div>
  );
}

