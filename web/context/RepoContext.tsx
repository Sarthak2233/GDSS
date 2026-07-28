"use client";

import React, { createContext, useContext, useState, ReactNode } from "react";

interface RepoContextState {
  repo: string;
  refName: string;
  setRepo: (repo: string) => void;
  setRefName: (refName: string) => void;
}

const RepoContext = createContext<RepoContextState | undefined>(undefined);

export function RepoProvider({ children, initialRepo = "." }: { children: ReactNode; initialRepo?: string }) {
  const [repo, setRepo] = useState(initialRepo);
  const [refName, setRefName] = useState("main");

  return (
    <RepoContext.Provider value={{ repo, refName, setRepo, setRefName }}>
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
