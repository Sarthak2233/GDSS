import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { StatPills } from "@/components/landing/stat-pills";
import { axe } from "jest-axe";

describe("StatPills component", () => {
  it("renders all four stat capability cards", () => {
    render(<StatPills />);
    expect(screen.getByText("Branches Tracked")).toBeInTheDocument();
    expect(screen.getByText("Drift Vector")).toBeInTheDocument();
    expect(screen.getByText("Conflict Tensor")).toBeInTheDocument();
    expect(screen.getByText("Convergence")).toBeInTheDocument();
  });

  it("has no accessibility violations", async () => {
    const { container } = render(<StatPills />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
