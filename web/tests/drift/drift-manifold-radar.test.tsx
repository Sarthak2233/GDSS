import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { axe } from "jest-axe";
import {
  DriftManifoldRadar,
  DriftManifoldRadarProps,
} from "../../components/drift/drift-manifold-radar";

vi.mock("framer-motion", async () => {
  const actual = await vi.importActual("framer-motion");
  return {
    ...actual,
    useReducedMotion: () => true,
  };
});

describe("DriftManifoldRadar component", () => {
  const sampleBranches: DriftManifoldRadarProps["branches"] = [
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
      magnitude: 0.25,
      velocity: -0.05,
      convergence: "converging",
      affected: [],
    },
  ];

  it("renders the Geodesic Orbital Radar heading and reference attractor", () => {
    render(
      <DriftManifoldRadar
        branches={sampleBranches}
        referenceBranch="main"
      />
    );

    expect(screen.getByText("Geodesic Orbital Radar")).toBeDefined();
    expect(screen.getAllByText("main").length).toBeGreaterThan(0);
    expect(screen.getAllByText("feature/auth-refactor").length).toBeGreaterThan(0);
    expect(screen.getAllByText("feature/graph-ui").length).toBeGreaterThan(0);
  });

  it("calls onSelectBranch when a branch row or node is clicked", () => {
    const handleSelectBranch = vi.fn();
    render(
      <DriftManifoldRadar
        branches={sampleBranches}
        referenceBranch="main"
        onSelectBranch={handleSelectBranch}
      />
    );

    const btn = screen.getByRole("button", { name: /feature\/auth-refactor/i });
    fireEvent.click(btn);

    expect(handleSelectBranch).toHaveBeenCalledWith("feature/auth-refactor");
  });

  it("has no accessibility violations", async () => {
    const { container } = render(
      <DriftManifoldRadar
        branches={sampleBranches}
        referenceBranch="main"
      />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
