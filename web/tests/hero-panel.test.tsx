import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { HeroPanel } from "@/components/landing/hero-panel";
import { axe } from "jest-axe";

describe("HeroPanel component", () => {
  it("renders main headings, badge, and CTA buttons", () => {
    render(<HeroPanel />);
    expect(screen.getByText("Continuous Geometric Synchronizer")).toBeInTheDocument();
    expect(screen.getByText(/The Semantic Intelligence Layer/i)).toBeInTheDocument();
    expect(screen.getByText("Explore Dashboard")).toBeInTheDocument();
    expect(screen.getByText("View Semantic Graph")).toBeInTheDocument();
  });

  it("has no accessibility violations", async () => {
    const { container } = render(<HeroPanel />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
