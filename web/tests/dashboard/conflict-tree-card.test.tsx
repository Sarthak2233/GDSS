import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { ConflictTreeCard } from "../../components/dashboard/conflict-tree-card";
import { axe } from "jest-axe";

vi.mock("framer-motion", async () => {
  const actual = await vi.importActual("framer-motion");
  return {
    ...actual,
    useReducedMotion: () => true,
  };
});

describe("ConflictTreeCard component", () => {
  const sampleCommitted = [
    {
      type: "rename_function",
      file: "gdss/core/ast_parser.py",
      name: "parse -> parse_file",
    },
    {
      type: "move_function",
      file: "gdss/utils.py",
      name: "helper_fn",
    },
  ];

  const sampleUncommitted = [
    {
      type: "signature_change",
      file: "gdss/drift/engine.py",
      name: "snapshot",
    },
  ];

  it("renders operator counts, category breakdown, risk pill, and switches tabs", () => {
    render(
      <ConflictTreeCard
        committedOperators={sampleCommitted}
        uncommittedOperators={sampleUncommitted}
      />
    );

    // Default tab is Uncommitted (1 operator, HIGH RISK due to signature_change)
    expect(screen.getByText("Operator Breakdown")).toBeInTheDocument();
    expect(screen.getByText("HIGH RISK")).toBeInTheDocument();
    expect(screen.getByText(/gdss\/drift\/engine\.py/i)).toBeInTheDocument();

    // Toggle to Committed tab
    const committedTabButton = screen.getByRole("button", {
      name: /committed \(2\)/i,
    });
    fireEvent.click(committedTabButton);

    expect(screen.getByText("LOW RISK")).toBeInTheDocument();
    expect(screen.getByText(/gdss\/core\/ast_parser\.py/i)).toBeInTheDocument();
    expect(screen.getByTestId("conflict-tree-card")).toBeInTheDocument();
  });

  it("renders empty state when no operators exist", () => {
    render(
      <ConflictTreeCard
        committedOperators={[]}
        uncommittedOperators={[]}
      />
    );
    expect(screen.getByText("No semantic operators detected")).toBeInTheDocument();
  });

  it("renders loading skeleton when isLoading is true", () => {
    render(
      <ConflictTreeCard
        committedOperators={[]}
        uncommittedOperators={[]}
        isLoading={true}
      />
    );
    expect(
      screen.getByTestId("conflict-tree-card-skeleton")
    ).toBeInTheDocument();
  });

  it("renders error message when error is provided", () => {
    render(
      <ConflictTreeCard
        committedOperators={[]}
        uncommittedOperators={[]}
        error="Failed to load operator matrix"
      />
    );
    expect(
      screen.getByText("Failed to load operator matrix")
    ).toBeInTheDocument();
  });

  it("has no accessibility violations", async () => {
    const { container } = render(
      <ConflictTreeCard
        committedOperators={sampleCommitted}
        uncommittedOperators={sampleUncommitted}
      />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
