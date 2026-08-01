import React from "react";
import { render, screen } from "@testing-library/react";
import { axe, toHaveNoViolations } from "jest-axe";
import { describe, it, expect } from "vitest";

expect.extend(toHaveNoViolations);

const { AssistiveBadge } = await import(
  "@/components/constellation/assistive-badge"
);

describe("AssistiveBadge component", () => {
  it("renders assistive badge label and explanation tooltip", () => {
    render(<AssistiveBadge />);
    expect(screen.getByText(/Assistive · Probabilistic/i)).toBeDefined();
    expect(
      screen.getByText(
        /Similarity results are based on embedding approximations, not structural equivalence/i
      )
    ).toBeDefined();
  });

  it("has no accessibility violations", async () => {
    const { container } = render(<AssistiveBadge />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
