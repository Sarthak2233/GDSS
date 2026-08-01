import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { axe } from "jest-axe";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RepoProvider } from "../../context/RepoContext";
import DriftPage from "../../app/(dashboard)/drift/page";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
  }),
}));

vi.mock("framer-motion", async () => {
  const actual = await vi.importActual("framer-motion");
  return {
    ...actual,
    useReducedMotion: () => true,
  };
});

vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual("../../lib/api");
  return {
    ...actual,
    fetcher: vi.fn(async (url: string) => {
      if (url === "/health") {
        return { version: "1.0", status: "ok", repo: "/tmp/repo" };
      }
      if (url.includes("/v1/branches")) {
        return {
          status: "ok",
          data: {
            branches: ["main", "feature/auth-refactor"],
            active_branch: "main",
            repo: "/tmp/repo",
          },
        };
      }
      if (url.includes("/v1/drift")) {
        return {
          status: "ok",
          data: {
            reference: "main",
            drift: [
              {
                branch: "feature/auth-refactor",
                magnitude: 0.85,
                tip_distance: 0.4,
                trajectory_integral: 0.5,
                velocity: 0.12,
                convergence_score: 0.2,
                convergence_label: "diverging",
                affected: [
                  { id: "gdss/auth/service.py::AuthService", name: "AuthService" },
                ],
                conflict_probability: {
                  score: 0.7,
                  reasons: ["operator interference"],
                  heuristic: "flat",
                },
              },
            ],
          },
        };
      }
      if (url.includes("/v1/alerts")) {
        return {
          status: "ok",
          data: [
            {
              branch: "feature/auth-refactor",
              severity: "high",
              message:
                "HIGH DRIFT ALERT\n\nfeature/auth-refactor diverging from main\nMagnitude: 0.850\n",
              magnitude: 0.85,
              affected: [
                { id: "gdss/auth/service.py::AuthService", name: "AuthService" },
              ],
            },
          ],
        };
      }
      return {};
    }),
  };
});

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <RepoProvider>{ui}</RepoProvider>
    </QueryClientProvider>
  );
}

describe("DriftPage component", () => {
  beforeEach(() => {
    pushMock.mockClear();
  });

  it("renders page header, reference attractor badge, drift radar, timeline, and alerts matrix", async () => {
    renderWithProviders(<DriftPage />);

    expect(screen.getByText("Drift Monitor")).toBeInTheDocument();
    expect(screen.getByText(/Semantic branch drift/i)).toBeInTheDocument();
    expect(screen.getByText(/Reference Attractor:/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getAllByText("feature/auth-refactor").length).toBeGreaterThan(0);
      expect(screen.getByText(/HIGH DRIFT ALERT/i)).toBeInTheDocument();
    });
  });

  it("toggles the 'How to read this Manifold' educational drawer", async () => {
    renderWithProviders(<DriftPage />);

    const guideBtn = screen.getByRole("button", {
      name: /How to read this Manifold/i,
    });
    expect(guideBtn).toBeInTheDocument();

    expect(screen.queryByText(/Tip vs trajectory/i)).toBeNull();

    fireEvent.click(guideBtn);

    expect(screen.getByText(/Tip vs trajectory/i)).toBeInTheDocument();
  });

  it("navigates to /graph when an affected symbol is clicked", async () => {
    renderWithProviders(<DriftPage />);

    await waitFor(() => {
      expect(screen.getAllByText("AuthService").length).toBeGreaterThan(0);
    });

    const symbolBtn = screen.getAllByRole("button", { name: /AuthService/i })[0];
    fireEvent.click(symbolBtn);

    expect(pushMock).toHaveBeenCalledWith(
      "/graph?symbol=gdss%2Fauth%2Fservice.py%3A%3AAuthService"
    );
  });

  it("has no accessibility violations", async () => {
    const { container } = renderWithProviders(<DriftPage />);
    await waitFor(() => {
      expect(screen.getAllByText("feature/auth-refactor").length).toBeGreaterThan(0);
    });
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
