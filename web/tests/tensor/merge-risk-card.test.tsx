import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { axe } from "jest-axe";
import { MergeRiskCard } from "../../components/tensor/merge-risk-card";

vi.mock("framer-motion", async () => {
  const actual = await vi.importActual("framer-motion");
  return {
    ...actual,
    useReducedMotion: () => true,
  };
});

describe("MergeRiskCard", () => {
  it("renders R_merge with deterministic badge and flat Omega subtitle", () => {
    render(<MergeRiskCard mergeRisk={0.97} reference="main" />);

    expect(screen.getByTestId("merge-risk-card")).toBeInTheDocument();
    expect(screen.getByText(/R_merge/i)).toBeInTheDocument();
    expect(screen.getByText(/0\.97/)).toBeInTheDocument();
    expect(screen.getByTestId("evidence-phase-badge")).toHaveAttribute(
      "data-phase",
      "deterministic"
    );
    expect(
      screen.getByText(/flat rank-2 Ω \(not geometric\)/i)
    ).toBeInTheDocument();
  });

  it("has no accessibility violations", async () => {
    const { container } = render(
      <MergeRiskCard mergeRisk={0.2} reference="dev" />
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
