"use client";

import { useRepo } from "@/context/RepoContext";

export function RepoRefPicker() {
  const { repo, refName, setRepo, setRefName } = useRepo();

  return (
    <div className="flex items-center gap-4 bg-background/60 backdrop-blur-md border-b border-border px-6 py-3">
      <div className="flex items-center gap-2">
        <label htmlFor="repo-input" className="text-sm font-medium text-muted-foreground whitespace-nowrap">Repo:</label>
        <input
          id="repo-input"
          type="text"
          value={repo}
          onChange={(e) => setRepo(e.target.value)}
          className="bg-muted px-3 py-1 rounded-md text-sm border-transparent focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all w-64 text-foreground"
        />
      </div>
      <div className="flex items-center gap-2">
        <label htmlFor="ref-input" className="text-sm font-medium text-muted-foreground whitespace-nowrap">Ref:</label>
        <input
          id="ref-input"
          type="text"
          value={refName}
          onChange={(e) => setRefName(e.target.value)}
          className="bg-muted px-3 py-1 rounded-md text-sm border-transparent focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all w-32 text-foreground"
        />
      </div>
    </div>
  );
}
