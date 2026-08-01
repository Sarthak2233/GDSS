"use client";

import React, { useMemo, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  Sparkles,
  Search,
  AlertCircle,
  RefreshCw,
  Network,
  SlidersHorizontal,
} from "lucide-react";
import { GDSS_API_BASE_URL } from "@/lib/api";
import { useRepo } from "@/context/RepoContext";
import { AssistiveBadge } from "@/components/constellation/assistive-badge";
import { SymbolSearchPicker } from "@/components/constellation/symbol-search-picker";
import { EmbeddingSpaceCanvas } from "@/components/embedding/embedding-space-canvas";
import { NeighborRankPanel } from "@/components/embedding/neighbor-rank-panel";
import type {
  EmbeddingProjectionData,
  SimilarData,
  SymbolItem,
} from "@/lib/api-types";

export default function SimilarPage() {
  const { refName } = useRepo();
  const [searchInput, setSearchInput] = useState("");
  const [activeSymbol, setActiveSymbol] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [k, setK] = useState(10);
  const [typeFilter, setTypeFilter] = useState<string>("all");

  const projectionQuery = useQuery<EmbeddingProjectionData>({
    queryKey: ["embeddings-projection", refName],
    queryFn: async () => {
      const url = new URL(
        "/v1/embeddings/projection",
        GDSS_API_BASE_URL || window.location.origin
      );
      url.searchParams.set("dims", "2");
      url.searchParams.set("limit", "500");
      const resp = await fetch(url.toString());
      if (!resp.ok) throw new Error("Failed to fetch embedding projection");
      const json = await resp.json();
      return json.data as EmbeddingProjectionData;
    },
    staleTime: 30_000,
  });

  const symbolsQuery = useQuery({
    queryKey: ["symbols", refName],
    queryFn: async () => {
      const url = new URL(
        "/v1/symbols",
        GDSS_API_BASE_URL || window.location.origin
      );
      if (refName) url.searchParams.set("ref", refName);
      const resp = await fetch(url.toString());
      if (!resp.ok) throw new Error("Failed to fetch symbols");
      const json = await resp.json();
      return (json.data?.symbols || []) as SymbolItem[];
    },
    staleTime: 30_000,
  });

  const similarQuery = useQuery<SimilarData>({
    queryKey: ["similar", activeSymbol, k],
    queryFn: async () => {
      if (!activeSymbol) return { assistive: true as const, hits: [] };
      const url = new URL(
        "/v1/similar",
        GDSS_API_BASE_URL || window.location.origin
      );
      url.searchParams.set("symbol", activeSymbol);
      url.searchParams.set("k", String(k));
      const resp = await fetch(url.toString());
      if (!resp.ok) throw new Error("Failed to fetch similar symbols");
      const json = await resp.json();
      return json.data as SimilarData;
    },
    enabled: Boolean(activeSymbol),
  });

  const points = useMemo(() => {
    const all = projectionQuery.data?.points || [];
    if (typeFilter === "all") return all;
    return all.filter((p) => p.type === typeFilter);
  }, [projectionQuery.data, typeFilter]);

  const typeOptions = useMemo(() => {
    const set = new Set<string>();
    for (const p of projectionQuery.data?.points || []) {
      if (p.type) set.add(p.type);
    }
    return Array.from(set).sort();
  }, [projectionQuery.data]);

  const hits = useMemo(() => similarQuery.data?.hits || [], [similarQuery.data]);

  const highlightedIds = useMemo(() => {
    if (!activeSymbol && !selectedId) return undefined;
    const set = new Set<string>();
    if (activeSymbol) set.add(activeSymbol);
    if (selectedId) set.add(selectedId);
    for (const h of hits) set.add(h.id);
    return set;
  }, [activeSymbol, selectedId, hits]);

  const symbolsList = useMemo(() => {
    if (symbolsQuery.data && symbolsQuery.data.length > 0) {
      return symbolsQuery.data;
    }
    return points.map((p) => ({
      id: p.id,
      name: p.name || p.id,
      type: p.type,
      location: p.location || "",
    }));
  }, [symbolsQuery.data, points]);

  const graphHref = activeSymbol
    ? `/graph?symbol=${encodeURIComponent(activeSymbol)}`
    : "/graph";

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchInput.trim()) return;
    const id = searchInput.trim();
    setActiveSymbol(id);
    setSelectedId(id);
  };

  const selectSymbol = (id: string) => {
    setActiveSymbol(id);
    setSelectedId(id);
  };

  return (
    <div className="flex flex-col h-full w-full gap-4 relative overflow-hidden">
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-border pb-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
              <Sparkles className="w-6 h-6 text-accent" />
              Embedding Space
            </h1>
            <span className="text-xs px-2 py-0.5 rounded-full border border-border bg-surfaceElevated text-textMuted font-mono">
              Phase F6+
            </span>
          </div>
          <p className="text-xs text-textSubtle mt-1">
            Assistive PCA projection of symbol embeddings. Distance approximates
            cosine similarity — not structural dependency.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          <AssistiveBadge />
          <form onSubmit={handleSearchSubmit} className="flex items-center gap-2">
            <div className="relative">
              <Search className="w-4 h-4 text-textSubtle absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Search symbol name..."
                className="w-56 bg-surface border border-border rounded-lg pl-9 pr-3 py-1.5 text-xs text-text placeholder:text-textSubtle focus:outline-none focus:border-accent transition-colors"
                aria-label="Search symbol name"
              />
            </div>
            <button
              type="submit"
              className="px-3 py-1.5 rounded-lg bg-accent hover:bg-accentMuted text-white text-xs font-semibold transition-colors flex items-center gap-1 shadow-md"
            >
              <span>Search</span>
            </button>
          </form>
        </div>
      </header>

      <div className="flex flex-col sm:flex-row sm:items-center gap-3">
        <SymbolSearchPicker
          symbols={symbolsList}
          onSelectSymbol={selectSymbol}
          placeholder="Search & inspect embedding neighbors (e.g., ASTParser)..."
        />
        <div className="flex items-center gap-3 flex-shrink-0">
          <label className="flex items-center gap-2 text-xs text-textMuted">
            <SlidersHorizontal className="w-3.5 h-3.5" />
            <span>k</span>
            <input
              type="range"
              min={3}
              max={30}
              value={k}
              onChange={(e) => setK(Number(e.target.value))}
              aria-label="Neighbor count k"
              className="w-24"
            />
            <span className="font-mono text-text w-6">{k}</span>
          </label>
          <label className="flex items-center gap-2 text-xs text-textMuted">
            <span>Type</span>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              aria-label="Filter by symbol type"
              className="bg-surface border border-border rounded-lg px-2 py-1 text-xs text-text"
            >
              <option value="all">all</option>
              {typeOptions.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>
          <Link
            href={graphHref}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border bg-surface text-xs font-medium text-text hover:border-accent/50 transition-colors"
          >
            <Network className="w-3.5 h-3.5 text-accent" />
            Open in Semantic Graph
          </Link>
        </div>
      </div>

      <div className="flex-1 min-h-0 flex flex-col md:flex-row gap-4">
        <div className="flex-1 min-h-0 relative rounded-xl overflow-hidden border border-border bg-bg">
          {projectionQuery.isLoading ? (
            <div className="w-full h-full flex items-center justify-center">
              <div className="flex items-center gap-2 text-textMuted text-sm animate-pulse">
                <Sparkles className="w-5 h-5 text-accent animate-spin" />
                <span>Loading embedding projection...</span>
              </div>
            </div>
          ) : projectionQuery.error ? (
            <div className="w-full h-full flex flex-col items-center justify-center gap-2 p-6 text-center">
              <AlertCircle className="w-8 h-8 text-danger" />
              <p className="text-sm font-semibold text-text">
                Failed to load embedding projection
              </p>
              <button
                type="button"
                onClick={() => projectionQuery.refetch()}
                className="mt-2 flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-danger/40 bg-danger/10 text-xs font-medium text-danger hover:bg-danger/20 transition-colors"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Retry</span>
              </button>
            </div>
          ) : (
            <EmbeddingSpaceCanvas
              points={points}
              selectedId={selectedId || activeSymbol}
              highlightedIds={highlightedIds}
              onSelect={selectSymbol}
            />
          )}
        </div>

        <NeighborRankPanel
          querySymbol={activeSymbol}
          hits={hits}
          onSelect={selectSymbol}
        />
      </div>

      {projectionQuery.data && (
        <footer className="text-[10px] text-textSubtle border-t border-border pt-2">
          method={projectionQuery.data.method} · encoder=
          {projectionQuery.data.encoder} · dim={projectionQuery.data.dim_full} ·{" "}
          {points.length} points shown (assistive PCA — not a dependency graph)
        </footer>
      )}
    </div>
  );
}
