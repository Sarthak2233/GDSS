import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { ConflictRiskCard } from "../../components/dashboard/resolution-probability-card";
import { axe } from "jest-axe";

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
  }: {
    children: React.ReactNode;
    href: string;
  }) => <a href={href}>{children}</a>,
}));

vi.mock("framer-motion", async () => {
  const actual = await vi.importActual("framer-motion");
  return {
    ...actual,
    useReducedMotion: () => true,
  };
});

describe("ConflictRiskCard component", () => {
  it("renders flat heuristic conflict score and reasons", () => {
    render(
      <ConflictRiskCard
        conflictScore={0.4}
        reasons={["shared modified files: a.py"]}
        branchCount={2}
      />
    );

    expect(screen.getByText("Conflict Risk")).toBeInTheDocument();
    expect(screen.getByText("40%")).toBeInTheDocument();
    expect(screen.getByText(/shared modified files/i)).toBeInTheDocument();
    expect(screen.getByTestId("conflict-risk-card")).toBeInTheDocument();
    expect(screen.getByTestId("evidence-phase-badge")).toHaveAttribute(
      "data-phase",
      "assistive-heuristic"
    );
    expect(
      screen.getByRole("link", { name: /view flat Ω matrix/i })
    ).toHaveAttribute("href", "/tensor");
  });

  it("renders loading skeleton when isLoading is true", () => {
    render(<ConflictRiskCard isLoading={true} />);
    expect(
      screen.getByTestId("conflict-risk-card-skeleton")
    ).toBeInTheDocument();
  });

  it("renders error message when error is provided", () => {
    render(
      <ConflictRiskCard error="Failed to calculate conflict probability" />
    );
    expect(
      screen.getByText("Failed to calculate conflict probability")
    ).toBeInTheDocument();
  });

  it("has no accessibility violations", async () => {
    const { container } = render(
      <ConflictRiskCard conflictScore={0.2} reasons={[]} branchCount={1} />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
