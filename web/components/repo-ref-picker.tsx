"use client";

import { useRepo } from "@/context/RepoContext";

export function RepoRefPicker() {
  const {
    repo,
    refName,
    setRefName,
    branches,
    branchesLoading,
    branchesError,
  } = useRepo();

  return (
    <div className="flex items-center gap-4 bg-surface border border-border rounded-xl px-6 py-3 shadow-md flex-wrap">
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
    </div>
  );
}
