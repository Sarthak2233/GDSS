"use client";

import { useState, useRef, useEffect } from "react";
import { useRepo } from "@/context/RepoContext";
import { Filter, ChevronDown, RotateCcw } from "lucide-react";

export function RepoRefPicker() {
  const {
    repo,
    refName,
    setRefName,
    branches,
    branchesLoading,
    branchesError,
    selectedBranches,
    setSelectedBranches,
  } = useRepo();

  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  const candidateBranches = branches.filter((b) => b !== refName);

  const toggleBranch = (branch: string) => {
    if (selectedBranches.includes(branch)) {
      setSelectedBranches(selectedBranches.filter((b) => b !== branch));
    } else {
      setSelectedBranches([...selectedBranches, branch]);
    }
  };

  const clearAll = () => {
    setSelectedBranches([]);
  };

  return (
    <div className="flex items-center gap-4 bg-surface border border-border rounded-xl px-6 py-3 shadow-md flex-wrap relative z-dropdown">
      <div className="flex items-center gap-2 min-w-0">
        <span className="text-sm font-medium text-textMuted whitespace-nowrap">
          Repo:
        </span>
        <span
          id="repo-display"
          aria-label="Repo:"
          title={repo || "Bound at gdss serve --repo"}
          className="bg-surfaceElevated px-3 py-1 rounded-md text-sm border border-border text-textMuted font-mono truncate max-w-xs"
          data-testid="repo-readonly"
        >
          {repo || "…"}
        </span>
        <span className="text-[10px] text-textSubtle whitespace-nowrap">
          (bound at serve)
        </span>
      </div>
      <div className="flex items-center gap-2">
        <label
          htmlFor="ref-select"
          className="text-sm font-medium text-textMuted whitespace-nowrap"
        >
          Ref:
        </label>
        <select
          id="ref-select"
          aria-label="Ref:"
          value={refName}
          onChange={(e) => setRefName(e.target.value)}
          disabled={branchesLoading || branches.length === 0}
          className="bg-surfaceElevated px-3 py-1 rounded-md text-sm border border-border focus:border-accent focus:ring-1 focus:ring-accent outline-none transition-all min-w-[8rem] text-text"
          data-testid="ref-select"
        >
          {branchesLoading && <option value={refName}>Loading…</option>}
          {!branchesLoading && branches.length === 0 && (
            <option value={refName}>{refName}</option>
          )}
          {branches.map((b) => (
            <option key={b} value={b}>
              {b}
            </option>
          ))}
        </select>
        {branchesError && (
          <span className="text-xs text-danger" role="alert">
            {branchesError}
          </span>
        )}
      </div>

      {/* Branch Scope Filter */}
      <div className="relative flex items-center gap-2" ref={dropdownRef}>
        <span className="text-sm font-medium text-textMuted whitespace-nowrap">
          Scope:
        </span>
        <button
          type="button"
          id="branch-scope-btn"
          aria-haspopup="dialog"
          aria-expanded={isOpen}
          aria-label="Filter target branches"
          data-testid="branch-scope-btn"
          onClick={() => setIsOpen((prev) => !prev)}
          disabled={branchesLoading || candidateBranches.length === 0}
          className="inline-flex items-center gap-2 bg-surfaceElevated px-3 py-1 rounded-md text-sm border border-border hover:border-accent/50 focus:border-accent focus:ring-1 focus:ring-accent outline-none transition-all text-text"
        >
          <Filter className="w-3.5 h-3.5 text-textMuted" aria-hidden="true" />
          <span>
            {selectedBranches.length === 0
              ? `All branches (${candidateBranches.length})`
              : `${selectedBranches.length} selected`}
          </span>
          <ChevronDown
            className={`w-3.5 h-3.5 text-textSubtle transition-transform ${
              isOpen ? "rotate-180" : ""
            }`}
            aria-hidden="true"
          />
        </button>

        {selectedBranches.length > 0 && (
          <button
            type="button"
            onClick={clearAll}
            aria-label="Reset branch filter"
            title="Reset branch filter"
            className="p-1 text-textSubtle hover:text-text rounded hover:bg-surfaceElevated transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" aria-hidden="true" />
          </button>
        )}

        {isOpen && (
          <div
            role="dialog"
            aria-label="Target branches filter"
            className="absolute top-full left-0 mt-2 w-64 bg-surfaceElevated border border-borderStrong rounded-lg shadow-xl p-3 z-modal"
          >
            <div className="flex items-center justify-between pb-2 mb-2 border-b border-border">
              <span className="text-xs font-semibold text-text uppercase tracking-wider">
                Filter Branches
              </span>
              <button
                type="button"
                onClick={clearAll}
                className="text-xs text-accent hover:underline"
              >
                Reset (All)
              </button>
            </div>
            <div className="max-h-48 overflow-y-auto space-y-1">
              {candidateBranches.length === 0 ? (
                <p className="text-xs text-textMuted py-2">
                  No other branches found.
                </p>
              ) : (
                candidateBranches.map((b) => {
                  const isChecked = selectedBranches.includes(b);
                  return (
                    <label
                      key={b}
                      className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-surface cursor-pointer text-xs text-text"
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => toggleBranch(b)}
                        className="rounded border-border bg-surface text-accent focus:ring-accent"
                      />
                      <span className="font-mono truncate">{b}</span>
                    </label>
                  );
                })
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

