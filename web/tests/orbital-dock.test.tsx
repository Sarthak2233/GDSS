import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { OrbitalDock } from "@/components/landing/orbital-dock";
import { axe } from "jest-axe";

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
}));

describe("OrbitalDock component", () => {
  it("renders dock navigation links with accessible label", () => {
    render(<OrbitalDock />);
    expect(screen.getByLabelText("Orbital Navigation Dock")).toBeInTheDocument();
    expect(screen.getByText("Overview")).toBeInTheDocument();
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
  });

  it("has no accessibility violations", async () => {
    const { container } = render(<OrbitalDock />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
