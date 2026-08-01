import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { TrajectoryCard } from "../../components/dashboard/trajectory-card";
import { axe } from "jest-axe";

vi.mock("framer-motion", async () => {
  const actual = await vi.importActual("framer-motion");
  return {
    ...actual,
    useReducedMotion: () => true,
  };
});

describe("TrajectoryCard component", () => {
  it("renders trajectory details, stability index, and operator context", () => {
    render(
      <TrajectoryCard
        activeBranch="feature/geometric-sync"
        referenceBranch="main"
        committedCount={12}
        uncommittedCount={3}
        stabilityPercent={98.7}
      />
    );

    expect(screen.getByText("Trajectory Polyhedron")).toBeInTheDocument();
    expect(screen.getByText("feature/geometric-sync")).toBeInTheDocument();
    expect(screen.getByText(/main/i)).toBeInTheDocument();
    expect(screen.getByText(/12 committed/i)).toBeInTheDocument();
    expect(screen.getByText(/3 uncommitted/i)).toBeInTheDocument();
    expect(screen.getByTestId("trajectory-card")).toBeInTheDocument();
  });

  it("renders loading skeleton when isLoading is true", () => {
    render(
      <TrajectoryCard
        activeBranch=""
        referenceBranch="main"
        committedCount={0}
        uncommittedCount={0}
        isLoading={true}
      />
    );
    expect(screen.getByTestId("trajectory-card-skeleton")).toBeInTheDocument();
  });

  it("renders error state when error is provided", () => {
    render(
      <TrajectoryCard
        activeBranch=""
        referenceBranch="main"
        committedCount={0}
        uncommittedCount={0}
        error="Failed to load trajectory"
      />
    );
    expect(screen.getByText("Failed to load trajectory")).toBeInTheDocument();
  });

  it("has no accessibility violations", async () => {
    const { container } = render(
      <TrajectoryCard
        activeBranch="main"
        referenceBranch="main"
        committedCount={5}
        uncommittedCount={0}
        stabilityPercent={100}
      />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
