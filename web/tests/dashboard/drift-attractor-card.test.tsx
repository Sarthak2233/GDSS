import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { DriftAttractorCard } from "../../components/dashboard/drift-attractor-card";
import { axe } from "jest-axe";

vi.mock("framer-motion", async () => {
  const actual = await vi.importActual("framer-motion");
  return {
    ...actual,
    useReducedMotion: () => true,
  };
});

describe("DriftAttractorCard component", () => {
  const sampleBranches = [
    {
      branch: "feature/geometric-sync",
      magnitude: 0.245,
      velocity: -0.05,
      convergence: "converging",
      affected: [
        { id: "sym-1", name: "parse_file" },
        { id: "sym-2", name: "ASTParser" },
      ],
    },
    {
      branch: "feature/experimental",
      magnitude: 0.612,
      velocity: 0.12,
      convergence: "diverging",
      affected: [{ id: "sym-3", name: "DriftEngine" }],
    },
  ];

  it("renders drift magnitude, velocity, convergence badge, and affected symbols", () => {
    render(
      <DriftAttractorCard
        referenceBranch="main"
        branches={sampleBranches}
      />
    );

    expect(screen.getByText("Drift vs Attractor")).toBeInTheDocument();
    expect(screen.getByText(/main/i)).toBeInTheDocument();
    expect(screen.getByText("parse_file")).toBeInTheDocument();
    expect(screen.getByText("ASTParser")).toBeInTheDocument();
    expect(screen.getByTestId("drift-attractor-card")).toBeInTheDocument();
  });

  it("renders stable zero-drift state when no local branches drift", () => {
    render(
      <DriftAttractorCard
        referenceBranch="main"
        branches={[]}
      />
    );
    expect(screen.getByText("0.000")).toBeInTheDocument();
    expect(screen.getByText("No drifted branches")).toBeInTheDocument();
  });

  it("renders loading skeleton when isLoading is true", () => {
    render(
      <DriftAttractorCard
        referenceBranch="main"
        branches={[]}
        isLoading={true}
      />
    );
    expect(
      screen.getByTestId("drift-attractor-card-skeleton")
    ).toBeInTheDocument();
  });

  it("renders error message when error is provided", () => {
    render(
      <DriftAttractorCard
        referenceBranch="main"
        branches={[]}
        error="Drift calculation failed"
      />
    );
    expect(screen.getByText("Drift calculation failed")).toBeInTheDocument();
  });

  it("has no accessibility violations", async () => {
    const { container } = render(
      <DriftAttractorCard
        referenceBranch="main"
        branches={sampleBranches}
      />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
