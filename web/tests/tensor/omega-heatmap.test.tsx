import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { axe } from "jest-axe";
import { OmegaHeatmap } from "../../components/tensor/omega-heatmap";
import type { TensorEntry } from "../../lib/api-types";

vi.mock("framer-motion", async () => {
  const actual = await vi.importActual("framer-motion");
  return {
    ...actual,
    useReducedMotion: () => true,
  };
});

const branches = ["feature", "main"];
const entries: TensorEntry[] = [
  {
    i: "feature",
    j: "main",
    omega: 0.42,
    reasons: ["same_file"],
  },
  {
    i: "feature",
    j: "feature",
    omega: 0.8,
    reasons: ["drift_self_energy"],
  },
];

describe("OmegaHeatmap", () => {
  it("renders N×N cells from branches and sparse entries", () => {
    render(
      <OmegaHeatmap
        branches={branches}
        entries={entries}
        selected={null}
        onSelect={vi.fn()}
      />
    );

    expect(screen.getByTestId("omega-heatmap")).toBeInTheDocument();
    expect(screen.getByRole("grid")).toBeInTheDocument();
    expect(screen.getByText(/Ω heatmap/i)).toBeInTheDocument();
    // 2×2 = 4 cells
    expect(screen.getAllByRole("gridcell")).toHaveLength(4);
    expect(screen.getByLabelText(/omega feature × main/i)).toHaveTextContent(
      "0.42"
    );
  });

  it("calls onSelect when a cell is activated", () => {
    const onSelect = vi.fn();
    render(
      <OmegaHeatmap
        branches={branches}
        entries={entries}
        selected={null}
        onSelect={onSelect}
      />
    );

    fireEvent.click(screen.getByLabelText(/omega feature × main/i));
    expect(onSelect).toHaveBeenCalledWith({ i: "feature", j: "main" });
  });

  it("has no accessibility violations", async () => {
    const { container } = render(
      <OmegaHeatmap
        branches={branches}
        entries={entries}
        selected={{ i: "feature", j: "main" }}
        onSelect={vi.fn()}
      />
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
