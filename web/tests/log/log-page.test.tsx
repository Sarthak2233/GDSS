import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { axe } from "jest-axe";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RepoProvider } from "@/context/RepoContext";
import LogPage from "@/app/(dashboard)/log/page";

vi.mock("framer-motion", async () => {
  const actual = await vi.importActual("framer-motion");
  return {
    ...actual,
    useReducedMotion: () => true,
  };
});

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual("@/lib/api");
  return {
    ...actual,
    fetcher: vi.fn(async (url: string) => {
      if (url === "/health") {
        return { version: "1.0", status: "ok", repo: "/tmp/repo" };
      }
      if (url.includes("/v1/branches")) {
        return {
          status: "ok",
          data: { branches: ["main"], active_branch: "main", repo: "/tmp/repo" },
        };
      }
      if (url.includes("/v1/log")) {
        return {
          status: "ok",
          data: [
            {
              sha: "abcdef1234567890",
              timestamp: "2026-07-29T00:00:00+00:00",
              operators: [
                {
                  type: "modify_function",
                  file: "a.py",
                  name: "function_1",
                },
              ],
            },
          ],
        };
      }
      return {};
    }),
  };
});

function wrap(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return (
    <QueryClientProvider client={client}>
      <RepoProvider>{ui}</RepoProvider>
    </QueryClientProvider>
  );
}

describe("Semantic Log page", () => {
  it("renders commits and operators from /v1/log", async () => {
    render(wrap(<LogPage />));
    expect(screen.getByText("Semantic Log")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("abcdef12")).toBeInTheDocument();
      expect(screen.getByText("modify_function")).toBeInTheDocument();
      expect(screen.getByText("function_1")).toBeInTheDocument();
    });
  });

  it("has no accessibility violations", async () => {
    const { container } = render(wrap(<LogPage />));
    await waitFor(() => {
      expect(screen.getByText("abcdef12")).toBeInTheDocument();
    });
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
