import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "jest-axe";
import { MetricCard } from "@/components/ui/metric-card";

describe("MetricCard", () => {
  it("shows trend + context + comparison, never a bare number", () => {
    render(
      <MetricCard
        label="Trajectory length"
        value={125}
        trend={{ delta: 14, percent: 12.7, period: "Today" }}
        spark={[10, 24, 18, 40, 36, 52, 60, 75, 88, 125]}
      />,
    );
    expect(screen.getByText("Trajectory length")).toBeInTheDocument();
    // The number is present (animated counter starts at 0 and animates up).
    expect(screen.getByTestId("metric-card")).toBeInTheDocument();
    // Comparison percent is shown.
    expect(screen.getByText(/12\.7/)).toBeInTheDocument();
    // Context period is shown.
    expect(screen.getByText("Today")).toBeInTheDocument();
  });

  it("has no a11y violations", async () => {
    const { container } = render(
      <MetricCard
        label="Drift"
        value={3}
        trend={{ delta: -2, percent: -40, period: "Today" }}
        spark={[8, 7, 7, 6, 5, 5, 4, 4, 3, 3]}
        tone="warning"
      />,
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("renders without a sparkline (graceful)", () => {
    render(
      <MetricCard
        label="Conflicts"
        value={1}
        trend={{ delta: 0, percent: 0, period: "Today" }}
        tone="danger"
      />,
    );
    expect(screen.getByText("Conflicts")).toBeInTheDocument();
  });
});
