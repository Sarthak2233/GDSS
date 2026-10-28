"use client";

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";
import { fetcher } from "@/lib/api";
import type { ApiOkEnvelope, BranchesData, HealthData } from "@/lib/api-types";

interface RepoContextState {
  /** Served repository path (read-only; bound at `gdss serve --repo`). */
  repo: string;
  refName: string;
  setRefName: (refName: string) => void;
  branches: string[];
  allBranches: string[];
  branchesLoading: boolean;
  branchesError: string | null;
  selectedBranches: string[];
  setSelectedBranches: (branches: string[]) => void;
}

const RepoContext = createContext<RepoContextState | undefined>(undefined);

export function RepoProvider({
  children,
  initialRepo = "",
}: {
  children: ReactNode;
  initialRepo?: string;
}) {
  const [repo, setRepo] = useState(initialRepo);
  const [refName, setRefName] = useState("main");
  const [branches, setBranches] = useState<string[]>([]);
  const [allBranches, setAllBranches] = useState<string[]>([]);
  const [branchesLoading, setBranchesLoading] = useState(true);
  const [branchesError, setBranchesError] = useState<string | null>(null);
  const [selectedBranches, setSelectedBranches] = useState<string[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setBranchesLoading(true);
      setBranchesError(null);
      try {
        const health = await fetcher<HealthData>("/health");
        if (!cancelled && health.repo) {
          setRepo(health.repo);
        }
      } catch {
        // Health may omit repo on older servers; keep initialRepo.
      }

      try {
        const resp = await fetcher<ApiOkEnvelope<BranchesData>>("/v1/branches");
        if (cancelled) return;
        const data = resp.data;
        setBranches(data.branches || []);
        setAllBranches(data.all_branches && data.all_branches.length > 0 ? data.all_branches : data.branches || []);
        if (data.repo) setRepo(data.repo);
        if (data.active_branch) {
          setRefName((prev) =>
            data.branches.includes(prev) ? prev : data.active_branch || prev
          );
        } else if (data.branches.length > 0) {
          setRefName((prev) =>
            data.branches.includes(prev) ? prev : data.branches[0]
          );
        }
      } catch (err) {
        if (!cancelled) {
          setBranchesError(
            err instanceof Error ? err.message : "Failed to load branches"
          );
        }
      } finally {
        if (!cancelled) setBranchesLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <RepoContext.Provider
      value={{
        repo,
        refName,
        setRefName,
        branches,
        allBranches,
        branchesLoading,
        branchesError,
        selectedBranches,
        setSelectedBranches,
      }}
    >
      {children}
    </RepoContext.Provider>
  );
}

export function useRepo() {
  const context = useContext(RepoContext);
  if (!context) {
    throw new Error("useRepo must be used within a RepoProvider");
  }
  return context;
}
