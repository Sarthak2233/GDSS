'use client';

import React, { useState } from 'react';
import { Brain, HelpCircle, X, Layers, GitFork, Sparkles, BookOpen } from 'lucide-react';

export interface ConstellationLegendProps {
  mode: 'graph' | 'similar';
}

export function ConstellationLegend({ mode }: ConstellationLegendProps) {
  const [showGuide, setShowGuide] = useState(false);

  const isGraph = mode === 'graph';

  React.useEffect(() => {
    if (!showGuide) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setShowGuide(false);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showGuide]);

  return (
    <>
      {/* Legend Banner */}
      <div
        className="flex flex-wrap items-center justify-between gap-3 px-4 py-2.5 rounded-lg border border-border bg-card/90 backdrop-blur-sm text-sm"
        role="region"
        aria-label="Constellation Legend and Mode Information"
      >
        <div className="flex items-center gap-3">
          <div
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold uppercase tracking-wider ${
              isGraph
                ? 'bg-blue-500/15 text-blue-400 border border-blue-500/30'
                : 'bg-purple-500/15 text-purple-400 border border-purple-500/30'
            }`}
          >
            <Brain className="h-3.5 w-3.5" aria-hidden="true" />
            <span>{isGraph ? 'DETERMINISTIC BRAIN' : 'PROBABILISTIC BRAIN'}</span>
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-2">
            <span className="font-medium text-foreground">
              {isGraph ? 'Structural AST Dependencies' : 'AI Vector Embeddings'}
            </span>
            <span className="hidden sm:inline text-muted-foreground">•</span>
            <span className="text-xs text-muted-foreground">
              {isGraph
                ? 'Showing exact call & import edges from parsed repository AST'
                : 'Showing 64-dim vector semantic neighbors across branch trajectories'}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Symbol type key summary */}
          <div className="hidden md:flex items-center gap-3 text-xs text-muted-foreground mr-2 border-r border-border pr-3">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-blue-500" aria-hidden="true" />
              <span>Function</span>
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-purple-500" aria-hidden="true" />
              <span>Class</span>
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-amber-500" aria-hidden="true" />
              <span>Method</span>
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-emerald-500" aria-hidden="true" />
              <span>Import</span>
            </span>
          </div>

          <button
            type="button"
            onClick={() => setShowGuide(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-secondary/80 hover:bg-secondary text-secondary-foreground transition-colors border border-border"
            aria-haspopup="dialog"
          >
            <HelpCircle className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
            <span>Understand the Two Brains</span>
          </button>
        </div>
      </div>

      {/* Interactive Two Brains Comparison Modal */}
      {showGuide && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="two-brains-guide-title"
          aria-describedby="two-brains-guide-desc"
        >
          <div className="relative w-full max-w-2xl max-h-[85vh] overflow-y-auto rounded-xl border border-border bg-card p-6 shadow-2xl space-y-6">
            <div className="flex items-start justify-between gap-4 border-b border-border pb-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2 text-primary font-semibold text-sm">
                  <BookOpen className="h-4 w-4" aria-hidden="true" />
                  <span>GDSS Architecture Guide</span>
                </div>
                <h2 id="two-brains-guide-title" className="text-xl font-bold text-foreground">
                  Why Two Different Pages?
                </h2>
                <p id="two-brains-guide-desc" className="text-xs text-muted-foreground">
                  Understanding the complement between Deterministic and Probabilistic analysis in GDSS.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowGuide(false)}
                className="p-1 rounded-md hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
                aria-label="Close guide modal"
              >
                <X className="h-5 w-5" aria-hidden="true" />
              </button>
            </div>

            {/* Comparison Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Deterministic Brain */}
              <div className="p-4 rounded-lg border border-blue-500/30 bg-blue-500/5 space-y-3">
                <div className="flex items-center gap-2 text-blue-400 font-semibold">
                  <GitFork className="h-4 w-4" aria-hidden="true" />
                  <span>Deterministic Brain (/graph)</span>
                </div>
                <p className="text-xs text-muted-foreground">
                  Powered by <strong>tree-sitter AST parsing</strong>. Shows absolute mathematical certainty: which symbol imports, defines, or calls which other symbol.
                </p>
                <ul className="text-xs space-y-1 text-foreground">
                  <li className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                    <span>Exact AST call & import edges</span>
                  </li>
                  <li className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                    <span>Structural refactor impact</span>
                  </li>
                  <li className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                    <span>Type & signature boundaries</span>
                  </li>
                </ul>
              </div>

              {/* Probabilistic Brain */}
              <div className="p-4 rounded-lg border border-purple-500/30 bg-purple-500/5 space-y-3">
                <div className="flex items-center gap-2 text-purple-400 font-semibold">
                  <Sparkles className="h-4 w-4" aria-hidden="true" />
                  <span>Probabilistic Brain (/similar)</span>
                </div>
                <p className="text-xs text-muted-foreground">
                  Powered by <strong>64-dim vector embeddings</strong>. Finds symbols with similar intent, structure, or terminology even if they never import each other.
                </p>
                <ul className="text-xs space-y-1 text-foreground">
                  <li className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-purple-400" />
                    <span>Semantic vector similarity</span>
                  </li>
                  <li className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-purple-400" />
                    <span>Cross-module conceptual drift</span>
                  </li>
                  <li className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-purple-400" />
                    <span>Fuzzy matching & refactor discovery</span>
                  </li>
                </ul>
              </div>
            </div>

            {/* Practical Example */}
            <div className="p-4 rounded-lg bg-secondary/50 border border-border space-y-2">
              <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <Layers className="h-4 w-4 text-primary" aria-hidden="true" />
                <span>When should I use which page?</span>
              </h3>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Use <strong>/graph</strong> when you are tracing a bug or refactoring a function and must know every caller that will break if the signature changes.
                Use <strong>/similar</strong> when you are adding a new feature or checking if another team has already implemented a similar helper or transformation across diverged branches.
              </p>
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={() => setShowGuide(false)}
                className="px-4 py-2 rounded-md text-xs font-semibold bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
              >
                Got it, close guide
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
