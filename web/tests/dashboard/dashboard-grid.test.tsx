import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { DashboardGrid } from "../../components/dashboard/dashboard-grid";
import { RepoProvider } from "@/context/RepoContext";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { axe } from "jest-axe";

vi.mock("framer-motion", async () => {
  const actual = await vi.importActual("framer-motion");
  return {
    ...actual,
    useReducedMotion: () => true,
  };
});

const mockFetcher = vi.fn();
vi.mock("@/lib/api", () => ({
  fetcher: (...args: unknown[]) => mockFetcher(...args),
  GDSS_API_BASE_URL: "http://127.0.0.1:8787",
}));

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <RepoProvider initialRepo="/home/sarakb/projects/GDSS">
        {ui}
      </RepoProvider>
    </QueryClientProvider>
  );
}

function mockApi(handlers: Record<string, unknown>) {
  mockFetcher.mockImplementation((url: string) => {
    if (url === "/health") {
      return Promise.resolve({
        version: "1.0",
        status: "ok",
        repo: "/home/sarakb/projects/GDSS",
      });
    }
    if (url.includes("/v1/branches")) {
      return Promise.resolve({
        status: "ok",
        data: {
          branches: ["main", "feature/geometric-sync"],
          active_branch: "feature/geometric-sync",
          repo: "/home/sarakb/projects/GDSS",
        },
      });
    }
    for (const [key, value] of Object.entries(handlers)) {
      if (url.includes(key)) return Promise.resolve(value);
    }
    return Promise.reject(new Error("Unknown url: " + url));
  });
}

describe("DashboardGrid component", () => {
  beforeEach(() => {
    mockFetcher.mockReset();
  });

  it("renders honest dashboard cards with real API fields", async () => {
    mockApi({
      "/v1/status": {
        status: "ok",
        data: {
          active_branch: "feature/geometric-sync",
          reference: "main",
          remote_sync: { label: "origin/main", ahead: 0, behind: 0 },
          committed_operators: [
            { type: "rename_function", file: "gdss/core/ast_parser.py" },
          ],
          uncommitted_operators: [
            { type: "signature_change", file: "gdss/drift/engine.py" },
          ],
        },
        warnings: [],
      },
      "/v1/drift": {
        status: "ok",
        data: {
          reference: "main",
          drift: [
            {
              branch: "feature/geometric-sync",
              magnitude: 0.245,
              tip_distance: 0.2,
              trajectory_integral: 0.3,
              velocity: -0.05,
              convergence_score: 0.8,
              convergence_label: "converging",
              affected: [{ id: "sym-1", name: "parse_file" }],
              conflict_probability: {
                score: 0.4,
                reasons: ["shared modified files: a.py"],
                heuristic: "flat",
              },
            },
          ],
        },
        warnings: [],
      },
    });

    renderWithProviders(<DashboardGrid />);

    await waitFor(() => {
      expect(screen.getByText("Trajectory Polyhedron")).toBeInTheDocument();
      expect(screen.getByText("Remote Sync & Drift")).toBeInTheDocument();
      expect(screen.getByText("Drift vs Attractor")).toBeInTheDocument();
      expect(screen.getByText("Operator Breakdown")).toBeInTheDocument();
      expect(screen.getByText("Conflict Risk")).toBeInTheDocument();
      expect(screen.getByText(/INTEGRITY DEGRADED/)).toBeInTheDocument();
      expect(screen.getByText("feature/geometric-sync")).toBeInTheDocument();
      expect(screen.getByText("parse_file")).toBeInTheDocument();
      expect(screen.getByTestId("dashboard-honesty-footer")).toBeInTheDocument();
    });
  });

  it("renders error state gracefully if API call fails", async () => {
    mockFetcher.mockRejectedValue(new Error("Network Error"));

    renderWithProviders(<DashboardGrid />);

    await waitFor(() => {
      expect(
        screen.getAllByText(/Failed to load/i).length
      ).toBeGreaterThan(0);
    });
  });

  it("has no accessibility violations", async () => {
    mockApi({
      "/v1/status": {
        status: "ok",
        data: {
          active_branch: "main",
          reference: "main",
          remote_sync: { label: "origin/main", ahead: 0, behind: 0 },
          committed_operators: [],
          uncommitted_operators: [],
        },
        warnings: [],
      },
      "/v1/drift": {
        status: "ok",
        data: { reference: "main", drift: [] },
        warnings: [],
      },
    });

    const { container } = renderWithProviders(<DashboardGrid />);
    await waitFor(() => {
      expect(screen.getByText("Trajectory Polyhedron")).toBeInTheDocument();
    });

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
