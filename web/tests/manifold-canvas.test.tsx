import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { ManifoldCanvas } from "@/components/landing/manifold-canvas";
import { axe } from "jest-axe";

// Mock framer-motion useReducedMotion
vi.mock("framer-motion", async () => {
  const actual = await vi.importActual("framer-motion");
  return {
    ...actual,
    useReducedMotion: () => true, // default to reduced motion in test environment for static SVG rendering
  };
});

describe("ManifoldCanvas component", () => {
  it("renders static SVG fallback in reduced motion mode", () => {
    render(<ManifoldCanvas />);
    expect(screen.getByLabelText("Static semantic manifold grid")).toBeInTheDocument();
  });

  it("has no accessibility violations", async () => {
    const { container } = render(<ManifoldCanvas />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
