import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { axe } from "jest-axe";
import {
  DriftTimelineChart,
  DriftBranchData,
} from "../../components/drift/drift-timeline-chart";

vi.mock("framer-motion", async () => {
  const actual = await vi.importActual("framer-motion");
  return {
    ...actual,
    useReducedMotion: () => true,
  };
});

describe("DriftTimelineChart component", () => {
  const sampleBranches: DriftBranchData[] = [
    {
      branch: "feature/auth-refactor",
      magnitude: 0.85,
      velocity: 0.12,
      convergence: "diverging",
      affected: [
        { id: "gdss/auth/service.py::AuthService", name: "AuthService" },
      ],
    },
    {
      branch: "feature/graph-ui",
      magnitude: 0.1,
      velocity: -0.05,
      convergence: "converging",
      affected: [],
    },
  ];

  it("renders manifold summary ribbon with telemetry and entropy status", () => {
    render(
      <DriftTimelineChart
        branches={sampleBranches}
        referenceBranch="main"
      />
    );

    expect(screen.getByText("Per-Branch Trajectory against")).toBeDefined();
    expect(screen.getAllByText("main").length).toBeGreaterThan(0);
    expect(screen.getAllByText("feature/auth-refactor").length).toBeGreaterThan(0);
    expect(screen.getAllByText("feature/graph-ui").length).toBeGreaterThan(0);

    // Summary telemetry labels
    expect(screen.getByText(/Total Trajectories/i)).toBeDefined();
    expect(screen.getByText(/Average Divergence/i)).toBeDefined();
  });

  it("displays philosophical context box when magnitude > 0 but 0 symbols are affected", () => {
    render(
      <DriftTimelineChart
        branches={sampleBranches}
        referenceBranch="main"
      />
    );

    expect(
      screen.getByText(/Structural refactoring, comments, or whitespace edits/i)
    ).toBeDefined();
  });

  it("calls onSelectSymbol when an affected symbol chip is clicked", () => {
    const handleSelectSymbol = vi.fn();
    render(
      <DriftTimelineChart
        branches={sampleBranches}
        referenceBranch="main"
        onSelectSymbol={handleSelectSymbol}
      />
    );

    const btn = screen.getByRole("button", { name: /AuthService/i });
    fireEvent.click(btn);

    expect(handleSelectSymbol).toHaveBeenCalledWith(
      "gdss/auth/service.py::AuthService"
    );
  });

  it("has no accessibility violations", async () => {
    const { container } = render(
      <DriftTimelineChart
        branches={sampleBranches}
        referenceBranch="main"
      />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
